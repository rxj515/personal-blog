# -*- coding: utf-8 -*-

"""
法规知识库构建程序（数组输出 articles.json）

OCR 引擎：阿里云 DocMind

输出：
    data/knowledge/<PDF名>/articles.json

支持三种文档：
    1. law_book      → 法规书（第一部分 + 第二部分）
    2. notice_items  → 通知 + 一、二、三、……
    3. regulation    → 规程（第X编/章/节 + 第X条）
"""

import os
import re
import json
import hashlib
import time
import uuid
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, unquote

import fitz as pymupdf
import oss2
import requests

from alibabacloud_docmind_api20220711.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_docmind_api20220711 import models as docmind_models
from alibabacloud_tea_util import models as util_models


# =========================================================
# 1. 目录
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "pdf"
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
BACKUP_DIR = BASE_DIR / "data" / "backup"
RAW_TXT_DIR = BASE_DIR / "data" / "raw_txt"
CLEAN_TXT_DIR = BASE_DIR / "data" / "clean_txt"
DOCMIND_DIR = BASE_DIR / "data" / "docmind"

PROGRESS_FILE = BASE_DIR / "data" / "update_progress.json"


# =========================================================
# 2. 全局进度
# =========================================================

_DEFAULT_PROGRESS = {
    "total": 0,
    "processed": 0,
    "status": "idle",
    "message": "",
    "source_file": "",
    "current_pdf": "",
    "overall_percent": 0,
    "stage": "",
    "stage_percent": 0,
    "part_total": 0,
    "part_processed": 0,
    "page_total": 0,
    "page_processed": 0,
}

update_progress = dict(_DEFAULT_PROGRESS)


def _save_progress():
    try:
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS_FILE.write_text(
            json.dumps(update_progress, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"⚠️ 写进度文件失败：{e}")


def _load_progress():
    global update_progress
    try:
        if PROGRESS_FILE.exists():
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in _DEFAULT_PROGRESS.items():
                    data.setdefault(k, v)
                update_progress.clear()
                update_progress.update(data)
                return
    except Exception as e:
        print(f"⚠️ 读进度文件失败：{e}")

    update_progress.clear()
    update_progress.update(_DEFAULT_PROGRESS)


def get_progress():
    _load_progress()
    return dict(update_progress)


def reset_progress(source_file=""):
    update_progress.clear()
    update_progress.update(dict(_DEFAULT_PROGRESS))
    update_progress["status"] = "running"
    update_progress["message"] = (
        f"准备更新 {source_file}" if source_file else "准备更新"
    )
    update_progress["source_file"] = source_file or ""
    update_progress["stage"] = "准备"
    _save_progress()


def set_progress(stage, stage_percent, message="", **extra):
    stage_percent = max(0.0, min(100.0, float(stage_percent)))

    if stage == "准备":
        overall = stage_percent * 0.05
    elif stage == "阿里云解析":
        overall = 5 + stage_percent * 0.90
    elif stage == "后处理":
        overall = 95 + stage_percent * 0.05
    else:
        overall = stage_percent

    update_progress["stage"] = stage
    update_progress["stage_percent"] = round(stage_percent, 1)
    update_progress["overall_percent"] = round(min(100.0, overall), 1)
    if message:
        update_progress["message"] = message
    for k, v in extra.items():
        update_progress[k] = v

    _save_progress()


def set_progress_field(key, value):
    update_progress[key] = value
    _save_progress()


# =========================================================
# 3. 阿里云 DocMind 配置
# =========================================================

ALIYUN_ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID", "").strip()
ALIYUN_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "").strip()

ALIYUN_ENDPOINT = "docmind-api.cn-hangzhou.aliyuncs.com"
ALIYUN_REGION = "cn-hangzhou"

ALIYUN_OSS_ENDPOINT = "https://oss-cn-hangzhou.aliyuncs.com"
ALIYUN_OSS_BUCKET = "pdf-ocr-temp"

# ---------- 超时配置（关键修改点） ----------
# 单位：毫秒
DOCMIND_CONNECT_TIMEOUT = 30000      # 连接超时 30 秒
DOCMIND_READ_TIMEOUT = 120000        # 读取超时 120 秒（原来是默认 10 秒）

DOCMIND_POLL_INTERVAL = 5
DOCMIND_MAX_WAIT = 60 * 30
DOCMIND_BATCH_SIZE = 50
DOCMIND_RETRY_COUNT = 3


# =========================================================
# 4. 目录创建
# =========================================================

def create_directories():
    for d in [
        PDF_DIR, KNOWLEDGE_DIR, BACKUP_DIR,
        RAW_TXT_DIR, CLEAN_TXT_DIR, DOCMIND_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)


# =========================================================
# 5. 安全文件名
# =========================================================

def safe_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return name or "未知法规"


# =========================================================
# 6. 阿里云工具：安全取值
# =========================================================

def _pick(obj, *keys):
    """从 dict 或对象里按顺序取第一个非空值"""
    if obj is None:
        return None

    for k in keys:
        if isinstance(obj, dict):
            if k in obj and obj[k] not in (None, ""):
                return obj[k]
        else:
            v = getattr(obj, k, None)
            if v not in (None, ""):
                return v

    return None


def check_aliyun_config():
    if not ALIYUN_ACCESS_KEY_ID or not ALIYUN_ACCESS_KEY_SECRET:
        raise RuntimeError(
            "没有配置 ALIYUN_ACCESS_KEY_ID / ALIYUN_ACCESS_KEY_SECRET"
        )


# =========================================================
# 7. PDF 页数
# =========================================================

def get_pdf_page_count(pdf_path):
    doc = pymupdf.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


# =========================================================
# 8. 上传 PDF 到 OSS
# =========================================================

def upload_pdf_to_oss(pdf_path):
    check_aliyun_config()

    auth = oss2.Auth(ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, ALIYUN_OSS_ENDPOINT, ALIYUN_OSS_BUCKET)

    object_name = f"pdf/{pdf_path.name}"

    print(f"⬆️ 上传到 OSS：{pdf_path.name}")
    print(f"   大小：{pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

    bucket.put_object_from_file(object_name, str(pdf_path))

    file_url = (
        f"https://{ALIYUN_OSS_BUCKET}.oss-cn-hangzhou.aliyuncs.com/"
        f"{object_name}"
    )
    print(f"✅ OSS URL：{file_url}")
    return file_url


# =========================================================
# 9. 阿里云 DocMind 客户端
# =========================================================

def create_docmind_client():
    config = open_api_models.Config(
        access_key_id=ALIYUN_ACCESS_KEY_ID,
        access_key_secret=ALIYUN_ACCESS_KEY_SECRET,
        region_id=ALIYUN_REGION,
    )
    config.endpoint = ALIYUN_ENDPOINT
    return Client(config)


# =========================================================
# 10. 提交解析任务（关键修改点：加超时 + 重试）
# =========================================================

def docmind_submit_job(client, pdf_url):
    parsed = urlparse(pdf_url)
    file_name = unquote(parsed.path.split("/")[-1])

    request = docmind_models.SubmitDocParserJobRequest(
        file_url=pdf_url,
        file_name=file_name,
    )

    # 显式设置超时，避免默认 10 秒 read timeout 导致超时
    runtime = util_models.RuntimeOptions(
        connect_timeout=DOCMIND_CONNECT_TIMEOUT,
        read_timeout=DOCMIND_READ_TIMEOUT,
    )

    last_exc = None
    for attempt in range(1, DOCMIND_RETRY_COUNT + 1):
        try:
            print(f"📤 提交 DocMind 任务（第 {attempt}/{DOCMIND_RETRY_COUNT} 次）...")
            response = client.submit_doc_parser_job_with_options(request, runtime)

            data = getattr(response.body, "data", None)
            if data is None:
                raise RuntimeError(f"DocMind 提交失败，返回：{response.body}")

            task_id = _pick(data, "Id", "id")
            if not task_id:
                raise RuntimeError("DocMind 没有返回 task_id")

            print(f"✅ 提交成功，TaskId={task_id}")
            return task_id

        except Exception as e:
            last_exc = e
            print(f"⚠️ 第 {attempt} 次提交失败：{e}")
            if attempt < DOCMIND_RETRY_COUNT:
                wait = 3 * attempt
                print(f"   {wait} 秒后重试...")
                time.sleep(wait)

    raise RuntimeError(
        f"DocMind 提交任务连续失败 {DOCMIND_RETRY_COUNT} 次，最后一次错误：{last_exc}"
    )


# =========================================================
# 11. 轮询状态 + 分页拉全部结果（关键修改点：统一超时）
# =========================================================

def docmind_wait_and_fetch(client, task_id):
    print("⏳ 等待阿里云解析...")
    start = time.time()

    # 统一使用配置里的超时
    runtime = util_models.RuntimeOptions(
        connect_timeout=DOCMIND_CONNECT_TIMEOUT,
        read_timeout=DOCMIND_READ_TIMEOUT,
    )

    while True:
        elapsed = time.time() - start
        if elapsed > DOCMIND_MAX_WAIT:
            raise TimeoutError(
                f"阿里云解析等待超过 {DOCMIND_MAX_WAIT // 60} 分钟"
            )

        status_request = docmind_models.QueryDocParserStatusRequest(
            id=task_id,
        )

        status_response = client.query_doc_parser_status_with_options(
            status_request, runtime
        )
        status_data = getattr(status_response.body, "data", None)

        if status_data is None:
            time.sleep(DOCMIND_POLL_INTERVAL)
            continue

        status = _pick(status_data, "Status", "status")
        print(f"  [{int(elapsed)}s] 状态：{status}")

        set_progress(
            "阿里云解析",
            50,
            f"阿里云解析中：{status}",
        )

        if status and status.lower() == "success":
            print("✅ 解析完成，开始拉取结果...")

            all_layouts = []
            offset = 0

            while True:
                result_request = docmind_models.GetDocParserResultRequest(
                    id=task_id,
                    layout_num=offset,
                    layout_step_size=DOCMIND_BATCH_SIZE,
                )
                result_response = client.get_doc_parser_result_with_options(
                    result_request, runtime
                )
                data = getattr(result_response.body, "data", None)

                if not data:
                    break

                layouts = _pick(data, "Layouts", "layouts") or []
                if isinstance(layouts, list):
                    all_layouts.extend(layouts)

                print(f"  已拉取 {len(all_layouts)} 个块...")

                if len(layouts) < DOCMIND_BATCH_SIZE:
                    break

                offset += DOCMIND_BATCH_SIZE
                time.sleep(0.2)

            print(f"✅ 共 {len(all_layouts)} 个 layout 块")
            return all_layouts

        elif status and status.lower() == "fail":
            raise RuntimeError(
                f"阿里云解析失败：{json.dumps(status_data, ensure_ascii=False, default=str)}"
            )

        time.sleep(DOCMIND_POLL_INTERVAL)


# =========================================================
# 12. layouts → markdown
# =========================================================

def layouts_to_markdown(layouts):
    """
    把阿里云返回的 layouts 拼成 markdown。

    注意：layout 是 dict，key 是驼峰 markdownContent
    （不是 MarkdownContent，也不是 markdown_content）
    """
    md_parts = []
    for layout in layouts:
        if isinstance(layout, dict):
            md = (
                layout.get("markdownContent")
                or layout.get("MarkdownContent")
                or layout.get("markdown_content")
                or layout.get("md")
            )
        else:
            md = (
                getattr(layout, "markdownContent", None)
                or getattr(layout, "MarkdownContent", None)
                or getattr(layout, "markdown_content", None)
                or getattr(layout, "md", None)
            )
        if md:
            md_parts.append(md)
    return "\n".join(md_parts)


# =========================================================
# 13. 主解析入口
# =========================================================

def parse_pdf_by_aliyun_docmind(pdf_path):
    print("\n========================================")
    print("开始调用阿里云 DocMind")
    print("========================================")

    check_aliyun_config()

    set_progress("准备", 20, f"[{pdf_path.name}] 读取页数...")
    page_count = get_pdf_page_count(pdf_path)
    print(f"PDF 页数：{page_count}")

    # ---------- 上传 OSS ----------
    set_progress("准备", 60, f"[{pdf_path.name}] 上传到 OSS...")
    pdf_url = upload_pdf_to_oss(pdf_path)

    # ---------- 提交任务 ----------
    set_progress("阿里云解析", 10, f"[{pdf_path.name}] 提交解析任务...")
    client = create_docmind_client()
    task_id = docmind_submit_job(client, pdf_url)
    print(f"TaskId：{task_id}")

    # ---------- 轮询 + 拉取 ----------
    set_progress("阿里云解析", 20, f"[{pdf_path.name}] 等待解析...")
    layouts = docmind_wait_and_fetch(client, task_id)

    if not layouts:
        raise RuntimeError("阿里云没有返回任何 layout")

    # ---------- 拼 markdown ----------
    set_progress("阿里云解析", 90, f"[{pdf_path.name}] 拼接 Markdown...")
    markdown = layouts_to_markdown(layouts)

    # ---------- 保存 md ----------
    out_dir = DOCMIND_DIR / safe_filename(pdf_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)
    final_md = out_dir / "full.md"
    final_md.write_text(markdown, encoding="utf-8")

    print("\n========================================")
    print("阿里云 DocMind 解析完成")
    print(f"Markdown：{final_md}")
    print(f"总长度：{len(markdown)} 字符")
    print("========================================")

    set_progress("阿里云解析", 100, f"[{pdf_path.name}] 解析完成")
    return markdown


# =========================================================
# 14. 识别法规名称
# =========================================================

def detect_law_name_from_markdown(markdown, pdf_path):
    if not markdown:
        return pdf_path.stem

    lines = markdown.splitlines()
    candidates = []

    exclude_keywords = [
        "目录", "Contents", "附件", "附录", "附则", "法规条文", "目录页",
    ]

    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        text = re.sub(r"^#{1,6}\s*", "", line).strip()
        if not text:
            continue

        text = re.sub(r"[\*_`]+", "", text).strip()

        if len(text) < 4 or len(text) > 80:
            continue
        if text in exclude_keywords:
            continue
        if re.match(r"^第\s*[一二三四五六七八九十百千万零〇0-9]+\s*条", text):
            continue
        if re.match(r"^第\s*[一二三四五六七八九十百千万零〇0-9]+\s*(编|章|节)", text):
            continue
        if re.fullmatch(
            r"[0-9０-９]{4}年[0-9０-９]{1,2}月[0-9０-９]{1,2}日?",
            text,
        ):
            continue

        score = 0
        if raw_line.startswith("# "):
            score += 100
        elif raw_line.startswith("## "):
            score += 60
        elif raw_line.startswith("### "):
            score += 30

        if re.search(r"(法|条例|规程|规定|办法|细则|规则|标准|规范)", text):
            score += 100

        if 5 <= len(text) <= 40:
            score += 30
        if len(text) > 50:
            score -= 30

        if re.search(r"(文件|通知|公告|决定|批复|函)$", text):
            score -= 50

        candidates.append({"text": text, "score": score, "index": index})

    if not candidates:
        return pdf_path.stem

    candidates.sort(key=lambda x: x["score"], reverse=True)
    title = re.sub(r"\s+", "", candidates[0]["text"])
    return title or pdf_path.stem


# =========================================================
# 15. 结构行 / 附则 / 附录
# =========================================================

def is_structure_line(line):
    return bool(
        re.match(
            r"^第\s*[一二三四五六七八九十百千万零〇0-9]+\s*(编|章|节)(?:\s+.*)?$",
            line.strip(),
        )
    )


def is_appendix_section(line):
    return bool(re.fullmatch(r"附\s*则", line.strip()))


def is_definitions_title(line):
    return bool(re.match(r"^附录\s*[　 ]*主要名词解释", line.strip()))


# =========================================================
# 16. 条文编号
# =========================================================

def normalize_article_number(text):
    match = re.match(
        r"^第\s*([一二三四五六七八九十百千万零〇0-9]+)\s*条",
        text,
    )
    if not match:
        return None
    return f"第{match.group(1)}条"


def is_true_article_start(text):
    if not text:
        return False

    text = text.strip()
    match = re.match(
        r"^第\s*([一二三四五六七八九十百千万零〇0-9]+)\s*条",
        text,
    )
    if not match:
        return False

    rest = text[match.end():].strip()
    if not rest:
        return True

    reference_pattern = re.compile(
        r"^(?:"
        r"第[一二三四五六七八九十百千万零〇0-9]+(?:项|款|目)"
        r"|的规定|规定|和|与|中|所述|以及|、"
        r"|，|,|。|；|;|：|:"
        r")"
    )
    if reference_pattern.match(rest):
        return False

    if re.search(r"(?:\.{2,}|…{2,}|·{2,})\s*[0-9０-９]+$", text):
        return False

    return True


def parse_article(text):
    if not text:
        return None, None

    text = text.strip()
    if not is_true_article_start(text):
        return None, None

    match = re.match(
        r"^第\s*([一二三四五六七八九十百千万零〇0-9]+)\s*条",
        text,
    )
    if not match:
        return None, None

    raw_article = match.group(0)
    article = normalize_article_number(raw_article)
    if not article:
        return None, None

    return article, text[len(raw_article):].strip()


# =========================================================
# 17. 上标 / LaTeX 清理
# =========================================================

def to_superscript(value):
    mapping = {
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
        "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
        "+": "⁺", "-": "⁻",
    }
    return "".join(mapping.get(c, c) for c in str(value))


def clean_math_formula(text):
    if not text:
        return text

    text = re.sub(
        r"\\mathrm\s*\{\s*~?\s*([a-zA-Z]+)\s*\}\s*\^\s*\{\s*([0-9]+)\s*\}",
        lambda m: f"{m.group(1)}{to_superscript(m.group(2))}",
        text,
    )
    text = re.sub(
        r"\\mathrm\s*\{\s*([a-zA-Z]+)\s*\}\s*\^\s*([0-9]+)",
        lambda m: f"{m.group(1)}{to_superscript(m.group(2))}",
        text,
    )
    text = re.sub(
        r"([a-zA-Z]+)\s*\^\s*\{\s*([0-9]+)\s*\}",
        lambda m: f"{m.group(1)}{to_superscript(m.group(2))}",
        text,
    )
    text = re.sub(
        r"([a-zA-Z]+)\s*\^\s*([0-9]+)",
        lambda m: f"{m.group(1)}{to_superscript(m.group(2))}",
        text,
    )
    text = re.sub(
        r"\\mathrm\s*\{\s*~?\s*([a-zA-Z]+)\s*\}",
        r"\1",
        text,
    )
    text = re.sub(r"\\mathrm\s+([a-zA-Z]+)", r"\1", text)
    text = re.sub(r"\\text\s*\{\s*([^{}]*)\s*\}", r"\1", text)

    text = text.replace(r"\,", " ").replace(r"\;", " ").replace(r"\:", " ")
    text = text.replace(r"\!", "").replace(r"\ ", " ")

    text = text.replace(r"\%", "%")
    text = text.replace(r"\times", "×")
    text = text.replace(r"\cdot", "·")
    text = text.replace(r"\leq", "≤").replace(r"\le", "≤")
    text = text.replace(r"\geq", "≥").replace(r"\ge", "≥")
    text = text.replace(r"\neq", "≠")
    text = text.replace(r"\pm", "±")

    text = re.sub(r"\$+", "", text)
    text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\mathrm\s*\{\s*~?\s*([a-zA-Z]+)\s*\}", r"\1", text)
    text = re.sub(r"\\mathrm\s+([a-zA-Z]+)", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def clean_markdown_line(line, preserve_heading=False):
    if not line:
        return ""

    line = line.replace("\r", "").strip()
    if not line:
        return ""

    heading_prefix = ""
    if preserve_heading:
        match = re.match(r"^(#{1,6})\s*", line)
        if match:
            heading_prefix = match.group(1)
            line = line[match.end():]
    else:
        line = re.sub(r"^#{1,6}\s*", "", line)

    line = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", line)
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    line = re.sub(r"<[^>]+>", "", line)
    line = re.sub(r"[\*\_\`]+", "", line)
    line = clean_math_formula(line)
    line = re.sub(r"[ \t]+", " ", line).strip()

    if preserve_heading and heading_prefix and line:
        line = f"{heading_prefix} {line}"

    return line


def remove_page_number(lines):
    result = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.fullmatch(r"[—\-－_]+", line):
            continue
        if re.fullmatch(r"[0-9０-９]+", line):
            continue
        result.append(line)
    return result


# =========================================================
# 18. 文本行
# =========================================================

def extract_pdf(pdf_path):
    print("\n正在读取：")
    print(pdf_path)

    markdown = parse_pdf_by_aliyun_docmind(pdf_path)

    law_name = detect_law_name_from_markdown(markdown, pdf_path)
    print(f"\n识别法规名称：{law_name}")

    lines = []
    for raw_line in markdown.splitlines():
        line = clean_markdown_line(raw_line, preserve_heading=True)
        if not line:
            continue
        lines.append(line)

    lines = remove_page_number(lines)
    print(f"解析返回文本：{len(lines)} 行")

    return law_name, lines, markdown


def save_raw_txt(pdf_path, all_lines):
    output_path = RAW_TXT_DIR / f"{safe_filename(pdf_path.stem)}_原始.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for line in all_lines:
            f.write(line + "\n")
    return output_path


def save_clean_txt(pdf_path, cleaned):
    output_path = CLEAN_TXT_DIR / f"{safe_filename(pdf_path.stem)}_清洗后.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for item in cleaned:
            f.write(item["text"] + "\n")
    return output_path


# =========================================================
# 19. 唯一 ID
# =========================================================

def make_article_id(law_name, article, part=""):
    raw = f"{law_name}_{part}_{article}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# =========================================================
# 20. 文档类型判断
# =========================================================

CN_ITEM_PATTERN = re.compile(
    r"^([一二三四五六七八九十百零〇]+)\s*[、.，,]\s*(.+)$"
)


def detect_document_type(markdown):
    if not markdown:
        return "unknown"

    lines = markdown.splitlines()

    has_part1 = False
    has_part2 = False
    article_count = 0

    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"#{0,6}\s*第一部分\s*", stripped):
            has_part1 = True
        if re.fullmatch(r"#{0,6}\s*第二部分\s*", stripped):
            has_part2 = True
        if re.fullmatch(r"#{0,6}\s*对照检查\s*", stripped):
            has_part2 = True

        text = re.sub(r"^#{1,6}\s*", "", stripped)
        if re.match(r"^第\s*[一二三四五六七八九十百千万零〇0-9]+\s*条", text):
            article_count += 1

    if has_part1 and has_part2:
        return "law_book"

    item_count = 0
    for line in lines:
        stripped = re.sub(r"^#{1,6}\s*", "", line).strip()
        if CN_ITEM_PATTERN.match(stripped):
            item_count += 1

    if item_count >= 5:
        return "notice_items"

    if article_count >= 50:
        return "regulation"

    return "unknown"


# =========================================================
# 21. 第一部分：清洗 + JSON
# =========================================================

def extract_section_title(line):
    match = re.match(
        r"^(第\s*[一二三四五六七八九十百千万零〇0-9]+\s*[编章节])",
        line.strip(),
    )
    if match:
        return re.sub(r"\s+", "", match.group(1))
    return line.strip()


def clean_text(all_lines):
    result = []
    current_text = ""
    current_section = ""

    def flush_current():
        nonlocal current_text
        if current_text.strip():
            result.append({
                "text": current_text.strip(),
                "section": current_section,
            })
        current_text = ""

    for line in all_lines:
        line = line.strip()
        if not line:
            continue

        line = re.sub(r"^#{1,6}\s*", "", line).strip()
        if not line:
            continue

        if is_appendix_section(line):
            flush_current()
            current_section = "附则"
            continue

        if is_definitions_title(line):
            flush_current()
            current_section = "附录"
            result.append({"text": line, "section": "附录"})
            continue

        if is_structure_line(line):
            flush_current()
            current_section = extract_section_title(line)
            continue

        if is_true_article_start(line):
            flush_current()
            current_text = line
            continue

        if current_text:
            current_text += "\n" + line
        else:
            current_text = line

    flush_current()
    return result


def build_part1_json(cleaned, law_name, source_file, part="第一部分"):
    articles = []
    in_definitions = False
    definitions_title = ""
    definitions_content = []
    current_article = None
    current_content = []
    current_section = ""

    def save_current_article():
        nonlocal current_article, current_content, current_section
        if not current_article:
            return

        content = "\n".join(current_content).strip()
        if not content:
            current_article = None
            current_content = []
            return

        data = {
            "id": make_article_id(law_name, current_article, part),
            "type": "article",
            "part": part,
            "law_name": law_name,
            "article": current_article,
            "content": content,
            "source_file": source_file,
        }
        if current_section:
            data["section"] = current_section

        articles.append(data)
        current_article = None
        current_content = []

    def save_definitions():
        nonlocal definitions_content
        if definitions_title and definitions_content:
            articles.append({
                "id": make_article_id(law_name, definitions_title, part),
                "type": "definitions",
                "part": part,
                "law_name": law_name,
                "title": definitions_title,
                "content": "\n".join(definitions_content).strip(),
                "source_file": source_file,
            })
        definitions_content = []

    for item in cleaned:
        text = item["text"].strip()
        section = item["section"] or ""
        if not text:
            continue

        if is_definitions_title(text):
            save_current_article()
            if in_definitions:
                save_definitions()
            definitions_title = text
            definitions_content = []
            in_definitions = True
            continue

        if in_definitions:
            if section == "附录":
                definitions_content.append(text)
                continue
            else:
                save_definitions()
                in_definitions = False

        article, content = parse_article(text)
        if article:
            save_current_article()
            current_article = article
            current_content = []
            current_section = section
            if content:
                current_content.append(content)
            continue

        if current_article:
            if is_structure_line(text):
                continue
            current_content.append(text)

    save_current_article()
    if in_definitions:
        save_definitions()

    return articles


# =========================================================
# 22. 第二部分：对照检查解析
# =========================================================

GUIDE_TITLE_PATTERN = re.compile(
    r"^#{1,6}\s*"
    r"第\s*([一二三四五六七八九十百千万零〇0-9]+)\s*条"
    r"\s*"
    r"[【\[［〔《(（]\s*"
    r"([^】\]］〕》\)）]+?)"
    r"\s*[】\]］〕》\)）]"
)

GUIDE_BLOCK_PATTERN = re.compile(
    r"^#{0,6}\s*[●◆♦\s]*"
    r"(解读|检查范围|检查方法)"
    r"\s*$"
)

CASE_TITLE_PATTERN = re.compile(
    r"^【\s*典型案例\s*([0-9０-９]*)\s*】\s*(.*)$"
)

CASE_FIELD_PATTERN = re.compile(
    r"^\s*([0-9０-９]+)\s*[\.、]\s*"
    r"(具体情形|行为定性|处罚结果)"
    r"\s*[:：]\s*(.*)$"
)


def extract_part2(markdown):
    lines = markdown.splitlines()
    start = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if re.fullmatch(r"#{0,6}\s*第二部分\s*", stripped):
            start = idx
            break
        if re.fullmatch(r"#{0,6}\s*对照检查\s*", stripped):
            start = idx
            break

    if start is None:
        return ""

    return "\n".join(lines[start:])


def parse_guide_part(markdown, law_name, source_file):
    part2_markdown = extract_part2(markdown)
    if not part2_markdown:
        print("⚠️ 没找到第二部分")
        return []

    lines = part2_markdown.splitlines()

    guides = []
    current = None
    current_block = None
    current_case = None
    current_case_field = None

    def new_guide(article, title):
        return {
            "id": make_article_id(law_name, article, "第二部分"),
            "type": "guide",
            "part": "第二部分",
            "law_name": law_name,
            "article": article,
            "title": title.strip(),
            "content": "",
            "interpretation": "",
            "check_scope": [],
            "check_method": [],
            "cases": [],
            "source_file": source_file,
        }

    def new_case(title, number=""):
        return {
            "number": number.strip(),
            "title": title.strip(),
            "situation": "",
            "定性": "",
            "处罚": "",
        }

    def flush_case():
        nonlocal current_case, current_case_field
        if current_case is not None and current is not None:
            current["cases"].append(current_case)
        current_case = None
        current_case_field = None

    def flush_guide():
        nonlocal current, current_block
        if current is not None:
            flush_case()
            guides.append(current)
        current = None
        current_block = None

    for raw_line in lines:
        cleaned_line = clean_markdown_line(raw_line, preserve_heading=False)
        stripped = cleaned_line.strip()

        if not stripped:
            continue

        if current_case is not None:
            m = CASE_FIELD_PATTERN.match(stripped)
            if m:
                field = m.group(2)
                value = m.group(3).strip()
                current_case_field = field
                if field == "具体情形":
                    current_case["situation"] = value
                elif field == "行为定性":
                    current_case["定性"] = value
                elif field == "处罚结果":
                    current_case["处罚"] = value
                continue

            if current_case_field == "具体情形":
                current_case["situation"] += "\n" + stripped
            elif current_case_field == "行为定性":
                current_case["定性"] += "\n" + stripped
            elif current_case_field == "处罚结果":
                current_case["处罚"] += "\n" + stripped
            continue

        m = GUIDE_TITLE_PATTERN.match(stripped)
        if m:
            flush_guide()
            article = f"第{m.group(1)}条"
            title = m.group(2)
            current = new_guide(article, title)
            current_block = "content"
            continue

        if current is None:
            continue

        m = GUIDE_BLOCK_PATTERN.match(stripped)
        if m:
            if current_case is not None:
                flush_case()
            name = m.group(1)
            if name == "解读":
                current_block = "interpretation"
            elif name == "检查范围":
                current_block = "check_scope"
            elif name == "检查方法":
                current_block = "check_method"
            continue

        m = CASE_TITLE_PATTERN.match(stripped)
        if m:
            flush_case()
            current_block = "case"
            current_case = new_case(m.group(2), m.group(1))
            current_case_field = None
            continue

        if current_block == "content":
            current["content"] = (
                current["content"] + "\n" + stripped
                if current["content"] else stripped
            )
        elif current_block == "interpretation":
            current["interpretation"] = (
                current["interpretation"] + "\n" + stripped
                if current["interpretation"] else stripped
            )
        elif current_block == "check_scope":
            current["check_scope"].append(stripped)
        elif current_block == "check_method":
            current["check_method"].append(stripped)

    flush_guide()
    return guides


# =========================================================
# 23. 通知：一、二、三、... 解析
# =========================================================

def parse_notice_items(markdown, law_name, source_file):
    lines = markdown.splitlines()

    items = []
    current_number = None
    current_content = []

    def save_current():
        nonlocal current_number, current_content
        if not current_number:
            return

        content = "\n".join(current_content).strip()
        if not content:
            current_number = None
            current_content = []
            return

        items.append({
            "id": make_article_id(law_name, current_number, "通知"),
            "type": "article",
            "part": "通知",
            "law_name": law_name,
            "article": current_number,
            "content": content,
            "source_file": source_file,
        })
        current_number = None
        current_content = []

    for raw_line in lines:
        line = clean_markdown_line(raw_line, preserve_heading=False)
        line = line.strip()
        if not line:
            continue

        m = CN_ITEM_PATTERN.match(line)
        if m:
            save_current()
            current_number = m.group(1)
            current_content = [m.group(2).strip()]
            continue

        if current_number:
            current_content.append(line)

    save_current()
    return items


# =========================================================
# 24. 规程：第X编/章/节 + 第X条 解析
# =========================================================

SECTION_PATTERN = re.compile(
    r"^(第\s*[一二三四五六七八九十百千万零〇0-9]+\s*[编章节])"
    r"(?:\s+(.+))?$"
)


def parse_regulation(markdown, law_name, source_file):
    lines = markdown.splitlines()

    articles = []
    current_article = None
    current_content = []
    current_section = ""

    def save_current():
        nonlocal current_article, current_content, current_section
        if not current_article:
            return

        content = "\n".join(current_content).strip()
        if not content:
            current_article = None
            current_content = []
            return

        data = {
            "id": make_article_id(law_name, current_article, "规程"),
            "type": "article",
            "part": "规程",
            "law_name": law_name,
            "article": current_article,
            "content": content,
            "source_file": source_file,
        }
        if current_section:
            data["section"] = current_section

        articles.append(data)
        current_article = None
        current_content = []

    for raw_line in lines:
        line = clean_markdown_line(raw_line, preserve_heading=False)
        line = line.strip()
        if not line:
            continue

        m = SECTION_PATTERN.match(line)
        if m:
            save_current()
            section_number = re.sub(r"\s+", "", m.group(1))
            section_title = m.group(2)
            if section_title:
                current_section = f"{section_number} {section_title.strip()}"
            else:
                current_section = section_number
            continue

        article, content = parse_article(line)
        if article:
            save_current()
            current_article = article
            current_content = []
            if content:
                current_content.append(content)
            continue

        if current_article:
            current_content.append(line)

    save_current()
    return articles


# =========================================================
# 25. 保存：数组型 articles.json
# =========================================================

def save_articles_json(pdf_path, law_name, all_items):
    pdf_name = safe_filename(Path(pdf_path).stem)
    out_dir = KNOWLEDGE_DIR / pdf_name
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "articles.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print("\n========================================")
    print("✅ 知识库保存成功")
    print(f"📁 {json_path.resolve()}")
    print(f"📊 合计：{len(all_items)} 条")
    print("========================================")

    return json_path


# =========================================================
# 26. 主程序
# =========================================================

def find_pdf_files():
    return sorted(PDF_DIR.glob("*.pdf"))


def main(source_file=None):
    reset_progress(source_file or "")

    print("\n====================================")
    print("       通用法规知识库构建程序")
    print("       阿里云 DocMind 版")
    print("====================================")

    create_directories()

    print("\nPDF目录：")
    print(PDF_DIR.resolve())

    try:
        check_aliyun_config()
    except Exception as e:
        print(f"\n❌ {e}")
        set_progress_field("status", "error")
        set_progress_field("message", str(e))
        return False

    if source_file:
        pdf_path = Path(str(source_file).strip())
        if not pdf_path.is_absolute():
            pdf_path = PDF_DIR / pdf_path
        pdf_path = pdf_path.resolve()

        if not pdf_path.exists():
            print("\n❌ 指定的 PDF 不存在：")
            print(f"实际查找路径：{pdf_path}")
            set_progress_field("status", "error")
            set_progress_field("message", f"PDF 不存在：{pdf_path.name}")
            return False

        if pdf_path.suffix.lower() != ".pdf":
            print("\n❌ 指定文件不是 PDF：")
            print(pdf_path)
            set_progress_field("status", "error")
            set_progress_field("message", f"不是 PDF：{pdf_path.name}")
            return False

        pdf_files = [pdf_path]

        print("\n====================================")
        print("本次为【单 PDF 更新】")
        print(f"当前 PDF：{pdf_path.name}")
        print(f"实际路径：{pdf_path}")
        print("不会处理其他 PDF")
        print("====================================")
    else:
        pdf_files = find_pdf_files()
        if not pdf_files:
            print("\n❌ 没有找到 PDF 文件。")
            print("\n请把法规 PDF 放到：")
            print(PDF_DIR.resolve())
            set_progress_field("status", "error")
            set_progress_field("message", "没有找到 PDF")
            return False

        print(f"\n发现 {len(pdf_files)} 个 PDF：")
        for index, pdf_path in enumerate(pdf_files, start=1):
            try:
                page_count = get_pdf_page_count(pdf_path)
            except Exception:
                page_count = "未知"
            print(f"{index}. {pdf_path.name} [{page_count}页]")

    _load_progress()
    update_progress["total"] = len(pdf_files)
    update_progress["processed"] = 0
    _save_progress()

    success_count = 0
    failed_count = 0

    for index, pdf_path in enumerate(pdf_files, start=1):
        print("\n====================================")
        print(f"正在处理 [{index}/{len(pdf_files)}]")
        print(pdf_path.name)
        print("====================================")

        _load_progress()
        update_progress["current_pdf"] = pdf_path.name
        update_progress["processed"] = index - 1
        update_progress["part_total"] = 0
        update_progress["part_processed"] = 0
        update_progress["page_total"] = 0
        update_progress["page_processed"] = 0
        _save_progress()

        try:
            law_name, all_lines, markdown = extract_pdf(pdf_path)
            print(f"\n识别法规名称：{law_name}")
            print(f"提取文本：{len(all_lines)} 行")

            set_progress("后处理", 30, f"[{pdf_path.name}] 保存原始 TXT...")
            try:
                raw_path = save_raw_txt(pdf_path, all_lines)
                print(f"原始TXT：{raw_path.resolve()}")
            except Exception as e:
                print(f"⚠️ 原始TXT保存失败：{e}")

            set_progress("后处理", 50, f"[{pdf_path.name}] 判断文档类型...")
            doc_type = detect_document_type(markdown)
            print(f"\n文档类型：{doc_type}")

            all_items = []

            if doc_type == "law_book":
                cleaned = clean_text(all_lines)
                print(f"清洗后：{len(cleaned)} 段")

                try:
                    clean_path = save_clean_txt(pdf_path, cleaned)
                    print(f"清洗TXT：{clean_path.resolve()}")
                except Exception as e:
                    print(f"⚠️ 清洗TXT保存失败：{e}")

                part1_articles = build_part1_json(
                    cleaned, law_name, pdf_path.name, part="第一部分",
                )
                part2_guides = parse_guide_part(
                    markdown, law_name, pdf_path.name,
                )
                all_items.extend(part1_articles)
                all_items.extend(part2_guides)
                print(f"第一部分条文：{len(part1_articles)} 条")
                print(f"第二部分对照检查：{len(part2_guides)} 条")

            elif doc_type == "notice_items":
                all_items = parse_notice_items(
                    markdown, law_name, pdf_path.name,
                )
                print(f"通知条文：{len(all_items)} 条")

            elif doc_type == "regulation":
                all_items = parse_regulation(
                    markdown, law_name, pdf_path.name,
                )
                print(f"规程条文：{len(all_items)} 条")

            else:
                print(f"⚠️ 未识别文档类型，跳过：{pdf_path.name}")
                failed_count += 1
                _load_progress()
                update_progress["processed"] = index
                _save_progress()
                continue

            if not all_items:
                print("\n❌ 没有识别到任何条文。")
                failed_count += 1
                _load_progress()
                update_progress["processed"] = index
                _save_progress()
                continue

            set_progress("后处理", 80, f"[{pdf_path.name}] 保存 JSON...")
            save_articles_json(pdf_path, law_name, all_items)

            set_progress("后处理", 100, f"[{pdf_path.name}] 完成")

            print(f"\n✅ PDF处理成功：{pdf_path.name}")
            print(f"   共生成：{len(all_items)} 条知识")

            success_count += 1

        except Exception as e:
            failed_count += 1
            print(f"\n❌ 处理失败：{e}")
            import traceback
            traceback.print_exc()

        _load_progress()
        update_progress["processed"] = index
        _save_progress()

    print("\n====================================")
    print("处理完成")
    print("====================================")
    print(f"成功处理 PDF：{success_count} 个")
    print(f"处理失败 PDF：{failed_count} 个")
    print("\n📁 知识库目录：")
    print(KNOWLEDGE_DIR.resolve())
    print("====================================")

    _load_progress()
    update_progress["status"] = "done"
    update_progress["processed"] = update_progress["total"]
    update_progress["overall_percent"] = 100
    update_progress["stage_percent"] = 100
    update_progress["stage"] = "后处理"
    update_progress["message"] = f"✅ 完成，成功 {success_count} 个"
    _save_progress()

    return success_count > 0


# =========================================================
# 直接运行 build_knowledge.py
# =========================================================

if __name__ == "__main__":
    import sys

    source_file = None

    if len(sys.argv) > 1:
        source_file = sys.argv[1]

    main(source_file=source_file)