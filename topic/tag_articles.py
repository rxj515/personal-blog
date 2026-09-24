# -*- coding: utf-8 -*-

"""
打标签脚本（长条文分段 + 多标签 + 树节点直出）

流程：
    1. 从 study_dept_bank_type.xlsx 读树节点名（作为 AI 可选列表）
    2. 读 data/knowledge/<PDF名>/articles.json
    3. 对每条 type == "article" 或 "guide" 的条目打标签
    4. 短条文（≤1500 字）：15 条一批，一次调 AI
    5. 长条文（>1500 字）：按（一）（二）（三）切段，逐段调 AI，合并标签
    6. 标签数量不设上限
    7. 写回 dept_type_name（数组）和 dept_type_name_str（字符串）

不再使用大类（采煤类/掘进类等），AI 直接输出树节点名。
"""

import json
import requests
import re
from pathlib import Path
import time

import pandas as pd


# ============================================================
# 1. 自动读取 AI 配置
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
config_file = BASE_DIR / "config" / "ai_config.json"

with open(config_file, "r", encoding="utf-8") as f:
    ai_config = json.load(f)

AI_API_URL = ai_config.get("base_url", "https://api.deepseek.com/v1") + "/chat/completions"
AI_MODEL = ai_config.get("model", "deepseek-chat")
AI_API_KEY = ai_config.get("api_key", "")

print(f"AI 接口地址: {AI_API_URL}")
print(f"AI 模型: {AI_MODEL}")

KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
EXCEL_PATH = BASE_DIR / "data" / "study_dept_bank_type.xlsx"


# ============================================================
# 2. ✅ 从 Excel 读取所有树节点名
# ============================================================

def load_all_nodes_from_excel():
    """
    从 Excel 读取所有节点名（去重），作为 AI 的可选标签列表。
    """
    if not EXCEL_PATH.exists():
        print(f"❌ 找不到 Excel：{EXCEL_PATH}")
        return []

    df = pd.read_excel(EXCEL_PATH)
    df = df.fillna("")

    if "name" not in df.columns:
        print(f"❌ Excel 里没有 'name' 列")
        return []

    nodes = []
    seen = set()

    for name in df["name"].astype(str):
        name = name.strip()
        if not name:
            continue
        if name in seen:
            continue
        seen.add(name)
        nodes.append(name)

    return nodes


ALL_NODES = load_all_nodes_from_excel()

print(f"✅ 从 Excel 读到 {len(ALL_NODES)} 个树节点")

# 用于校验 AI 输出的合法节点
VALID_NODES = set(ALL_NODES)

# 长条文阈值
LONG_TEXT_THRESHOLD = 1500
SEGMENT_MAX_LEN = 1200
BATCH_SIZE = 15


# ============================================================
# 3. ⭐ 全局进度（文件存储，兼容多 worker / --reload）
# ============================================================

TAG_PROGRESS_FILE = BASE_DIR / "data" / "tag_progress.json"

_DEFAULT_TAG_PROGRESS = {
    "total": 0,
    "processed": 0,
    "status": "idle",        # idle | running | done | error
    "message": "",
    "source_file": "",
    "current_article": "",
    "current_pdf": "",
    "overall_percent": 0,
    "stage": "",
    "stage_percent": 0,
    "part_total": 0,
    "part_processed": 0,
    "page_total": 0,
    "page_processed": 0,
}

tag_progress = dict(_DEFAULT_TAG_PROGRESS)


def _save_tag_progress():
    try:
        TAG_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        TAG_PROGRESS_FILE.write_text(
            json.dumps(tag_progress, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"⚠️ 写打标签进度文件失败：{e}")


def _load_tag_progress():
    global tag_progress
    try:
        if TAG_PROGRESS_FILE.exists():
            data = json.loads(TAG_PROGRESS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in _DEFAULT_TAG_PROGRESS.items():
                    data.setdefault(k, v)
                tag_progress.clear()
                tag_progress.update(data)
                return
    except Exception as e:
        print(f"⚠️ 读打标签进度文件失败：{e}")

    tag_progress.clear()
    tag_progress.update(_DEFAULT_TAG_PROGRESS)


def get_tag_progress():
    """供接口调用：每次从文件读最新"""
    _load_tag_progress()
    return dict(tag_progress)


def reset_tag_progress(source_file=""):
    """重置进度并写文件"""
    tag_progress.clear()
    tag_progress.update(dict(_DEFAULT_TAG_PROGRESS))
    tag_progress["status"] = "running"
    tag_progress["message"] = (
        f"准备给 {source_file} 打标签" if source_file else "准备打标签"
    )
    tag_progress["source_file"] = source_file or ""
    tag_progress["stage"] = "准备"
    _save_tag_progress()


def set_tag_progress(stage, stage_percent, message="", **extra):
    """
    统一设置进度（自动写文件）。

    阶段权重：
        准备          → 0%   ~ 5%
        AI 打标签     → 5%   ~ 95%
        后处理        → 95%  ~ 100%
    """
    stage_percent = max(0.0, min(100.0, float(stage_percent)))

    if stage == "准备":
        overall = stage_percent * 0.05
    elif stage == "AI 打标签":
        overall = 5 + stage_percent * 0.90
    elif stage == "后处理":
        overall = 95 + stage_percent * 0.05
    else:
        overall = stage_percent

    tag_progress["stage"] = stage
    tag_progress["stage_percent"] = round(stage_percent, 1)
    tag_progress["overall_percent"] = round(min(100.0, overall), 1)
    if message:
        tag_progress["message"] = message
    for k, v in extra.items():
        tag_progress[k] = v

    _save_tag_progress()


def set_tag_progress_field(key, value):
    """单字段更新（自动写文件）"""
    tag_progress[key] = value
    _save_tag_progress()


def get_progress():
    """兼容旧接口"""
    return get_tag_progress()


# ============================================================
# 4. AI 调用
# ============================================================

def ai_call(prompt):
    """调用 AI 接口"""
    try:
        response = requests.post(
            AI_API_URL,
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的煤矿安全法规分类助手。只返回分类结果，不要输出其他内容。"
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            },
            timeout=600
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"AI调用失败：{e}")
        return None


# ============================================================
# 5. 长文本切段
# ============================================================

def split_long_text(text, max_len=SEGMENT_MAX_LEN):
    if not text:
        return [""]

    if len(text) <= max_len:
        return [text]

    parts = re.split(r'(?=（[一二三四五六七八九十百零〇0-9]+）)', text)

    segments = []
    current = ""

    for part in parts:
        if not part.strip():
            continue

        if len(current) + len(part) <= max_len:
            current += part
        else:
            if current:
                segments.append(current)
            current = part

    if current:
        segments.append(current)

    final_segments = []
    for seg in segments:
        if len(seg) <= max_len * 2:
            final_segments.append(seg)
        else:
            for i in range(0, len(seg), max_len):
                final_segments.append(seg[i:i + max_len])

    return final_segments or [text]


# ============================================================
# 6. ✅ 构建 Prompt（节点名清单喂给 AI）
# ============================================================

def build_node_list_text():
    """把节点名拼成一段文本，用于 prompt"""
    lines = []
    for i in range(0, len(ALL_NODES), 8):
        chunk = ALL_NODES[i:i + 8]
        lines.append("、".join(chunk))
    return "\n".join(lines)


NODE_LIST_TEXT = build_node_list_text()


def build_prompt_for_batch(batch_data):
    """
    构建批量 prompt（短条文）。
    """
    batch_content = ""

    for i, idx, item, segments in batch_data:
        section = item.get("section", "")
        content = item.get("content", "")

        line = f"{i}. "
        if section:
            line += f"[{section}] "
        line += content[:1500]

        batch_content += line + "\n\n"

    prompt = f"""
请判断以下法条内容分别涉及哪些岗位或队（可以多选，没有数量限制）。

【可选标签列表】（只能从下列节点名里选，不能自创）：
{NODE_LIST_TEXT}

【说明】
- 综采、综采一队、采煤队、综采公共题目 → 采煤相关
- 掘进开拓、掘进队、掘进二队、掘进公共题目 → 掘进相关
- 运输、运输队、运输公共题目 → 运输相关
- 机电、机电运输、机电队、机运队、地面机电队、机电公共题目 → 机电相关
- 通风、通风队、通风公共题目、一通三防部 → 通风相关
- 安全、安监部、安监科、安全监管部、安全公共题目、教育培训部、培训科 → 安全相关
- 抽采、探水、探水队、地质防治水部 → 抽采/探水
- 监控信息、监控中心、监控公共题目 → 监控相关
- 各岗位（采煤机司机、爆破员、瓦斯员等）→ 按岗位职责判断

【法条内容】
{batch_content}

【返回格式】
每个法条一行，格式为"序号:节点1,节点2,..."：
1:综采一队,采煤机司机
2:通风队,安全
3:掘进二队,爆破员,安全
4:安监部门,安全公共题目

【注意】
1. 必须为每个法条都返回结果，序号从1到{len(batch_data)}
2. 只能从上述可选标签列表中选择，不能自创节点名
3. 每个法条可以返回 1 个或多个节点，用英文逗号分隔，能打几个就打几个
4. 只打真正相关的，不确定的不要打
5. 如果无法判断，返回"鑫隆煤业"
6. 不要输出其他任何内容
"""
    return prompt


def build_prompt_for_segment(item, segment, segment_index, total_segments):
    """
    构建单段 prompt（长条文）。
    """
    section = item.get("section", "")
    header = ""
    if section:
        header += f"[{section}] "
    if total_segments > 1:
        header += f"（第 {segment_index}/{total_segments} 段）"

    prompt = f"""
请判断以下法条片段涉及哪些岗位或队（可以多选，没有数量限制）。

【可选标签列表】（只能从下列节点名里选，不能自创）：
{NODE_LIST_TEXT}

{header}
【法条片段】
{segment}

【返回格式】
只返回一行，格式为"节点1,节点2,..."：
综采一队,采煤机司机,安全

【注意】
1. 只能从上述可选标签列表中选择，不能自创节点名
2. 可以返回 1 个或多个节点，用英文逗号分隔
3. 只打真正相关的，不确定的不要打
4. 如果无法判断，返回"鑫隆煤业"
5. 不要输出其他任何内容
"""
    return prompt


# ============================================================
# 7. 解析 AI 返回
# ============================================================

def match_node(part):
    """
    从 AI 返回的一段文字里，匹配出合法的节点名。
    """
    part = part.strip()
    if not part:
        return None

    if part in VALID_NODES:
        return part

    best = None
    for node in VALID_NODES:
        if node in part:
            if best is None or len(node) > len(best):
                best = node

    return best


def parse_ai_response_for_batch(result, batch_data):
    """
    解析批量返回。
    """
    results = {}

    if result is None:
        for i, idx, item, segments in batch_data:
            results[idx] = ["鑫隆煤业"]
        return results

    lines = result.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(
            r'^(?:第)?\s*(\d+)\s*[条]?\s*[：:.、\s]\s*(.+)$',
            line,
        )
        if not match:
            continue

        num = int(match.group(1))
        node_text = match.group(2).strip()

        parts = re.split(r'[,，、;；\s]+', node_text)

        matched_nodes = []

        for part in parts:
            node = match_node(part)
            if node and node not in matched_nodes:
                matched_nodes.append(node)

        if not matched_nodes:
            matched_nodes = ["鑫隆煤业"]

        for i, idx, item, segments in batch_data:
            if i == num:
                if idx not in results:
                    results[idx] = []
                for tag in matched_nodes:
                    if tag not in results[idx]:
                        results[idx].append(tag)
                break

    for i, idx, item, segments in batch_data:
        if idx not in results:
            results[idx] = ["鑫隆煤业"]

    return results


def parse_segment_tags(result):
    """
    解析单段返回。
    """
    if not result:
        return ["鑫隆煤业"]

    result = result.strip()
    result = re.sub(r'^(?:节点|分类|结果|答案|标签)\s*[：:]\s*', '', result)

    parts = re.split(r'[,，、;；\s]+', result)

    matched_nodes = []

    for part in parts:
        node = match_node(part)
        if node and node not in matched_nodes:
            matched_nodes.append(node)

    return matched_nodes or ["鑫隆煤业"]


# ============================================================
# 8. 长条文处理
# ============================================================

def process_long_article(idx, item):
    content = item.get("content", "")
    segments = split_long_text(content)
    total_segments = len(segments)

    print(f"   🔍 长条文 {item.get('article', '')}：{len(content)} 字，切成 {total_segments} 段")

    all_tags = []

    for seg_idx, segment in enumerate(segments, 1):
        prompt = build_prompt_for_segment(item, segment, seg_idx, total_segments)
        result = ai_call(prompt)
        tags = parse_segment_tags(result)

        for tag in tags:
            if tag not in all_tags:
                all_tags.append(tag)

        print(f"      段 {seg_idx}/{total_segments} → {tags}")

        time.sleep(0.3)

    if not all_tags:
        all_tags = ["鑫隆煤业"]

    print(f"   ✅ 长条文 {item.get('article', '')} 最终标签：{all_tags}")

    return all_tags


# ============================================================
# 9. 处理单个知识库
# ============================================================

def process_single_knowledge(json_path, knowledge_name):
    """
    ⭐ 内部会更新全局 tag_progress
    """
    global tag_progress

    print()
    print("=" * 60)
    print(f"📄 处理知识库：{knowledge_name}")
    print("=" * 60)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            articles = json.load(f)

        if not isinstance(articles, list):
            print(f"   ⚠️ 数据格式不是数组，跳过")
            return {"success": False, "count": 0}

        total = len(articles)
        print(f"   📊 共 {total} 条记录")

        article_indices = [
            idx for idx, item in enumerate(articles)
            if item.get("type") in ("article", "guide")
        ]

        if not article_indices:
            print(f"   ⚠️ 没有需要打标签的法条")
            return {"success": True, "count": 0}

        print(f"   📊 需要打标签的法条：{len(article_indices)} 条")

        short_indices = []
        long_indices = []

        for idx in article_indices:
            content = articles[idx].get("content", "")
            if len(content) > LONG_TEXT_THRESHOLD:
                long_indices.append(idx)
            else:
                short_indices.append(idx)

        print(f"   📊 短条文：{len(short_indices)} 条")
        print(f"   📊 长条文：{len(long_indices)} 条")

        processed_count = 0
        total_articles = len(article_indices)

        # -----------------------------------------------------
        # 先处理长条文
        # -----------------------------------------------------

        for idx in long_indices:
            try:
                # ⭐ 更新当前处理的条文
                set_tag_progress_field(
                    "current_article",
                    articles[idx].get("article", "")
                )
                set_tag_progress(
                    "AI 打标签",
                    (processed_count / max(1, total_articles)) * 100,
                    f"[{knowledge_name}] 长条文：{articles[idx].get('article', '')}",
                    current_pdf=knowledge_name,
                )

                tags = process_long_article(idx, articles[idx])

                # ✅ 直接写入树节点（不再有 dept_category）
                articles[idx]["dept_type_name"] = tags
                articles[idx]["dept_type_name_str"] = ",".join(tags)

                processed_count += 1

                # ⭐ 更新进度
                set_tag_progress(
                    "AI 打标签",
                    (processed_count / max(1, total_articles)) * 100,
                    f"[{knowledge_name}] 已完成 {processed_count}/{total_articles} 条",
                    current_pdf=knowledge_name,
                    processed=processed_count,
                )

                print(f"   ✅ 已完成 {processed_count}/{total_articles} 条")

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)

            except Exception as e:
                print(f"   ❌ 长条文 {articles[idx].get('article', '')} 处理失败：{e}")
                articles[idx]["dept_type_name"] = ["鑫隆煤业"]
                articles[idx]["dept_type_name_str"] = "鑫隆煤业"

                processed_count += 1

                set_tag_progress(
                    "AI 打标签",
                    (processed_count / max(1, total_articles)) * 100,
                    f"[{knowledge_name}] 已完成 {processed_count}/{total_articles} 条",
                    current_pdf=knowledge_name,
                    processed=processed_count,
                )

        # -----------------------------------------------------
        # 再处理短条文（批量）
        # -----------------------------------------------------

        batches = []
        for i in range(0, len(short_indices), BATCH_SIZE):
            batch = short_indices[i:i + BATCH_SIZE]
            batches.append((i // BATCH_SIZE, batch))

        print(f"   📦 短条文共分成 {len(batches)} 批，每批 {BATCH_SIZE} 条")

        for batch_idx, batch_indices in batches:
            try:
                batch_data = []
                for i, idx in enumerate(batch_indices, 1):
                    item = articles[idx]
                    segments = [item.get("content", "")]
                    batch_data.append((i, idx, item, segments))

                set_tag_progress(
                    "AI 打标签",
                    (processed_count / max(1, total_articles)) * 100,
                    f"[{knowledge_name}] 短条文批次 {batch_idx + 1}/{len(batches)}",
                    current_pdf=knowledge_name,
                )

                prompt = build_prompt_for_batch(batch_data)
                result = ai_call(prompt)
                results = parse_ai_response_for_batch(result, batch_data)

                for idx, dept_names in results.items():
                    if 0 <= idx < len(articles):
                        articles[idx]["dept_type_name"] = dept_names
                        articles[idx]["dept_type_name_str"] = ",".join(dept_names)

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)

                processed_count += len(batch_indices)

                set_tag_progress(
                    "AI 打标签",
                    (processed_count / max(1, total_articles)) * 100,
                    f"[{knowledge_name}] 已完成 {processed_count}/{total_articles} 条",
                    current_pdf=knowledge_name,
                    processed=processed_count,
                )

                print(f"   ✅ 已完成 {processed_count}/{total_articles} 条")

                time.sleep(0.5)

            except Exception as e:
                print(f"   ❌ 批次 {batch_idx + 1} 处理失败：{e}")

                processed_count += len(batch_indices)

                set_tag_progress(
                    "AI 打标签",
                    (processed_count / max(1, total_articles)) * 100,
                    f"[{knowledge_name}] 已完成 {processed_count}/{total_articles} 条",
                    current_pdf=knowledge_name,
                    processed=processed_count,
                )

        # -----------------------------------------------------
        # 最终校验
        # -----------------------------------------------------

        tagged_count = 0
        for item in articles:
            if item.get("type") in ("article", "guide"):
                if item.get("dept_type_name"):
                    tagged_count += 1

                    if isinstance(item["dept_type_name"], str):
                        item["dept_type_name"] = [
                            x.strip()
                            for x in item["dept_type_name"].split(",")
                            if x.strip()
                        ]

                    if isinstance(item["dept_type_name"], list):
                        item["dept_type_name"] = [
                            n for n in item["dept_type_name"]
                            if n in VALID_NODES
                        ] or ["鑫隆煤业"]

                    item["dept_type_name_str"] = ",".join(item["dept_type_name"])

                else:
                    item["dept_type_name"] = ["鑫隆煤业"]
                    item["dept_type_name_str"] = "鑫隆煤业"
                    tagged_count += 1

        for item in articles:
            if isinstance(item, dict) and "dept_category" in item:
                del item["dept_category"]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        print(f"   ✅ {knowledge_name} 打标签完成！{tagged_count}/{total_articles} 条已打标签")

        return {"success": True, "count": tagged_count}

    except Exception as e:
        print(f"   ❌ 处理失败：{e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "count": 0}


# ============================================================
# 10. 主函数
# ============================================================

def main(source_file=None):
    """
    打标签主函数
    """
    # ---------- 重置进度 ----------
    reset_tag_progress(source_file or "")

    print()
    print("=" * 60)
    print("🏷️  开始打标签（树节点直出，无大类）...")
    print("=" * 60)

    # ========================================================
    # 1. 检查 Excel 节点
    # ========================================================

    if not ALL_NODES:
        print("❌ 没有读到任何树节点，检查 Excel 路径")
        set_tag_progress_field("status", "error")
        set_tag_progress_field("message", "没有读到树节点")
        return {
            "success": False,
            "error": "没有读到树节点"
        }

    # ========================================================
    # 2. 检查知识库目录
    # ========================================================

    try:
        if not KNOWLEDGE_DIR.exists():
            message = f"知识库目录不存在：{KNOWLEDGE_DIR}"
            print(f"❌ {message}")
            set_tag_progress_field("status", "error")
            set_tag_progress_field("message", message)
            return {
                "success": False,
                "error": message
            }

        # ====================================================
        # 3. 确定本次要处理哪些知识库
        # ====================================================

        knowledge_files = []

        if source_file:
            source_file = str(source_file).strip()

            print()
            print("=" * 60)
            print("本次为【单 PDF 打标签】")
            print(f"当前 PDF：{source_file}")
            print("不会处理其他 PDF")
            print("=" * 60)

            source_name = source_file
            if source_name.lower().endswith(".pdf"):
                source_name = source_name[:-4]
            source_name = source_name.strip()

            print(f"对应知识库目录名：{source_name}")

            target_dir = KNOWLEDGE_DIR / source_name
            json_file = target_dir / "articles.json"

            if not json_file.exists():
                print()
                print("⚠️ 精确匹配没有找到，开始搜索知识库目录...")

                target_dir = None

                for dir_path in sorted(KNOWLEDGE_DIR.iterdir()):
                    if not dir_path.is_dir():
                        continue
                    if dir_path.name == source_name:
                        target_dir = dir_path
                        break
                    if source_name in dir_path.name:
                        target_dir = dir_path
                        break

                if target_dir:
                    json_file = target_dir / "articles.json"

            if not target_dir or not json_file.exists():
                print()
                print("❌ 没有找到当前 PDF 对应的知识库")
                print(f"PDF：{source_file}")
                print(f"查找目录：{KNOWLEDGE_DIR}")

                set_tag_progress_field("status", "error")
                set_tag_progress_field("message", f"没有找到知识库：{source_file}")

                return {
                    "success": False,
                    "error": f"没有找到知识库：{source_file}"
                }

            knowledge_files.append((json_file, target_dir.name))

            print()
            print("✅ 已找到当前 PDF 对应知识库：")
            print(f"   {json_file}")

        else:
            print()
            print("=" * 60)
            print("本次为【全部知识库打标签】")
            print("未指定 PDF，将处理所有知识库")
            print("=" * 60)

            for dir_path in sorted(KNOWLEDGE_DIR.iterdir()):
                if not dir_path.is_dir():
                    continue

                json_file = dir_path / "articles.json"
                if not json_file.exists():
                    continue

                knowledge_files.append((json_file, dir_path.name))

        # ====================================================
        # 4. 检查最终要处理的数量
        # ====================================================

        if not knowledge_files:
            print()
            print("❌ 没有找到需要处理的知识库")
            set_tag_progress_field("status", "error")
            set_tag_progress_field("message", "没有找到需要处理的知识库")
            return {
                "success": False,
                "error": "没有找到需要处理的知识库"
            }

        # 统计总条数
        total_articles_all = 0
        for json_file, _ in knowledge_files:
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                if isinstance(arr, list):
                    for it in arr:
                        if it.get("type") in ("article", "guide"):
                            total_articles_all += 1
            except Exception:
                pass

        set_tag_progress_field("total", total_articles_all)
        set_tag_progress_field("processed", 0)

        print()
        print(f"本次准备处理 {len(knowledge_files)} 个知识库")
        print(f"总法条数：{total_articles_all}")

        for index, (json_file, knowledge_name) in enumerate(knowledge_files, start=1):
            print(f"{index}. {knowledge_name}")

        # ====================================================
        # 5. 开始处理
        # ====================================================

        total_processed = 0
        total_success = 0
        total_failed = 0

        for index, (json_file, knowledge_name) in enumerate(knowledge_files, start=1):
            print()
            print("=" * 60)

            if source_file:
                print(f"正在处理当前 PDF [{index}/{len(knowledge_files)}]")
            else:
                print(f"正在处理知识库 [{index}/{len(knowledge_files)}]")

            print(f"知识库：{knowledge_name}")
            print(f"文件：{json_file}")
            print("=" * 60)

            try:
                result = process_single_knowledge(json_file, knowledge_name)

                if result.get("success"):
                    total_success += 1
                    total_processed += result.get("count", 0)
                else:
                    total_failed += 1

            except Exception as e:
                total_failed += 1
                print(f"❌ 知识库处理失败：{e}")
                import traceback
                traceback.print_exc()

        # ====================================================
        # 6. 最终结果
        # ====================================================

        print()
        print("=" * 60)

        if source_file:
            print("✅ 当前 PDF 打标签完成！")
        else:
            print("✅ 全部知识库打标签完成！")

        print("=" * 60)
        print(f"   📊 成功处理：{total_success} 个知识库")
        print(f"   📊 处理失败：{total_failed} 个知识库")
        print(f"   📊 共打标签：{total_processed} 条法条")
        print("=" * 60)

        # ⭐ 标记完成
        _load_tag_progress()
        tag_progress["status"] = "done"
        tag_progress["processed"] = tag_progress.get("total", total_processed)
        tag_progress["overall_percent"] = 100
        tag_progress["stage_percent"] = 100
        tag_progress["stage"] = "后处理"

        if source_file:
            tag_progress["message"] = (
                f"✅ {source_file} 打标签完成！共 {total_processed} 条"
            )
        else:
            tag_progress["message"] = (
                f"✅ 全部完成！已为 {total_processed} 条法条打上树节点标签"
            )

        _save_tag_progress()

        return {
            "success": True,
            "total_knowledge": total_success,
            "total_articles": total_processed,
            "source_file": source_file
        }

    except Exception as e:
        set_tag_progress_field("status", "error")
        set_tag_progress_field("message", f"❌ 打标签失败：{str(e)}")

        print(f"❌ 打标签失败：{e}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e),
            "source_file": source_file
        }


# ============================================================
# 直接运行脚本
# ============================================================

if __name__ == "__main__":
    import sys

    source_file = None

    if len(sys.argv) > 1:
        source_file = sys.argv[1]

    main(source_file=source_file)