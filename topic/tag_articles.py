import json
import requests
import os
import concurrent.futures
import time

# ============================================================
# 1. 自动读取 AI 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(BASE_DIR, "config", "ai_config.json")

with open(config_file, "r", encoding="utf-8") as f:
    ai_config = json.load(f)

AI_API_URL = ai_config.get("base_url", "https://api.deepseek.com/v1") + "/chat/completions"
AI_MODEL = ai_config.get("model", "deepseek-chat")
AI_API_KEY = ai_config.get("api_key", "")

print(f"AI 接口地址: {AI_API_URL}")
print(f"AI 模型: {AI_MODEL}")


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
                    {"role": "system", "content": "你是一个专业的煤矿安全法规分类助手。"},
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


# ============================================================
# 主函数：并发 + 大批次
# ============================================================

def main():
    global tag_progress

    tag_progress = {
        "total": 0,
        "processed": 0,
        "status": "running",
        "message": "开始打标签..."
    }

    try:
        articles_file = os.path.join(BASE_DIR, "data", "articles.json")
        
        if not os.path.exists(articles_file):
            tag_progress["status"] = "error"
            tag_progress["message"] = f"文件不存在：{articles_file}"
            return

        with open(articles_file, "r", encoding="utf-8") as f:
            articles = json.load(f)

        total = len(articles)
        tag_progress["total"] = total
        tag_progress["message"] = f"共 {total} 条法条，开始处理..."

        print(f"共读取到 {total} 条法条")

        # ============================================================
        # 配置参数
        # ============================================================

        BATCH_SIZE = 30      # 每批30条，减少调用次数
        MAX_WORKERS = 5      # 5个并发请求

        # ============================================================
        # 处理单个批次
        # ============================================================

        def process_batch(start_idx, batch):
            """处理一个批次，返回结果字典"""
            batch_content = ""
            for j, article in enumerate(batch):
                content = article.get("content", "")
                batch_content += f"法条 {start_idx + j + 1}: {content[:150]}\n\n"
            
            prompt = f"""
            请判断以下法条内容分别属于哪个大类？
            
            大类列表：采煤类、掘进类、通风类、机电类、安全类、探水类、运输类
            
            法条内容：
            {batch_content}
            
            请按照格式返回，每行一个结果，格式为：
            法条序号:大类名称
            
            例如：
            法条 1:采煤类
            法条 2:通风类
            
            如果没有匹配，返回"全部工种"。
            """
            
            result = ai_call(prompt)
            if result is None:
                return {}
            
            results = {}
            lines = result.strip().split("\n")
            for line in lines:
                try:
                    if ":" in line:
                        parts = line.split(":", 1)
                        idx = int(parts[0].replace("法条", "").strip()) - 1
                        dept_name = parts[1].strip().replace("。", "").replace("，", "").replace("\"", "").strip()
                        results[idx] = dept_name
                except Exception as e:
                    print(f"解析失败：{line}，错误：{e}")
            
            return results

        # ============================================================
        # 生成所有批次
        # ============================================================

        batches = []
        for i in range(0, total, BATCH_SIZE):
            batch = articles[i:i + BATCH_SIZE]
            batches.append((i, batch))

        print(f"共分成 {len(batches)} 批，每批 {BATCH_SIZE} 条，并发数 {MAX_WORKERS}")
        print("=" * 60)

        # ============================================================
        # 并发执行
        # ============================================================

        processed_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_batch = {
                executor.submit(process_batch, start_idx, batch): (start_idx, batch)
                for start_idx, batch in batches
            }
            
            for future in concurrent.futures.as_completed(future_to_batch):
                start_idx, batch = future_to_batch[future]
                try:
                    results = future.result()
                    
                    # 更新文章
                    for idx, dept_name in results.items():
                        if start_idx <= idx < start_idx + len(batch):
                            articles[idx]["dept_type_name"] = dept_name
                    
                    # 每完成一批就保存
                    with open(articles_file, "w", encoding="utf-8") as f:
                        json.dump(articles, f, ensure_ascii=False, indent=2)
                    
                    # 更新进度
                    processed_count += len(batch)
                    tag_progress["processed"] = min(processed_count, total)
                    tag_progress["message"] = f"已处理 {tag_progress['processed']}/{total} 条法条..."
                    
                    print(f"✅ 已完成第 {start_idx//BATCH_SIZE + 1} 批，已处理 {tag_progress['processed']}/{total} 条")
                    
                except Exception as e:
                    print(f"❌ 批次处理失败：{e}")

        # ============================================================
        # 完成
        # ============================================================

        tag_progress["status"] = "done"
        tag_progress["processed"] = total
        tag_progress["message"] = f"✅ 全部完成！已为 {total} 条法条打上 AI 标签"
        print("=" * 60)
        print(f"✅ 全部完成！已为 {total} 条法条打上 AI 标签")

    except Exception as e:
        tag_progress["status"] = "error"
        tag_progress["message"] = f"❌ 打标签失败：{str(e)}"
        print(f"❌ 打标签失败：{e}")


if __name__ == "__main__":
    main()