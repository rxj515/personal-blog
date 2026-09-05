import json
import requests
import os
import concurrent.futures
import time
import re
from pathlib import Path

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

# 知识库目录
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"

# 合法的大类列表
VALID_CATEGORIES = ["采煤类", "掘进类", "通风类", "机电类", "安全类", "探水类", "运输类", "全部工种"]

# ============================================================
# 全局进度变量
# ============================================================

tag_progress = {
    "total": 0,
    "processed": 0,
    "status": "idle",
    "message": ""
}


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
                    {"role": "system", "content": "你是一个专业的煤矿安全法规分类助手。只返回分类结果，不要输出其他内容。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1
            },
            timeout=120
        )
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"AI调用失败：{e}")
        return None


def get_progress():
    return tag_progress


def extract_category_from_response(text):
    """从 AI 返回的文本中提取分类结果"""
    text = text.strip()
    
    # 直接匹配完整大类名
    for category in VALID_CATEGORIES:
        if category in text:
            return category
    
    # 匹配 "xxx:采煤类" 格式
    pattern = r'[：:]\s*([采掘通机安探运]+[类])'
    match = re.search(pattern, text)
    if match:
        cat = match.group(1)
        for category in VALID_CATEGORIES:
            if category in cat:
                return category
    
    # 匹配单独的类名
    for category in VALID_CATEGORIES:
        if category.replace("类", "") in text:
            return category
    
    # 默认返回全部工种
    return "全部工种"


def process_single_knowledge(json_path, knowledge_name):
    """
    处理单个知识库文件，确保所有法条都能打上标签
    """
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

        # 找出所有 article 类型的索引
        article_indices = [
            idx for idx, item in enumerate(articles)
            if item.get("type") == "article"
        ]

        if not article_indices:
            print(f"   ⚠️ 没有需要打标签的法条")
            return {"success": True, "count": 0}

        print(f"   📊 需要打标签的法条：{len(article_indices)} 条")

        # ============================================================
        # 配置参数
        # ============================================================

        BATCH_SIZE = 25  # 每批25条，更稳定
        MAX_WORKERS = 2  # 并发数降低，避免 API 限流

        # ============================================================
        # 处理单个批次 - 强制返回所有法条的结果
        # ============================================================

        def process_batch(batch_indices, batch_idx):
            """处理一个批次，强制为所有法条返回结果"""
            batch_data = []
            batch_content = ""
            
            # 构建批次内容，使用简洁的序号
            for i, idx in enumerate(batch_indices, 1):
                item = articles[idx]
                content = item.get("content", "")[:200]
                batch_data.append((i, idx, item))
                batch_content += f"{i}. {content}\n\n"

            prompt = f"""
            请判断以下法条内容分别属于哪个大类？

            大类列表：采煤类、掘进类、通风类、机电类、安全类、探水类、运输类

            法条内容：
            {batch_content}

            请严格按照以下格式返回，每个法条一行，格式为"序号:大类名称"：
            1:采煤类
            2:通风类
            3:安全类

            注意：
            1. 必须为每个法条都返回结果，序号从1到{len(batch_indices)}
            2. 只能从上述大类列表中选择
            3. 如果无法判断，返回"全部工种"
            4. 不要输出其他任何内容
            """

            result = ai_call(prompt)
            if result is None:
                # AI 调用失败，所有法条标记为全部工种
                print(f"   ⚠️ 批次 {batch_idx + 1} AI 调用失败，全部标记为全部工种")
                return {idx: "全部工种" for _, idx, _ in batch_data}

            # 解析结果
            results = {}
            lines = result.strip().split("\n")
            
            # 先尝试解析标准格式
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 匹配 "序号:分类" 或 "序号：分类"
                match = re.match(r'^(\d+)\s*[：:]\s*(.+)$', line)
                if match:
                    num = int(match.group(1))
                    category = match.group(2).strip()
                    # 提取大类名称
                    for valid_cat in VALID_CATEGORIES:
                        if valid_cat in category:
                            # 找到对应的原始索引
                            for i, idx, _ in batch_data:
                                if i == num:
                                    results[idx] = valid_cat
                                    break
                            break
                    else:
                        # 没匹配到合法大类，尝试模糊匹配
                        for valid_cat in VALID_CATEGORIES:
                            if valid_cat.replace("类", "") in category or category in valid_cat:
                                for i, idx, _ in batch_data:
                                    if i == num:
                                        results[idx] = valid_cat
                                        break
                                break
            
            # 检查是否有遗漏的法条
            missing_indices = set(idx for _, idx, _ in batch_data) - set(results.keys())
            if missing_indices:
                print(f"   ⚠️ 批次 {batch_idx + 1} 遗漏了 {len(missing_indices)} 条法条，补充为全部工种")
                for idx in missing_indices:
                    results[idx] = "全部工种"
            
            # 确保每个法条都有结果
            for _, idx, _ in batch_data:
                if idx not in results:
                    results[idx] = "全部工种"
            
            return results

        # ============================================================
        # 生成所有批次
        # ============================================================

        batches = []
        for i in range(0, len(article_indices), BATCH_SIZE):
            batch = article_indices[i:i + BATCH_SIZE]
            batches.append((i // BATCH_SIZE, batch))

        print(f"   📦 共分成 {len(batches)} 批，每批 {BATCH_SIZE} 条")

        # ============================================================
        # 串行执行（避免并发冲突和 API 限流）
        # ============================================================

        processed_count = 0
        total_articles = len(article_indices)

        for batch_idx, batch_indices in batches:
            try:
                results = process_batch(batch_indices, batch_idx)
                
                # 更新文章
                for idx, dept_name in results.items():
                    if 0 <= idx < len(articles):
                        articles[idx]["dept_type_name"] = dept_name
                
                # 保存
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(articles, f, ensure_ascii=False, indent=2)
                
                processed_count += len(batch_indices)
                print(f"   ✅ 已完成 {processed_count}/{total_articles} 条")
                
                # 避免 API 限流
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ❌ 批次 {batch_idx + 1} 处理失败：{e}")

        # ============================================================
        # 最终验证：确保所有 article 都有标签
        # ============================================================

        tagged_count = 0
        for item in articles:
            if item.get("type") == "article":
                if item.get("dept_type_name"):
                    tagged_count += 1
                else:
                    # 如果还是没有标签，补上全部工种
                    item["dept_type_name"] = "全部工种"
                    tagged_count += 1
        
        # 再次保存
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
# 主函数：遍历所有知识库
# ============================================================

def main():
    global tag_progress

    tag_progress = {
        "total": 0,
        "processed": 0,
        "status": "running",
        "message": "开始打标签..."
    }

    print()
    print("=" * 60)
    print("🏷️  开始打工种标签...")
    print("=" * 60)

    try:
        if not KNOWLEDGE_DIR.exists():
            tag_progress["status"] = "error"
            tag_progress["message"] = f"知识库目录不存在：{KNOWLEDGE_DIR}"
            print(f"❌ 知识库目录不存在：{KNOWLEDGE_DIR}")
            return

        total_processed = 0
        total_success = 0
        total_failed = 0

        for dir_path in sorted(KNOWLEDGE_DIR.iterdir()):
            if not dir_path.is_dir():
                continue

            json_file = dir_path / "articles.json"
            if not json_file.exists():
                continue

            result = process_single_knowledge(json_file, dir_path.name)

            if result["success"]:
                total_success += 1
                total_processed += result["count"]
            else:
                total_failed += 1

        print()
        print("=" * 60)
        print("✅ 打标签完成！")
        print("=" * 60)
        print(f"   📊 成功处理：{total_success} 个知识库")
        print(f"   📊 处理失败：{total_failed} 个知识库")
        print(f"   📊 共打标签：{total_processed} 条法条")
        print("=" * 60)

        tag_progress["status"] = "done"
        tag_progress["processed"] = total_processed
        tag_progress["message"] = f"✅ 全部完成！已为 {total_processed} 条法条打上 AI 标签"

        return {
            "success": True,
            "total_knowledge": total_success,
            "total_articles": total_processed
        }

    except Exception as e:
        tag_progress["status"] = "error"
        tag_progress["message"] = f"❌ 打标签失败：{str(e)}"
        print(f"❌ 打标签失败：{e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    main()