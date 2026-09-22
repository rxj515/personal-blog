# -*- coding: utf-8 -*-

"""
法规知识库构建程序（数组输出 articles.json）

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
import zipfile
import tempfile
import shutil
import time
import uuid
from pathlib import Path
from datetime import datetime

import requests
import fitz as pymupdf


# =========================================================
# 1. 目录
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "pdf"
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
BACKUP_DIR = BASE_DIR / "data" / "backup"
RAW_TXT_DIR = BASE_DIR / "data" / "raw_txt"
CLEAN_TXT_DIR = BASE_DIR / "data" / "clean_txt"
MINERU_DIR = BASE_DIR / "data" / "mineru"


# =========================================================
# ⭐ 新增：全局进度（供 /api/knowledge/update/progress 读取）
# =========================================================

update_progress = {
    "total": 0,
    "processed": 0,
    "status": "idle",       # idle | running | done | error
    "message": "",
    "source_file": "",
    "current_pdf": "",
}


def get_progress():
    """返回当前进度（供接口调用）"""
    return update_progress


# =========================================================
# 2. MinerU 配置
# =========================================================

MINERU_TOKEN = os.getenv("MINERU_TOKEN", "").strip()
MINERU_BASE_URL = "https://mineru.net"
MINERU_UPLOAD_URL = f"{MINERU_BASE_URL}/api/v4/file-urls/batch"
MINERU_RESULT_URL = f"{MINERU_BASE_URL}/api/v4/extract-results/batch"

MINERU_MODEL_VERSION = os.getenv("MINERU_MODEL_VERSION", "vlm").strip()
MINERU_IS_OCR = True
MINERU_ENABLE_TABLE = True
MINERU_ENABLE_FORMULA = False
MINERU_LANGUAGE = "ch"

MINERU_MAX_PAGES = 200
MINERU_POLL_INTERVAL = 8
MINERU_MAX_WAIT = 60 * 60
MINERU_HTTP_TIMEOUT = 180
MINERU_RETRY_COUNT = 3


# =========================================================
# 3. 目录创建
# =========================================================

def create_directories():
    for d in [
        PDF_DIR, KNOWLEDGE_DIR, BACKUP_DIR,
        RAW_TXT_DIR, CLEAN_TXT_DIR, MINERU_DIR,
    ]:
        d.mkdir(parents=True, exist_ok=True)


# =========================================================
# 4. 安全文件名
# =========================================================

def safe_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip()
    return name or "未知法规"


# =========================================================
# 5. Token
# =========================================================

def check_mineru_token():
    if not MINERU_TOKEN:
        raise RuntimeError(
            # "\n没有配置 MINERU_TOKEN。\n\n"
            # "Windows CMD：\n"
            # "set MINERU_TOKEN=你的MinerUToken\n\n"
            # "PowerShell：\n"
            # '$env:MINERU_TOKEN="你的MinerUToken"\n'
        )


# =========================================================
# 6. PDF 页数
# =========================================================

def get_pdf_page_count(pdf_path):
    doc = pymupdf.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


# =========================================================
# 7. 重新整理 PDF
# =========================================================

def rebuild_pdf(pdf_path):
    pdf_path = Path(pdf_path)
    print("\n正在重新整理 PDF 文件...")

    source = pymupdf.open(pdf_path)
    try:
        output_dir = MINERU_DIR / "_upload_cache"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / (
            f"{safe_filename(pdf_path.stem)}"
            f"_rebuilt_{uuid.uuid4().hex[:8]}.pdf"
        )

        new_doc = pymupdf.open()
        try:
            new_doc.insert_pdf(source)
            new_doc.save(output_path, garbage=4, deflate=True, clean=True)
        finally:
            new_doc.close()
    finally:
        source.close()

    print(f"重新整理完成：{output_path}")
    return output_path


# =========================================================
# 8. 拆分 PDF
# =========================================================

def split_pdf_for_mineru(pdf_path, max_pages=MINERU_MAX_PAGES):
    pdf_path = Path(pdf_path)
    doc = pymupdf.open(pdf_path)

    try:
        total_pages = len(doc)
        if total_pages <= max_pages:
            return [pdf_path], None

        print(f"\nPDF共 {total_pages} 页，超过 MinerU 单文件 {max_pages} 页限制。")

        temp_dir = Path(tempfile.mkdtemp(prefix="mineru_split_"))
        parts = []

        for start in range(0, total_pages, max_pages):
            end = min(start + max_pages, total_pages)
            part_path = temp_dir / (
                f"{safe_filename(pdf_path.stem)}"
                f"_part_{start + 1}_{end}.pdf"
            )

            part_doc = pymupdf.open()
            try:
                part_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
                part_doc.save(part_path, garbage=4, deflate=True, clean=True)
            finally:
                part_doc.close()

            parts.append(part_path)
            print(f"  已生成：{part_path.name}  [{start + 1}-{end}页]")

        return parts, temp_dir
    finally:
        doc.close()


# =========================================================
# 9. 识别法规名称
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
# 10. 结构行 / 附则 / 附录
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
# 11. 条文编号
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
# 12. 上标 / LaTeX 清理
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
# 13. MinerU：下载
# =========================================================

def download_mineru_zip(zip_url, output_path):
    print("\n正在下载 MinerU 解析结果...")
    response = requests.get(zip_url, timeout=MINERU_HTTP_TIMEOUT)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    print(f"解析结果下载完成：{output_path}")
    print(f"文件大小：{len(response.content) / 1024 / 1024:.2f} MB")
    return output_path


def find_full_markdown(extract_dir):
    candidates = list(extract_dir.rglob("full.md"))
    if not candidates:
        candidates = [
            p for p in extract_dir.rglob("*")
            if p.is_file() and p.name.lower() == "full.md"
        ]
    if not candidates:
        raise RuntimeError("MinerU 解析结果 ZIP 中没有找到 full.md")
    return candidates[0]


def make_mineru_data_id(pdf_path, attempt=1):
    raw = (
        f"{pdf_path.resolve()}|{pdf_path.stat().st_size}|"
        f"{pdf_path.stat().st_mtime_ns}|{attempt}|{uuid.uuid4().hex}"
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# =========================================================
# 14. 上传 / 查询
# =========================================================

def mineru_create_upload_url(pdf_path, attempt=1):
    check_mineru_token()
    data_id = make_mineru_data_id(pdf_path, attempt)

    headers = {
        "Authorization": f"Bearer {MINERU_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    data = {
        "files": [{
            "name": pdf_path.name,
            "data_id": data_id,
            "is_ocr": MINERU_IS_OCR,
        }],
        "model_version": MINERU_MODEL_VERSION,
        "language": MINERU_LANGUAGE,
        "enable_table": MINERU_ENABLE_TABLE,
        "enable_formula": MINERU_ENABLE_FORMULA,
    }

    print("\n正在申请 MinerU 上传地址...")
    response = requests.post(
        MINERU_UPLOAD_URL, headers=headers, json=data,
        timeout=MINERU_HTTP_TIMEOUT,
    )
    print(f"HTTP状态码：{response.status_code}")

    if response.status_code != 200:
        raise RuntimeError(
            f"MinerU 获取上传地址失败：\nHTTP：{response.status_code}\n"
            f"{response.text[:2000]}"
        )

    result = response.json()
    if result.get("code") != 0:
        raise RuntimeError(
            "MinerU 获取上传地址失败：\n"
            + json.dumps(result, ensure_ascii=False, indent=2)
        )

    data_result = result.get("data") or {}
    batch_id = data_result.get("batch_id")
    file_urls = data_result.get("file_urls")

    if not batch_id or not file_urls:
        raise RuntimeError(
            "MinerU 没有返回 batch_id/file_urls：\n"
            + json.dumps(result, ensure_ascii=False, indent=2)
        )

    return batch_id, file_urls[0]


def mineru_upload_file(pdf_path, upload_url):
    print("\n正在上传 PDF 到 MinerU...")
    print(f"文件：{pdf_path.name}")
    print(f"大小：{pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

    with open(pdf_path, "rb") as f:
        response = requests.put(
            upload_url, data=f, timeout=MINERU_HTTP_TIMEOUT,
        )

    print(f"上传HTTP状态：{response.status_code}")
    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"MinerU PDF 上传失败。\nHTTP状态码：{response.status_code}\n"
            f"返回：{response.text[:2000]}"
        )
    print("PDF 上传成功。")


def mineru_query_batch(batch_id):
    headers = {
        "Authorization": f"Bearer {MINERU_TOKEN}",
        "Accept": "application/json",
    }
    url = f"{MINERU_RESULT_URL}/{batch_id}"
    response = requests.get(url, headers=headers, timeout=MINERU_HTTP_TIMEOUT)
    response.raise_for_status()
    result = response.json()

    if result.get("code") != 0:
        raise RuntimeError(
            "MinerU 查询任务失败：\n"
            + json.dumps(result, ensure_ascii=False, indent=2)
        )
    return result


def mineru_wait_result(batch_id):
    print("\n等待 MinerU 解析...")
    start_time = time.time()
    last_state = None

    while True:
        elapsed = time.time() - start_time
        if elapsed > MINERU_MAX_WAIT:
            raise TimeoutError(
                f"MinerU 解析等待超过 {MINERU_MAX_WAIT // 60} 分钟。"
            )

        result = mineru_query_batch(batch_id)
        data = result.get("data") or {}
        extract_results = data.get("extract_result") or []

        if not extract_results:
            print("MinerU 尚未返回任务状态，稍后重试...")
            time.sleep(MINERU_POLL_INTERVAL)
            continue

        item = extract_results[0]
        state = item.get("state", "")
        progress = item.get("extract_progress") or {}
        extracted_pages = progress.get("extracted_pages")
        total_pages = progress.get("total_pages")

        elapsed_text = f"{int(elapsed) // 60:02d}:{int(elapsed) % 60:02d}"

        # ⭐ 新增：把 MinerU 内部页数进度同步到全局 message
        if extracted_pages is not None and total_pages is not None:
            pct = int(extracted_pages / max(1, total_pages) * 100)
            update_progress["message"] = (
                f"[{update_progress.get('current_pdf', '')}] "
                f"MinerU 解析 {extracted_pages}/{total_pages} 页 ({pct}%)"
            )

        if state != last_state:
            if extracted_pages is not None and total_pages is not None:
                print(f"[{elapsed_text}] 状态：{state} {extracted_pages}/{total_pages}")
            else:
                print(f"[{elapsed_text}] 状态：{state}")
            last_state = state

        if state == "done":
            zip_url = item.get("full_zip_url")
            if not zip_url:
                raise RuntimeError(
                    "MinerU 已完成，但没有返回 full_zip_url：\n"
                    + json.dumps(item, ensure_ascii=False, indent=2)
                )
            print("\nMinerU 解析完成！")
            return zip_url

        if state == "failed":
            error_message = item.get("err_msg") or "未知错误"
            raise RuntimeError(f"MinerU 解析失败：\n{error_message}")

        time.sleep(MINERU_POLL_INTERVAL)


def download_and_extract_mineru_result(zip_url, pdf_path, output_name):
    pdf_output_dir = (
        MINERU_DIR / safe_filename(pdf_path.stem) / safe_filename(output_name)
    )
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = pdf_output_dir / "mineru_result.zip"
    download_mineru_zip(zip_url, zip_path)

    extract_dir = pdf_output_dir / "result"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    print("\n正在解压 MinerU 结果...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    markdown_path = find_full_markdown(extract_dir)
    print("\n找到 Markdown：")
    print(markdown_path)

    markdown_text = markdown_path.read_text(encoding="utf-8")
    final_md_path = pdf_output_dir / "full.md"
    final_md_path.write_text(markdown_text, encoding="utf-8")
    print(f"Markdown保存：{final_md_path}")

    return markdown_text


def parse_one_pdf_by_mineru(pdf_path, output_name):
    last_error = None
    current_pdf = Path(pdf_path)

    for attempt in range(1, MINERU_RETRY_COUNT + 1):
        print("\n----------------------------------------")
        print(f"MinerU 第 {attempt}/{MINERU_RETRY_COUNT} 次尝试")
        print(f"文件：{current_pdf.name}")
        print("----------------------------------------")

        try:
            batch_id, upload_url = mineru_create_upload_url(current_pdf, attempt)
            print(f"Batch ID：{batch_id}")

            mineru_upload_file(current_pdf, upload_url)
            zip_url = mineru_wait_result(batch_id)

            return download_and_extract_mineru_result(
                zip_url, Path(pdf_path), output_name,
            )
        except Exception as e:
            last_error = e
            print(f"\n⚠️ 第 {attempt} 次 MinerU 处理失败：")
            print(str(e))

            if attempt >= MINERU_RETRY_COUNT:
                break

            print("\n准备重新生成 PDF 后再次上传...")
            try:
                rebuilt = rebuild_pdf(current_pdf)
                current_pdf = rebuilt
            except Exception as rebuild_error:
                print(f"重新生成 PDF 失败：{rebuild_error}")

            time.sleep(3)

    raise RuntimeError(
        f"MinerU 多次解析失败。\n最后一次错误：{last_error}"
    )


# =========================================================
# 14.5 合并分片 + 去重
# =========================================================

def merge_markdown_parts(markdown_parts):
    if not markdown_parts:
        return ""

    merged_lines = []
    seen_blocks = set()
    current_block = []
    current_title = ""

    def flush_block():
        nonlocal current_block, current_title
        if not current_block:
            return

        block_text = "\n".join(current_block).strip()
        if not block_text:
            current_block = []
            current_title = ""
            return

        key = (current_title, block_text[:80])

        if key in seen_blocks:
            print(f"⚠️ 跳过重复块：{current_title[:40]}")
        else:
            seen_blocks.add(key)
            merged_lines.extend(current_block)
            merged_lines.append("")

        current_block = []
        current_title = ""

    for markdown in markdown_parts:
        if not markdown:
            continue
        for line in markdown.splitlines():
            stripped = line.strip()

            if (
                stripped.startswith("## ")
                or stripped.startswith("（")
                or stripped.startswith("(")
                or stripped.startswith("【典型案例")
                or stripped.startswith("## ◆")
                or stripped.startswith("◆")
                or stripped.startswith("♦")
            ):
                flush_block()
                current_title = stripped[:80]

            current_block.append(line)

        flush_block()

    return "\n".join(merged_lines)


def deduplicate_markdown(markdown):
    if not markdown:
        return markdown

    lines = markdown.splitlines()
    result = []
    seen_blocks = set()
    current_block = []
    current_title = ""

    def flush_block():
        nonlocal current_block, current_title
        if not current_block:
            return

        block_text = "\n".join(current_block).strip()
        if not block_text:
            current_block = []
            current_title = ""
            return

        key = (current_title, block_text[:80])

        if key in seen_blocks:
            print(f"⚠️ 跳过重复块：{current_title[:30]}")
        else:
            seen_blocks.add(key)
            result.extend(current_block)
            result.append("")

        current_block = []
        current_title = ""

    for line in lines:
        stripped = line.strip()

        if (
            stripped.startswith("## ")
            or stripped.startswith("（")
            or stripped.startswith("(")
            or stripped.startswith("【典型案例")
            or stripped.startswith("## ◆")
            or stripped.startswith("◆")
        ):
            flush_block()
            current_title = stripped[:60]

        current_block.append(line)

    flush_block()

    return "\n".join(result)


def parse_pdf_by_mineru(pdf_path):
    print("\n========================================")
    print("开始调用 MinerU API")
    print("========================================")

    check_mineru_token()

    page_count = get_pdf_page_count(pdf_path)
    print(f"PDF页数：{page_count}")
    print(f"MinerU模型：{MINERU_MODEL_VERSION}")
    print(f"OCR：{MINERU_IS_OCR}")
    print(f"中文：{MINERU_LANGUAGE}")
    print(f"单文件最大页数：{MINERU_MAX_PAGES}")

    parts = []
    temp_dir = None
    try:
        parts, temp_dir = split_pdf_for_mineru(pdf_path, MINERU_MAX_PAGES)
        print(f"\n本次 MinerU 实际处理 {len(parts)} 个文件")

        markdown_parts = []
        for index, part_path in enumerate(parts, start=1):
            print("\n========================================")
            print(f"处理 PDF 分片 [{index}/{len(parts)}]")
            print(part_path.name)
            print("========================================")

            markdown = parse_one_pdf_by_mineru(part_path, f"part_{index}")
            markdown_parts.append(markdown)

        markdown = merge_markdown_parts(markdown_parts)
        markdown = deduplicate_markdown(markdown)

        final_output_dir = MINERU_DIR / safe_filename(pdf_path.stem)
        final_output_dir.mkdir(parents=True, exist_ok=True)

        final_md_path = final_output_dir / "full.md"
        final_md_path.write_text(markdown, encoding="utf-8")

        print("\n========================================")
        print("MinerU 全部解析完成")
        print(f"Markdown：{final_md_path}")
        print("========================================")

        return markdown
    finally:
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


# =========================================================
# 15. 文本行
# =========================================================

def extract_pdf(pdf_path):
    print("\n正在读取：")
    print(pdf_path)

    markdown = parse_pdf_by_mineru(pdf_path)

    law_name = detect_law_name_from_markdown(markdown, pdf_path)
    print(f"\n识别法规名称：{law_name}")

    lines = []
    for raw_line in markdown.splitlines():
        line = clean_markdown_line(raw_line, preserve_heading=True)
        if not line:
            continue
        lines.append(line)

    lines = remove_page_number(lines)
    print(f"MinerU返回文本：{len(lines)} 行")

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
# 16. 唯一 ID（加 part）
# =========================================================

def make_article_id(law_name, article, part=""):
    raw = f"{law_name}_{part}_{article}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# =========================================================
# 17. 文档类型判断
# =========================================================

CN_ITEM_PATTERN = re.compile(
    r"^([一二三四五六七八九十百零〇]+)\s*[、.，,]\s*(.+)$"
)


def detect_document_type(markdown):
    """
    law_book     → 有第一部分 + 第二部分
    notice_items → 有 5 个以上的 一、二、三、……
    regulation   → 有 50 个以上的 第X条
    unknown      → 都不是
    """
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
# 18. 第一部分：清洗 + JSON
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
# 19. 第二部分：对照检查解析
# =========================================================

# 只认 ## 第X条【标题】，不认别的
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

        # 0. 案例内部优先
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

        # 1. ## 第X条【标题】
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

        # 2. 解读 / 检查范围 / 检查方法
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

        # 3. 典型案例
        m = CASE_TITLE_PATTERN.match(stripped)
        if m:
            flush_case()
            current_block = "case"
            current_case = new_case(m.group(2), m.group(1))
            current_case_field = None
            continue

        # 4. 续行
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
# 20. 通知：一、二、三、... 解析
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
# 21. 规程：第X编/章/节 + 第X条 解析
# =========================================================

# 匹配 “第一编 总则”、“第一章 设计及井巷布置”、“第一节 一般规定”
SECTION_PATTERN = re.compile(
    r"^(第\s*[一二三四五六七八九十百千万零〇0-9]+\s*[编章节])"
    r"(?:\s+(.+))?$"
)


def parse_regulation(markdown, law_name, source_file):
    """
    解析“第X编/章/节 + 第X条”形式的长篇法规。
    """
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

        # 编 / 章 / 节
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

        # 第X条
        article, content = parse_article(line)
        if article:
            save_current()
            current_article = article
            current_content = []
            if content:
                current_content.append(content)
            continue

        # 续行
        if current_article:
            current_content.append(line)

    save_current()
    return articles


# =========================================================
# 22. 保存：数组型 articles.json
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
# 23. 主程序
# =========================================================

def find_pdf_files():
    return sorted(PDF_DIR.glob("*.pdf"))


def main(source_file=None):
    # ⭐ 新增：初始化全局进度
    global update_progress
    update_progress = {
        "total": 0,
        "processed": 0,
        "status": "running",
        "message": f"开始处理 {source_file or '全部'}",
        "source_file": source_file or "",
        "current_pdf": "",
    }

    print("\n====================================")
    print("       通用法规知识库构建程序")
    print("       MinerU API 版（数组输出）")
    print("====================================")

    create_directories()

    print("\nPDF目录：")
    print(PDF_DIR.resolve())

    # =====================================================
    # 检查 MinerU Token
    # =====================================================
    try:
        check_mineru_token()
    except Exception as e:
        print(f"\n❌ {e}")
        # ⭐ 新增：标记错误
        update_progress["status"] = "error"
        update_progress["message"] = str(e)
        return False

    # =====================================================
    # 确定本次需要处理的 PDF
    #
    # source_file 有值：
    #     只处理当前指定的 PDF
    #
    # source_file 没有值：
    #     才处理 pdf 目录下的全部 PDF
    # =====================================================

    if source_file:
        # -------------------------------------------------
        # 单 PDF 更新模式
        # -------------------------------------------------
        pdf_path = Path(str(source_file).strip())

        # -------------------------------------------------
        # 如果传进来的是文件名：
        #
        # 山西统筹煤炭安全新规通知.pdf
        #
        # 那么必须去：
        #
        # D:\personal-blog\topic\pdf\
        #
        # 里面找
        # -------------------------------------------------
        if not pdf_path.is_absolute():
            pdf_path = PDF_DIR / pdf_path

        pdf_path = pdf_path.resolve()

        # -------------------------------------------------
        # 检查 PDF 是否存在
        # -------------------------------------------------
        if not pdf_path.exists():
            print("\n❌ 指定的 PDF 不存在：")
            print(f"实际查找路径：{pdf_path}")

            print("\nPDF目录：")
            print(PDF_DIR.resolve())

            # ⭐ 新增：标记错误
            update_progress["status"] = "error"
            update_progress["message"] = f"PDF 不存在：{pdf_path.name}"
            return False

        # -------------------------------------------------
        # 检查是否为 PDF
        # -------------------------------------------------
        if pdf_path.suffix.lower() != ".pdf":
            print("\n❌ 指定文件不是 PDF：")
            print(pdf_path)

            # ⭐ 新增：标记错误
            update_progress["status"] = "error"
            update_progress["message"] = f"不是 PDF：{pdf_path.name}"
            return False

        # -------------------------------------------------
        # 单 PDF 模式
        # -------------------------------------------------
        pdf_files = [pdf_path]

        print("\n====================================")
        print("本次为【单 PDF 更新】")
        print(f"当前 PDF：{pdf_path.name}")
        print(f"实际路径：{pdf_path}")
        print("不会处理其他 PDF")
        print("====================================")

    else:
        # =================================================
        # 没有指定 PDF
        # 才扫描整个 pdf 目录
        # =================================================
        pdf_files = find_pdf_files()

        if not pdf_files:
            print("\n❌ 没有找到 PDF 文件。")

            print("\n请把法规 PDF 放到：")
            print(PDF_DIR.resolve())

            # ⭐ 新增：标记错误
            update_progress["status"] = "error"
            update_progress["message"] = "没有找到 PDF"
            return False

        print(f"\n发现 {len(pdf_files)} 个 PDF：")

        for index, pdf_path in enumerate(
            pdf_files,
            start=1
        ):
            try:
                page_count = get_pdf_page_count(
                    pdf_path
                )
            except Exception:
                page_count = "未知"

            print(
                f"{index}. {pdf_path.name} "
                f"[{page_count}页]"
            )

    # ⭐ 新增：设置总进度 = PDF 数量
    update_progress["total"] = len(pdf_files)
    update_progress["processed"] = 0

    # =====================================================
    # 开始处理 PDF
    # =====================================================

    success_count = 0
    failed_count = 0

    for index, pdf_path in enumerate(
        pdf_files,
        start=1
    ):

        print("\n====================================")
        print(
            f"正在处理 [{index}/{len(pdf_files)}]"
        )
        print(pdf_path.name)
        print("====================================")

        # ⭐ 新增：更新当前正在处理的 PDF
        update_progress["current_pdf"] = pdf_path.name
        update_progress["message"] = f"[{pdf_path.name}] 开始解析"

        try:

            # -------------------------------------------------
            # 1. MinerU 解析当前 PDF
            # -------------------------------------------------

            law_name, all_lines, markdown = extract_pdf(
                pdf_path
            )

            print(
                f"\n识别法规名称：{law_name}"
            )

            print(
                f"提取文本：{len(all_lines)} 行"
            )

            # ⭐ 新增：更新阶段
            update_progress["message"] = f"[{pdf_path.name}] 保存原始 TXT"

            # -------------------------------------------------
            # 2. 保存原始 TXT
            # -------------------------------------------------

            try:

                raw_path = save_raw_txt(
                    pdf_path,
                    all_lines
                )

                print(
                    f"原始TXT：{raw_path.resolve()}"
                )

            except Exception as e:

                print(
                    f"⚠️ 原始TXT保存失败：{e}"
                )

            # -------------------------------------------------
            # 3. 判断文档类型
            # -------------------------------------------------

            # ⭐ 新增：更新阶段
            update_progress["message"] = f"[{pdf_path.name}] 判断文档类型"

            doc_type = detect_document_type(
                markdown
            )

            print(
                f"\n文档类型：{doc_type}"
            )

            all_items = []

            # -------------------------------------------------
            # 4. 法规书
            # -------------------------------------------------

            if doc_type == "law_book":

                cleaned = clean_text(
                    all_lines
                )

                print(
                    f"清洗后：{len(cleaned)} 段"
                )

                try:

                    clean_path = save_clean_txt(
                        pdf_path,
                        cleaned
                    )

                    print(
                        f"清洗TXT："
                        f"{clean_path.resolve()}"
                    )

                except Exception as e:

                    print(
                        f"⚠️ 清洗TXT保存失败：{e}"
                    )

                part1_articles = build_part1_json(
                    cleaned,
                    law_name,
                    pdf_path.name,
                    part="第一部分",
                )

                part2_guides = parse_guide_part(
                    markdown,
                    law_name,
                    pdf_path.name,
                )

                all_items.extend(
                    part1_articles
                )

                all_items.extend(
                    part2_guides
                )

                print(
                    f"第一部分条文："
                    f"{len(part1_articles)} 条"
                )

                print(
                    f"第二部分对照检查："
                    f"{len(part2_guides)} 条"
                )

            # -------------------------------------------------
            # 5. 通知
            # -------------------------------------------------

            elif doc_type == "notice_items":

                all_items = parse_notice_items(
                    markdown,
                    law_name,
                    pdf_path.name,
                )

                print(
                    f"通知条文："
                    f"{len(all_items)} 条"
                )

            # -------------------------------------------------
            # 6. 规程
            # -------------------------------------------------

            elif doc_type == "regulation":

                all_items = parse_regulation(
                    markdown,
                    law_name,
                    pdf_path.name,
                )

                print(
                    f"规程条文："
                    f"{len(all_items)} 条"
                )

            # -------------------------------------------------
            # 7. 未识别
            # -------------------------------------------------

            else:

                print(
                    f"⚠️ 未识别文档类型，跳过："
                    f"{pdf_path.name}"
                )

                failed_count += 1

                # ⭐ 新增：跳过也要推进进度
                update_progress["processed"] = index
                continue

            # -------------------------------------------------
            # 8. 没有解析出条文
            # -------------------------------------------------

            if not all_items:

                print(
                    "\n❌ 没有识别到任何条文。"
                )

                failed_count += 1

                # ⭐ 新增：跳过也要推进进度
                update_progress["processed"] = index
                continue

            # -------------------------------------------------
            # 9. 保存 articles.json
            # -------------------------------------------------

            # ⭐ 新增：更新阶段
            update_progress["message"] = f"[{pdf_path.name}] 保存 JSON"

            save_articles_json(
                pdf_path,
                law_name,
                all_items
            )

            print(
                f"\n✅ PDF处理成功："
                f"{pdf_path.name}"
            )

            print(
                f"   共生成："
                f"{len(all_items)} 条知识"
            )

            success_count += 1

        except Exception as e:

            failed_count += 1

            print(
                f"\n❌ 处理失败：{e}"
            )

            import traceback

            traceback.print_exc()

        # ⭐ 新增：每个 PDF 处理完（无论成功失败）推进进度
        update_progress["processed"] = index

    # =====================================================
    # 处理结果
    # =====================================================

    print("\n====================================")
    print("处理完成")
    print("====================================")

    print(
        f"成功处理 PDF："
        f"{success_count} 个"
    )

    print(
        f"处理失败 PDF："
        f"{failed_count} 个"
    )

    print("\n📁 知识库目录：")

    print(
        KNOWLEDGE_DIR.resolve()
    )

    print("====================================")

    # ⭐ 新增：标记完成
    update_progress["status"] = "done"
    update_progress["processed"] = update_progress["total"]
    update_progress["message"] = f"✅ 完成，成功 {success_count} 个"

    # =====================================================
    # 返回结果
    #
    # 单 PDF 更新：
    #     成功 -> True
    #     失败 -> False
    #
    # 全量处理：
    #     只要有一个成功就算本次有成功
    # =====================================================

    if success_count > 0:
        return True

    return False


# =========================================================
# 直接运行 build_knowledge.py 时
# =========================================================

if __name__ == "__main__":
    import sys

    # -----------------------------------------------------
    # 命令行启动方式：
    #
    # python build_knowledge.py
    #
    # = 处理全部 PDF
    #
    #
    # python build_knowledge.py xxx.pdf
    #
    # = 只处理指定 PDF
    # -----------------------------------------------------

    source_file = None

    if len(sys.argv) > 1:
        source_file = sys.argv[1]

    main(source_file=source_file)