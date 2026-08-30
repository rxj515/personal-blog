# ============================================================
# main.py
# 通用法规 AI 系统 Web 服务
#
# 职责：
# 1. FastAPI 服务
# 2. 页面路由
# 3. API 接口
# 4. 静态资源
# 5. 调用 Python 业务模块
#
# 不负责：
# 1. HTML具体页面内容
# 2. CSS样式
# 3. JS业务逻辑
# 4. AI出题具体实现
# 5. Excel具体生成
#
# ============================================================


# ============================================================
# 1. 导入
# ============================================================

import sys
import json
from pathlib import Path
import asyncio

from fastapi import FastAPI, Body, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ai_config import (
    get_ai_config,
    save_ai_config
)

import uvicorn


# ============================================================
# 2. 项目根目录
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# 3. 项目目录
# ============================================================

# 数据目录
DATA_DIR = BASE_DIR / "data"

# 题库目录
QUESTIONS_DIR = BASE_DIR / "questions"

# Excel目录
EXCEL_DIR = BASE_DIR / "excel"

# PDF目录
PDF_DIR = BASE_DIR / "pdf"

# 配置目录
CONFIG_DIR = BASE_DIR / "config"

# HTML模板目录
TEMPLATES_DIR = BASE_DIR / "templates"

# 静态资源目录
STATIC_DIR = BASE_DIR / "static"

# 页面目录
PAGES_DIR = TEMPLATES_DIR / "pages"


# ============================================================
# 4. 数据文件
# ============================================================

# 法规知识库
KNOWLEDGE_FILE = DATA_DIR / "articles.json"

# AI配置文件
AI_CONFIG_FILE = CONFIG_DIR / "ai_config.json"


# ============================================================
# 5. 创建必要目录
# ============================================================

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

QUESTIONS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

EXCEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PDF_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CONFIG_DIR.mkdir(
    parents=True,
    exist_ok=True
)

TEMPLATES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

PAGES_DIR.mkdir(
    parents=True,
    exist_ok=True
)

STATIC_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 6. FastAPI
# ============================================================

app = FastAPI(
    title="通用法规 AI 系统",
    description="法规知识库与 AI 自动出题系统",
    version="2.0.0"
)


# ============================================================
# 7. 静态文件
# ============================================================

app.mount(
    "/static",
    StaticFiles(
        directory=str(STATIC_DIR)
    ),
    name="static"
)


# ============================================================
# 8. HTML模板
# ============================================================

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR)
)


# ============================================================
# 9. 通用工具函数
# ============================================================

def read_json_file(file_path: Path):
    """
    读取 JSON 文件

    返回：
        成功：JSON数据
        失败：None
    """

    if not file_path.exists():
        return None

    try:
        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"读取JSON失败：{file_path}"
        )

        print(e)

        return None


# ============================================================
# 10. 查找历史题库（排除 _new.json）
# ============================================================

def find_question_file():
    """
    查找 questions 目录中
    最近修改的 JSON 文件
    
    排除：
        *_new.json - 这些是临时生成的新题，不显示在题库管理中
    """

    if not QUESTIONS_DIR.exists():
        return None

    # 排除 _new.json 文件
    json_files = [
        f for f in QUESTIONS_DIR.glob("*.json")
        if not f.name.endswith("_new.json")
    ]

    if not json_files:
        return None

    json_files.sort(
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    return json_files[0]


# ============================================================
# 11. 页面模板检查
# ============================================================

def page_exists(page_name: str):

    return (
        PAGES_DIR / page_name
    ).exists()


# ============================================================
# 12. 首页
# ============================================================

@app.get("/")
def index(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


# ============================================================
# 13. 工作台
# ============================================================

@app.get("/dashboard")
def dashboard(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="pages/dashboard.html"
    )


# ============================================================
# 14. 法规知识库
# ============================================================

@app.get("/knowledge")
def knowledge(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="pages/knowledge.html"
    )


# ============================================================
# 15. AI智能出题
# ============================================================

@app.get("/ai-question")
def ai_question(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="pages/ai_question.html"
    )


# ============================================================
# 16. 题库管理
# ============================================================

@app.get("/question-bank")
def question_bank(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="pages/question_bank.html"
    )


# ============================================================
# 17. 系统设置
# ============================================================

@app.get("/system")
def system(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="pages/system.html"
    )


# ============================================================
# 18. 系统配置 API
#
# GET /api/config
#
# ============================================================

@app.get("/api/config")
def get_config():

    try:

        ai = get_ai_config()

        provider = ai.get(
            "provider",
            ai.get(
                "ai",
                "ollama"
            )
        )

        model = ai.get(
            "model",
            "qwen3:8b"
        )

        base_url = ai.get(
            "base_url",
            "http://localhost:11434"
        )

        # ✅ 新增：读取 api_key
        api_key = ai.get(
            "api_key",
            ""
        )

        return {
            "success": True,
            "data": {
                "python": sys.version.split()[0],

                "project_dir": str(BASE_DIR),

                "provider": provider,

                "model": model,

                "base_url": base_url,

                "api_key": api_key,   # ✅ 新增

                # 为了兼容旧前端
                "ai": provider
            }
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"读取AI配置失败：{e}"
            }
        )

# ============================================================
# 19. 获取AI配置
#
# GET /api/system/ai/config
#
# ============================================================

@app.get("/api/system/ai/config")
def read_ai_config():

    try:

        config = get_ai_config()

        return {
            "success": True,
            "data": config
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"读取AI配置失败：{e}"
            }
        )


# ============================================================
# 20. 保存AI配置
#
# POST /api/system/ai/config
#
# 前端可以传：
#
# {
#     "provider": "deepseek",
#     "model": "deepseek-chat",
#     "base_url": "https://api.deepseek.com/chat/completions"
# }
#
# 也兼容旧前端：
#
# {
#     "ai": "deepseek",
#     "model": "deepseek-chat",
#     "base_url": "..."
# }
#
# ============================================================

# ============================================================
# 20. 保存AI配置
#
# POST /api/system/ai/config
#
# ============================================================

@app.post("/api/system/ai/config")
def update_ai_config(
    data: dict = Body(...)
):

    try:

        # ----------------------------------------------------
        # provider
        # ----------------------------------------------------

        provider = (
            data.get("provider")
            or data.get("ai")
            or "ollama"
        )

        # ----------------------------------------------------
        # model
        # ----------------------------------------------------

        model = data.get(
            "model",
            "qwen3:8b"
        )

        # ----------------------------------------------------
        # base_url
        # ----------------------------------------------------

        base_url = data.get(
            "base_url",
            "http://localhost:11434"
        )

        # ----------------------------------------------------
        # ✅ 新增：api_key
        # ----------------------------------------------------

        api_key = data.get(
            "api_key",
            ""
        )

        # ----------------------------------------------------
        # 统一配置格式
        # ----------------------------------------------------

        config = {
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "api_key": api_key   # ✅ 新增
        }

        # ----------------------------------------------------
        # 保存
        # ----------------------------------------------------

        save_ai_config(config)

        print()
        print("=" * 60)
        print("AI配置保存成功")
        print("=" * 60)
        print("provider :", provider)
        print("model    :", model)
        print("base_url :", base_url)
        print("api_key  :", "已配置" if api_key else "未配置")  # ✅ 新增
        print("=" * 60)
        print()

        return {
            "success": True,
            "message": "AI配置保存成功",
            "data": config
        }

    except Exception as e:

        print("保存AI配置失败：", e)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"保存AI配置失败：{e}"
            }
        )

# ============================================================
# 21. 兼容旧接口
#
# POST /api/config/save
#
# 注意：
# 不再自己写 ai_config.json
#
# 统一调用 save_ai_config()
#
# ============================================================

@app.post("/api/config/save")
def save_config(
    data: dict = Body(...)
):

    try:

        provider = (
            data.get("provider")
            or data.get("ai")
            or "ollama"
        )

        model = data.get(
            "model",
            "qwen3:8b"
        )

        base_url = data.get(
            "base_url",
            "http://localhost:11434"
        )

        config = {
            "provider": provider,
            "model": model,
            "base_url": base_url
        }

        # 统一保存
        save_ai_config(config)

        return {
            "success": True,
            "message": "AI配置保存成功",
            "data": config
        }

    except Exception as e:

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"AI配置保存失败：{e}"
            }
        )


# ============================================================
# 22. 系统健康检查
#
# GET /api/health
#
# ============================================================

@app.get("/api/health")
def health():

    return {
        "success": True,
        "message": "系统运行正常",
        "version": "2.0.0"
    }


# ============================================================
# 23. 系统目录信息
#
# GET /api/system/info
#
# ============================================================

@app.get("/api/system/info")
def system_info():

    question_file = find_question_file()

    return {
        "success": True,
        "data": {

            "project_dir":
                str(BASE_DIR),

            "data_dir":
                str(DATA_DIR),

            "questions_dir":
                str(QUESTIONS_DIR),

            "excel_dir":
                str(EXCEL_DIR),

            "pdf_dir":
                str(PDF_DIR),

            "knowledge_file":
                str(KNOWLEDGE_FILE),

            "ai_config_file":
                str(AI_CONFIG_FILE),

            "latest_question_file":
                (
                    str(question_file)
                    if question_file
                    else None
                )
        }
    }


# ============================================================
# 24. 更新法规知识库
#
# POST /api/knowledge/update
#
# ============================================================

@app.post("/api/knowledge/update")
def update_knowledge():

    try:

        print()
        print("=" * 60)
        print("开始更新法规知识库")
        print("=" * 60)

        import build_knowledge

        build_knowledge.main()

        print()
        print("法规知识库更新完成")
        print()

        return {
            "success": True,
            "message": "法规知识库更新完成"
        }

    except ModuleNotFoundError:

        return {
            "success": False,
            "message": "找不到 build_knowledge.py"
        }

    except Exception as e:

        print()
        print("法规知识库更新失败")
        print(e)
        print()

        return {
            "success": False,
            "message": f"更新失败：{e}"
        }


# ============================================================
# 25. 读取法规知识库
#
# GET /api/knowledge/data
#
# ============================================================

@app.get("/api/knowledge/data")
def get_knowledge_data():

    try:

        # ----------------------------------------------------
        # 检查文件
        # ----------------------------------------------------

        if not KNOWLEDGE_FILE.exists():

            return {
                "success": False,
                "message":
                    f"找不到法规知识库：{KNOWLEDGE_FILE}",
                "count": 0,
                "data": []
            }

        # ----------------------------------------------------
        # 读取JSON
        # ----------------------------------------------------

        data = read_json_file(
            KNOWLEDGE_FILE
        )

        if data is None:

            return {
                "success": False,
                "message": "法规知识库JSON读取失败",
                "count": 0,
                "data": []
            }

        # ----------------------------------------------------
        # 检查格式
        # ----------------------------------------------------

        if not isinstance(data, list):

            return {
                "success": False,
                "message": "法规知识库JSON格式不是数组",
                "count": 0,
                "data": []
            }

        # ----------------------------------------------------
        # 过滤有效条文
        # ----------------------------------------------------

        article_data = [

            item

            for item in data

            if isinstance(item, dict)
            and item.get("article")
            and item.get("content")
        ]

        return {
            "success": True,
            "message": "读取成功",
            "count": len(article_data),
            "data": article_data
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"读取知识库失败：{e}",
            "count": 0,
            "data": []
        }


# ============================================================
# 26. 获取法规知识库统计
#
# GET /api/knowledge/statistics
#
# ============================================================

@app.get("/api/knowledge/statistics")
def get_knowledge_statistics():

    try:

        data = read_json_file(
            KNOWLEDGE_FILE
        )

        if not isinstance(data, list):

            return {
                "success": True,
                "data": {
                    "total": 0
                }
            }

        valid_data = [

            item

            for item in data

            if isinstance(item, dict)
            and item.get("article")
            and item.get("content")
        ]

        return {
            "success": True,
            "data": {
                "total": len(valid_data)
            }
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"统计失败：{e}",
            "data": {
                "total": 0
            }
        }


# ============================================================
# 27. AI生成题目（普通模式，保留兼容）
#
# POST /api/questions/generate
#
# 注意：
# 1. AI模型不从前端传递
# 2. AI模型统一读取 config/ai_config.json
# 3. main.py 不负责AI调用
# 4. generate_questions.py 不需要接收 model
#
# ============================================================

# # ============================================================
# # 28. AI生成题目（流式模式 - SSE）
# #
# # POST /api/questions/generate-stream
# #
# # 每生成一道题就立即通过 SSE 推送给前端
# #
# # ============================================================

# @app.post("/api/questions/generate-stream")
# async def generate_questions_stream(
#     data: dict = Body(...)
# ):
#     try:

#         # ----------------------------------------------------
#         # 1. 获取AI配置
#         # ----------------------------------------------------

#         ai = get_ai_config()

#         provider = (
#             ai.get("provider")
#             or ai.get("ai")
#             or "ollama"
#         )

#         # ----------------------------------------------------
#         # 2. 获取参数
#         # ----------------------------------------------------

#         question_type = data.get(
#             "question_type",
#             "单选题"
#         )

#         try:
#             count = int(
#                 data.get(
#                     "count",
#                     10
#                 )
#             )
#         except (TypeError, ValueError):
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "success": False,
#                     "message": "题目数量必须是整数"
#                 }
#             )

#         if count < 1:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "success": False,
#                     "message": "题目数量必须大于0"
#                 }
#             )

#         if count > 100:
#             return JSONResponse(
#                 status_code=400,
#                 content={
#                     "success": False,
#                     "message": "一次最多生成100道题"
#                 }
#             )

#         # ----------------------------------------------------
#         # 3. 设置AI服务商
#         # ----------------------------------------------------

#         import ai_client

#         ai_client.set_ai_type(provider)

#         # ----------------------------------------------------
#         # 4. 导入出题模块
#         # ----------------------------------------------------

#         import generate_questions as question_generator

#         # ----------------------------------------------------
#         # 5. 创建 SSE 流式生成器
#         # ----------------------------------------------------

#         async def event_generator():

#             # 发送开始信号
#             yield f"data: {json.dumps({'type': 'start', 'message': '开始生成题目...', 'total': count})}\n\n"

#             # 用于收集所有题目
#             all_questions = []
#             success_count = 0
#             failed_count = 0

#             # 重新加载法规知识库（使用外层的 BASE_DIR）
#             articles_file = BASE_DIR / "data" / "articles.json"

#             if not articles_file.exists():
#                 yield f"data: {json.dumps({'type': 'error', 'message': '找不到法规知识库'})}\n\n"
#                 return

#             try:
#                 with open(articles_file, "r", encoding="utf-8") as f:
#                     articles = json.load(f)
#             except Exception as e:
#                 yield f"data: {json.dumps({'type': 'error', 'message': f'读取法规知识库失败：{e}'})}\n\n"
#                 return

#             if not isinstance(articles, list):
#                 yield f"data: {json.dumps({'type': 'error', 'message': '法规知识库格式错误'})}\n\n"
#                 return

#             # 获取法规名称
#             law_names = {
#                 item.get("law_name")
#                 for item in articles
#                 if isinstance(item, dict) and item.get("law_name")
#             }

#             if law_names:
#                 law_name = list(law_names)[0]
#             else:
#                 law_name = "法规"

#             # 获取可出题条文
#             article_list = [
#                 item
#                 for item in articles
#                 if isinstance(item, dict)
#                 and item.get("type") == "article"
#                 and item.get("article")
#                 and item.get("content")
#             ]

#             if not article_list:
#                 yield f"data: {json.dumps({'type': 'error', 'message': '没有找到可用于出题的法规条文'})}\n\n"
#                 return

#             # 生成题型计划
#             import random

#             if question_type in ("判断题", "单选题", "多选题"):
#                 type_plan = [question_type for _ in range(count)]
#             else:
#                 types = ["判断题", "单选题", "多选题"]
#                 type_plan = [types[i % 3] for i in range(count)]
#                 random.shuffle(type_plan)

#             # 读取历史题库（用于去重）
#             history_file = question_generator.get_question_file(law_name, use_new=False)
#             history_questions = []

#             if history_file.exists():
#                 try:
#                     with open(history_file, "r", encoding="utf-8") as f:
#                         history_questions = json.load(f)
#                         if not isinstance(history_questions, list):
#                             history_questions = []
#                 except Exception:
#                     history_questions = []

#             used_questions = {
#                 (
#                     item.get("article"),
#                     item.get("title_category_name")
#                 )
#                 for item in history_questions
#                 if isinstance(item, dict)
#                 and item.get("article")
#                 and item.get("title_category_name")
#             }

#             failed_questions = set()
#             new_questions = []

#             # 获取 _new.json 文件路径
#             new_questions_file = question_generator.get_question_file(law_name, use_new=True)

#             # 循环生成每一道题
#             while success_count < count:

#                 current_type = type_plan[success_count]

#                 # 找可用法规
#                 available = [
#                     item
#                     for item in article_list
#                     if (
#                         (item.get("article"), current_type)
#                         not in used_questions
#                     )
#                     and (
#                         (item.get("article"), current_type)
#                         not in failed_questions
#                     )
#                 ]

#                 if not available:
#                     yield f"data: {json.dumps({'type': 'warning', 'message': f'当前题型 {current_type} 没有更多可用法规条文'})}\n\n"
#                     break

#                 item = random.choice(available)
#                 article = item.get("article", "")
#                 content = item.get("content", "")

#                 # 生成题目
#                 question = question_generator.generate_one_question(
#                     article,
#                     content,
#                     current_type
#                 )

#                 if question is None:
#                     failed_questions.add((article, current_type))
#                     failed_count += 1
#                     yield f"data: {json.dumps({'type': 'progress', 'message': f'第 {success_count + 1} 题生成失败，正在重试...', 'success': success_count, 'failed': failed_count, 'total': count})}\n\n"
#                     continue

#                 # 验证题型
#                 if question.get("title_category_name") != current_type:
#                     failed_questions.add((article, current_type))
#                     failed_count += 1
#                     continue

#                 # 保存题目
#                 new_questions.append(question)
#                 used_questions.add((article, current_type))
#                 success_count += 1

#                 # 每次生成后保存 _new.json
#                 try:
#                     with open(new_questions_file, "w", encoding="utf-8") as f:
#                         json.dump(new_questions, f, ensure_ascii=False, indent=2)
#                 except Exception as e:
#                     yield f"data: {json.dumps({'type': 'error', 'message': f'保存新题失败：{e}'})}\n\n"
#                     return

#                 # 推送这道题给前端
#                 yield f"data: {json.dumps({'type': 'question', 'question': question, 'index': success_count, 'total': count, 'success': success_count, 'failed': failed_count})}\n\n"

#                 # 小延迟，让前端有时间渲染
#                 await asyncio.sleep(0.1)

#             # 所有题目生成完成后，统一追加到历史题库
#             if new_questions:
#                 try:
#                     current_history = []
#                     if history_file.exists():
#                         try:
#                             with open(history_file, "r", encoding="utf-8") as f:
#                                 current_history = json.load(f)
#                                 if not isinstance(current_history, list):
#                                     current_history = []
#                         except Exception:
#                             current_history = []

#                     current_history.extend(new_questions)

#                     with open(history_file, "w", encoding="utf-8") as f:
#                         json.dump(current_history, f, ensure_ascii=False, indent=2)

#                 except Exception as e:
#                     yield f"data: {json.dumps({'type': 'error', 'message': f'追加历史题库失败：{e}'})}\n\n"

#             # 发送完成信号
#             yield f"data: {json.dumps({'type': 'end', 'message': f'生成完成，共生成 {success_count} 道题', 'total': success_count, 'questions': new_questions})}\n\n"

#         # ====================================================
#         # 返回 SSE 流式响应
#         # ====================================================

#         return StreamingResponse(
#             event_generator(),
#             media_type="text/event-stream",
#             headers={
#                 "Cache-Control": "no-cache",
#                 "Connection": "keep-alive",
#                 "X-Accel-Buffering": "no"
#             }
#         )

#     except Exception as e:

#         print()
#         print("=" * 60)
#         print("AI流式出题失败")
#         print("=" * 60)
#         print("异常类型：", type(e).__name__)
#         print("异常信息：", e)
#         print("=" * 60)
#         print()

#         return JSONResponse(
#             status_code=500,
#             content={
#                 "success": False,
#                 "message": f"AI流式出题失败：{e}"
#             }
#         )
        

def get_category_by_superior_name(superior_name):
    """
    根据上级名称，自动归类到大类
    """
    SUPERIOR_TO_CATEGORY = {
        "综采": "采煤类",
        "综采一队": "采煤类",
        "掘进开拓": "掘进类",
        "掘进二队": "掘进类",
        "运输": "运输类",
        "机运队": "运输类",
        "机电": "机电类",
        "机电运输": "机电类",
        "地面机电队": "机电类",
        "通风队": "通风类",
        "通风": "通风类",
        "安全": "安全类",
        "安监部门": "安全类",
        "抽采": "抽采类",
        "探水": "探水类",
        "监控信息": "监控类",
        "鑫隆煤业": "全部工种",
        "荣大煤业": "全部工种",
        "惠安煤业": "全部工种",
        "煤业公司": "全部工种",
        None: "全部工种"
    }
    return SUPERIOR_TO_CATEGORY.get(superior_name, "全部工种")


@app.post("/api/questions/generate-stream")
async def generate_questions_stream(
    data: dict = Body(...)
):
    try:

        # ----------------------------------------------------
        # 1. 获取AI配置
        # ----------------------------------------------------

        ai = get_ai_config()

        provider = (
            ai.get("provider")
            or ai.get("ai")
            or "ollama"
        )

        # ----------------------------------------------------
        # 2. 获取参数
        # ----------------------------------------------------

        question_type = data.get(
            "question_type",
            "单选题"
        )

        try:
            count = int(
                data.get(
                    "count",
                    10
                )
            )
        except (TypeError, ValueError):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "题目数量必须是整数"
                }
            )

        if count < 1:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "题目数量必须大于0"
                }
            )

        if count > 100:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "一次最多生成100道题"
                }
            )

        # ----------------------------------------------------
        # 3. ✅ 新增：接收分类（工种）信息
        # ----------------------------------------------------

        dept = data.get("dept", {})
        dept_id = dept.get("id", "")
        dept_name = dept.get("fullName", "")
        superior_name = dept.get("superiorName", "")

        # ----------------------------------------------------
        # 4. 设置AI服务商
        # ----------------------------------------------------

        import ai_client

        ai_client.set_ai_type(provider)

        # ----------------------------------------------------
        # 5. 导入出题模块
        # ----------------------------------------------------

        import generate_questions as question_generator

        # ----------------------------------------------------
        # 6. 创建 SSE 流式生成器
        # ----------------------------------------------------

        async def event_generator():

            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'message': '开始生成题目...', 'total': count})}\n\n"

            # 用于收集所有题目
            all_questions = []
            success_count = 0
            failed_count = 0

            # 重新加载法规知识库（使用外层的 BASE_DIR）
            articles_file = BASE_DIR / "data" / "articles.json"

            if not articles_file.exists():
                yield f"data: {json.dumps({'type': 'error', 'message': '找不到法规知识库'})}\n\n"
                return

            try:
                with open(articles_file, "r", encoding="utf-8") as f:
                    articles = json.load(f)
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'读取法规知识库失败：{e}'})}\n\n"
                return

            if not isinstance(articles, list):
                yield f"data: {json.dumps({'type': 'error', 'message': '法规知识库格式错误'})}\n\n"
                return

            # 获取法规名称
            law_names = {
                item.get("law_name")
                for item in articles
                if isinstance(item, dict) and item.get("law_name")
            }

            if law_names:
                law_name = list(law_names)[0]
            else:
                law_name = "法规"

            # 获取可出题条文
            article_list = [
                item
                for item in articles
                if isinstance(item, dict)
                and item.get("type") == "article"
                and item.get("article")
                and item.get("content")
            ]

            if not article_list:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有找到可用于出题的法规条文'})}\n\n"
                return

            # ----------------------------------------------------
            # ✅ 新增：根据上级名称（大类）过滤法条
            # ----------------------------------------------------

            if superior_name:
                # 用上级名称判断大类
                dept_category = get_category_by_superior_name(superior_name)

                # 根据大类过滤法条
                article_list = [
                    item for item in article_list
                    if item.get("dept_type_name") == dept_category
                    or item.get("dept_type_name") == "全部工种"
                ]

                # 如果没有匹配到法条，使用全部法条
                if not article_list:
                    print(f"⚠️ 大类 [{dept_category}] 没有匹配到法条，使用全部法条")

            # 生成题型计划
            import random

            if question_type in ("判断题", "单选题", "多选题"):
                type_plan = [question_type for _ in range(count)]
            else:
                types = ["判断题", "单选题", "多选题"]
                type_plan = [types[i % 3] for i in range(count)]
                random.shuffle(type_plan)

            # 读取历史题库（用于去重）
            history_file = question_generator.get_question_file(law_name, use_new=False)
            history_questions = []

            if history_file.exists():
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        history_questions = json.load(f)
                        if not isinstance(history_questions, list):
                            history_questions = []
                except Exception:
                    history_questions = []

            used_questions = {
                (
                    item.get("article"),
                    item.get("title_category_name")
                )
                for item in history_questions
                if isinstance(item, dict)
                and item.get("article")
                and item.get("title_category_name")
            }

            failed_questions = set()
            new_questions = []

            # 获取 _new.json 文件路径
            new_questions_file = question_generator.get_question_file(law_name, use_new=True)

            # 循环生成每一道题
            while success_count < count:

                current_type = type_plan[success_count]

                # 找可用法规
                available = [
                    item
                    for item in article_list
                    if (
                        (item.get("article"), current_type)
                        not in used_questions
                    )
                    and (
                        (item.get("article"), current_type)
                        not in failed_questions
                    )
                ]

                if not available:
                    yield f"data: {json.dumps({'type': 'warning', 'message': f'当前题型 {current_type} 没有更多可用法规条文'})}\n\n"
                    break

                item = random.choice(available)
                article = item.get("article", "")
                content = item.get("content", "")

                # 生成题目
                question = question_generator.generate_one_question(
                    article,
                    content,
                    current_type
                )

                if question is None:
                    failed_questions.add((article, current_type))
                    failed_count += 1
                    yield f"data: {json.dumps({'type': 'progress', 'message': f'第 {success_count + 1} 题生成失败，正在重试...', 'success': success_count, 'failed': failed_count, 'total': count})}\n\n"
                    continue

                # 验证题型
                if question.get("title_category_name") != current_type:
                    failed_questions.add((article, current_type))
                    failed_count += 1
                    continue

                # 保存题目
                new_questions.append(question)
                used_questions.add((article, current_type))
                success_count += 1

                # 每次生成后保存 _new.json
                try:
                    with open(new_questions_file, "w", encoding="utf-8") as f:
                        json.dump(new_questions, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'保存新题失败：{e}'})}\n\n"
                    return

                # 推送这道题给前端
                yield f"data: {json.dumps({'type': 'question', 'question': question, 'index': success_count, 'total': count, 'success': success_count, 'failed': failed_count})}\n\n"

                # 小延迟，让前端有时间渲染
                await asyncio.sleep(0.1)

            # 所有题目生成完成后，统一追加到历史题库
            if new_questions:
                try:
                    current_history = []
                    if history_file.exists():
                        try:
                            with open(history_file, "r", encoding="utf-8") as f:
                                current_history = json.load(f)
                                if not isinstance(current_history, list):
                                    current_history = []
                        except Exception:
                            current_history = []

                    current_history.extend(new_questions)

                    with open(history_file, "w", encoding="utf-8") as f:
                        json.dump(current_history, f, ensure_ascii=False, indent=2)

                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'追加历史题库失败：{e}'})}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'end', 'message': f'生成完成，共生成 {success_count} 道题', 'total': success_count, 'questions': new_questions})}\n\n"

        # ====================================================
        # 返回 SSE 流式响应
        # ====================================================

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:

        print()
        print("=" * 60)
        print("AI流式出题失败")
        print("=" * 60)
        print("异常类型：", type(e).__name__)
        print("异常信息：", e)
        print("=" * 60)
        print()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"AI流式出题失败：{e}"
            }
        )


        
# ============================================================
# 29. 读取最新题库（只读历史题库，排除 _new.json）
#
# GET /api/questions/data
#
# ============================================================

@app.get("/api/questions/data")
def get_questions_data():

    try:

        # ----------------------------------------------------
        # 查找历史题库（排除 _new.json）
        # ----------------------------------------------------

        question_file = find_question_file()

        if question_file is None:

            return {
                "success": False,
                "message":
                    "questions目录中没有找到历史题库JSON",
                "count": 0,
                "data": []
            }

        # ----------------------------------------------------
        # 读取JSON
        # ----------------------------------------------------

        data = read_json_file(
            question_file
        )

        if data is None:

            return {
                "success": False,
                "message": "题库JSON读取失败",
                "count": 0,
                "data": []
            }

        # ----------------------------------------------------
        # 检查格式
        # ----------------------------------------------------

        if not isinstance(data, list):

            return {
                "success": False,
                "message": "题库JSON格式不是数组",
                "count": 0,
                "data": []
            }

        return {
            "success": True,
            "message": "读取成功",
            "count": len(data),
            "file": str(question_file),
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"读取题库失败：{e}",
            "count": 0,
            "data": []
        }


# ============================================================
# 30. 获取题库统计（只统计历史题库，排除 _new.json）
#
# GET /api/questions/statistics
#
# ============================================================

@app.get("/api/questions/statistics")
def get_questions_statistics():

    try:

        question_file = find_question_file()

        if question_file is None:

            return {
                "success": True,
                "data": {
                    "total": 0,
                    "file": None
                }
            }

        data = read_json_file(
            question_file
        )

        if not isinstance(data, list):

            return {
                "success": True,
                "data": {
                    "total": 0,
                    "file": str(question_file)
                }
            }

        # ----------------------------------------------------
        # 统计题型
        # ----------------------------------------------------

        type_count = {}

        for item in data:

            if not isinstance(item, dict):
                continue

            question_type = (
                item.get("question_type")
                or item.get("type")
                or "未知"
            )

            type_count[question_type] = (
                type_count.get(
                    question_type,
                    0
                ) + 1
            )

        return {
            "success": True,
            "data": {
                "total": len(data),
                "file": str(question_file),
                "type_count": type_count
            }
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"统计题库失败：{e}"
        }


# ============================================================
# 31. 读取本次新题（_new.json）
#
# GET /api/questions/new-data
#
# ============================================================

@app.get("/api/questions/new-data")
def get_new_questions_data():

    try:

        # 查找 _new.json 文件
        json_files = list(
            QUESTIONS_DIR.glob("*_new.json")
        )

        if not json_files:

            return {
                "success": False,
                "message": "没有找到本次新题",
                "count": 0,
                "data": []
            }

        # 按修改时间排序，取最新的
        json_files.sort(
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        question_file = json_files[0]

        data = read_json_file(question_file)

        if data is None:

            return {
                "success": False,
                "message": "读取新题失败",
                "count": 0,
                "data": []
            }

        if not isinstance(data, list):

            return {
                "success": False,
                "message": "新题JSON格式不是数组",
                "count": 0,
                "data": []
            }

        return {
            "success": True,
            "message": "读取成功",
            "count": len(data),
            "file": str(question_file),
            "data": data
        }

    except Exception as e:

        return {
            "success": False,
            "message": f"读取新题失败：{e}",
            "count": 0,
            "data": []
        }


# ============================================================
# 32. Excel导出
#
# POST /api/questions/export
#
# ============================================================

@app.post("/api/questions/export")
def export_questions(
    data: dict = Body(...)
):

    try:

        print()
        print("=" * 60)
        print("开始导出Excel")
        print("=" * 60)

        print(
            "网页传入参数：",
            data
        )

        # ----------------------------------------------------
        # 参数检查
        # ----------------------------------------------------

        if not isinstance(data, dict):

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Excel导出参数必须是对象"
                }
            )

        # ----------------------------------------------------
        # 获取题目
        # ----------------------------------------------------

        questions = data.get(
            "questions",
            []
        )

        if not isinstance(
            questions,
            list
        ):

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "questions必须是数组"
                }
            )

        # ----------------------------------------------------
        # 数量检查
        # ----------------------------------------------------

        if len(questions) == 0:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "没有可导出的题目"
                }
            )

        print()
        print(
            f"准备导出：{len(questions)} 道题"
        )

        # ----------------------------------------------------
        # 导入Excel模块
        # ----------------------------------------------------

        import export_questions

        # ----------------------------------------------------
        # 调用Excel生成
        # ----------------------------------------------------

        result = export_questions.main(
            data=data
        )

        # ----------------------------------------------------
        # 检查返回
        # ----------------------------------------------------

        if result is None:

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message":
                        "Excel导出程序没有返回结果"
                }
            )

        # ----------------------------------------------------
        # export_questions自己报告失败
        # ----------------------------------------------------

        if not result.get(
            "success",
            False
        ):

            return JSONResponse(
                status_code=500,
                content=result
            )

        # ----------------------------------------------------
        # Excel文件
        # ----------------------------------------------------

        excel_file = result.get(
            "excel_file"
        )

        if not excel_file:

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message":
                        "Excel生成成功，但没有返回Excel文件路径"
                }
            )

        # ----------------------------------------------------
        # 转Path
        # ----------------------------------------------------

        excel_path = Path(
            excel_file
        )

        print()
        print("Excel实际文件：")
        print(excel_path)

        # ----------------------------------------------------
        # 检查文件
        # ----------------------------------------------------

        if not excel_path.exists():

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message":
                        "Excel生成成功，但找不到生成的Excel文件",
                    "excel_file":
                        str(excel_path)
                }
            )

        # ----------------------------------------------------
        # 检查xlsx
        # ----------------------------------------------------

        if excel_path.suffix.lower() != ".xlsx":

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message":
                        "生成的文件不是xlsx格式",
                    "excel_file":
                        str(excel_path)
                }
            )

        # ----------------------------------------------------
        # 文件名
        # ----------------------------------------------------

        filename = excel_path.name

        # ----------------------------------------------------
        # 输出
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("Excel生成成功")
        print()
        print("文件：", excel_path)
        print("题目数量：", len(questions))
        print("=" * 60)
        print()

        # ----------------------------------------------------
        # 直接返回文件
        # ----------------------------------------------------

        return FileResponse(
            path=str(excel_path),
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            filename=filename
        )

    except ModuleNotFoundError as e:

        print()
        print(
            "找不到export_questions.py"
        )
        print(e)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message":
                    "找不到export_questions.py，请检查文件是否存在"
            }
        )

    except Exception as e:

        print()
        print("=" * 60)
        print("Excel导出失败")
        print("=" * 60)
        print(e)
        print()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Excel导出失败：{e}"
            }
        )


# ============================================================
# 33. 导入题目到数据库
#
# POST /api/questions/import
#
# ============================================================

@app.post("/api/questions/import")
def import_questions_to_db(
    data: dict = Body(...)
):
    """
    将题目导入到MySQL数据库
    """
    try:

        print()
        print("=" * 60)
        print("开始导入题目到数据库")
        print("=" * 60)

        # ----------------------------------------------------
        # 参数检查
        # ----------------------------------------------------

        if not isinstance(data, dict):

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "导入参数必须是对象"
                }
            )

        # ----------------------------------------------------
        # 获取题目
        # ----------------------------------------------------

        questions = data.get(
            "questions",
            []
        )

        if not isinstance(
            questions,
            list
        ):

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "questions必须是数组"
                }
            )

        # ----------------------------------------------------
        # 数量检查
        # ----------------------------------------------------

        if len(questions) == 0:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "没有可导入的题目"
                }
            )

        print()
        print(
            f"准备导入：{len(questions)} 道题"
        )

        # ----------------------------------------------------
        # 导入数据库模块
        # ----------------------------------------------------

        import import_questions_db

        # ----------------------------------------------------
        # 调用导入函数
        # ----------------------------------------------------

        result = import_questions_db.main(
            data=data
        )

        # ----------------------------------------------------
        # 检查返回
        # ----------------------------------------------------

        if result is None:

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "导入程序没有返回结果"
                }
            )

        # ----------------------------------------------------
        # 返回结果
        # ----------------------------------------------------

        print()
        print("=" * 60)
        print("导入完成")
        print()
        print(f"处理：{result.get('total', 0)} 道")
        print(f"成功：{result.get('inserted', 0)} 道")
        print(f"跳过：{result.get('skipped', 0)} 道")
        print("=" * 60)
        print()

        return {
            "success": True,
            "message": f"成功导入 {result.get('inserted', 0)} 道题",
            "data": result
        }

    except ModuleNotFoundError as e:

        print()
        print("找不到 import_questions_db.py")
        print(e)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "找不到 import_questions_db.py，请检查文件是否存在"
            }
        )

    except Exception as e:

        print()
        print("=" * 60)
        print("导入数据库失败")
        print("=" * 60)
        print(e)
        print()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"导入数据库失败：{e}"
            }
        )




# ============================================================
# 获取题库分类列表（从 Java 后端获取）
#
# GET /api/dept/list
#
# ============================================================

@app.get("/api/dept/list")
def get_dept_list():
    """
    从 Java 后端获取题库分类列表（包含层级结构）
    """
    try:
        import requests
        
        # ✅ 走网关，端口固定 1100
        java_api_url = "http://localhost:1100/deptBankType/getExcelTypeSelectPy"
        
        # 后端加了 @SaIgnore 后，不需要 token 了
        response = requests.get(
            java_api_url,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            # 后端直接返回数组，不是包一层对象
            data = response.json()
            
            # 兼容处理：如果是字典且有 data 字段，取 data；如果是数组，直接用
            if isinstance(data, dict):
                items = data.get("data", [])
            else:
                items = data
            
            # 构建树形结构
            dept_list = []
            dept_map = {}
            
            # 先全部转换为字典
            for item in items:
                dept_id = item.get("id")
                
                # ✅ 修复：parentId 可能是 "0" 或 null，需要统一处理
                parent_id = item.get("parentId") or ""
                if parent_id == "0":
                    parent_id = ""
                
                dept_map[dept_id] = {
                    "id": dept_id,
                    "name": item.get("name"),
                    "code": item.get("code"),
                    "parentId": parent_id,
                    "superiorId": item.get("superiorId") or "",
                    "superiorName": item.get("superiorName"),
                    "subjectionId": item.get("subjectionId"),
                    "subjectionName": item.get("subjectionName"),
                    # ✅ 修复：isMine 可能是 null，需要统一为 0
                    "isMine": item.get("isMine") or 0,
                    "children": []
                }
            
            # 构建层级关系
            root_list = []
            for dept_id, dept in dept_map.items():
                parent_id = dept["parentId"]
                if parent_id and parent_id in dept_map:
                    dept_map[parent_id]["children"].append(dept)
                else:
                    root_list.append(dept)
            
            return {
                "success": True,
                "data": root_list
            }
        else:
            return {
                "success": False,
                "message": f"获取分类失败：HTTP {response.status_code}",
                "data": []
            }
            
    except requests.exceptions.ConnectionError:
        print("Java 后端未连接，使用本地缓存数据")
        return {
            "success": False,
            "message": "Java 后端未连接，使用本地缓存数据",
            "data": get_local_dept_list()
        }
        
    except Exception as e:
        print(f"获取分类异常：{e}")
        return {
            "success": False,
            "message": f"获取分类失败：{str(e)}",
            "data": get_local_dept_list()
        }

def get_local_dept_list():
    """
    本地分类数据（当 Java 后端不可用时使用）
    """
    return [
        {
            "id": "1",
            "name": "鑫隆煤业",
            "code": "xlmy",
            "parentId": "",
            "superiorId": "",
            "superiorName": "",
            "subjectionId": "001",
            "subjectionName": "鑫隆煤业",
            "isMine": 1,
            "children": [
                {
                    "id": "101",
                    "name": "抽采工",
                    "code": "ccg",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": []
                },
                {
                    "id": "102",
                    "name": "泵站值班员",
                    "code": "bzzby",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": []
                },
                {
                    "id": "103",
                    "name": "观察工",
                    "code": "gcg",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": []
                },
                {
                    "id": "104",
                    "name": "探水",
                    "code": "ts",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": [
                        {
                            "id": "1041",
                            "name": "探水工",
                            "code": "tsg",
                            "parentId": "104",
                            "superiorId": "1",
                            "superiorName": "鑫隆煤业",
                            "subjectionId": "001",
                            "subjectionName": "鑫隆煤业",
                            "isMine": 1,
                            "children": []
                        }
                    ]
                },
                {
                    "id": "105",
                    "name": "地面机电队",
                    "code": "dmjdd",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": []
                },
                {
                    "id": "106",
                    "name": "监控信息",
                    "code": "jkxx",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": []
                },
                {
                    "id": "107",
                    "name": "安全管理人员",
                    "code": "aqglry",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": []
                },
                {
                    "id": "108",
                    "name": "通风机房",
                    "code": "tffj",
                    "parentId": "1",
                    "superiorId": "1",
                    "superiorName": "鑫隆煤业",
                    "subjectionId": "001",
                    "subjectionName": "鑫隆煤业",
                    "isMine": 1,
                    "children": []
                }
            ]
        }
    ]

# ============================================================
# 33. 获取页面列表
#
# GET /api/pages
#
# ============================================================

@app.get("/api/pages")
def get_pages():

    return {
        "success": True,
        "data": [

            {
                "key": "dashboard",
                "name": "工作台",
                "path": "/dashboard",
                "icon": "dashboard"
            },

            {
                "key": "knowledge",
                "name": "法规知识库",
                "path": "/knowledge",
                "icon": "book"
            },

            {
                "key": "ai-question",
                "name": "AI智能出题",
                "path": "/ai-question",
                "icon": "robot"
            },

            {
                "key": "question-bank",
                "name": "题库管理",
                "path": "/question-bank",
                "icon": "database"
            },

            {
                "key": "system",
                "name": "系统设置",
                "path": "/system",
                "icon": "setting"
            }

        ]
    }


# ============================================================
# 34. 全局异常处理
# ============================================================

@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exc
):

    # API请求返回JSON
    if request.url.path.startswith("/api/"):

        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message":
                    f"接口不存在：{request.url.path}"
            }
        )

    # 普通网页请求
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "message": "页面不存在"
        }
    )


# ============================================================
# 35. 启动
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print(
        "        通用法规 AI 系统"
    )
    print("=" * 60)
    print()

    print(
        "AI服务正在启动……"
    )

    print()

    print(
        "访问地址："
    )

    print(
        "http://127.0.0.1:8000"
    )

    print()

    print(
        "工作台："
    )

    print(
        "http://127.0.0.1:8000/dashboard"
    )

    print()

    print(
        "法规知识库："
    )

    print(
        "http://127.0.0.1:8000/knowledge"
    )

    print()

    print(
        "AI智能出题："
    )

    print(
        "http://127.0.0.1:8000/ai-question"
    )

    print()

    print(
        "题库管理："
    )

    print(
        "http://127.0.0.1:8000/question-bank"
    )

    print()

    print(
        "系统设置："
    )

    print(
        "http://127.0.0.1:8000/system"
    )

    print()

    print(
        "API文档："
    )

    print(
        "http://127.0.0.1:8000/docs"
    )

    print()

    print("=" * 60)
    print()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )

# ============================================================
# 打标签接口（独立）
#
# POST /api/tag/articles
#
# ============================================================

@app.post("/api/tag/articles")
def tag_articles_api():
    """
    给法条打工种标签（独立接口）
    """
    try:

        print()
        print("=" * 60)
        print("🏷️ 开始打工种标签...")
        print("=" * 60)

        import tag_articles
        tag_articles.main()

        print("✅ 工种标签打标完成")
        print("=" * 60)
        print()

        return {
            "success": True,
            "message": "打标签完成"
        }

    except Exception as e:

        print()
        print("❌ 打标签失败：", e)
        print()

        return {
            "success": False,
            "message": f"打标签失败：{e}"
        }

# ============================================================
# 36. 删除新题（通过ID精确删除，同时从历史题库中移除）
#
# POST /api/questions/delete-new
#
# ============================================================

@app.post("/api/questions/delete-new")
def delete_new_question(
    data: dict = Body(...)
):
    """
    从 _new.json 和历史题库中删除指定ID的题目
    
    请求体：
    {
        "id": "uuid-xxx-xxx"  // 题目的唯一ID
    }
    """
    try:

        print()
        print("=" * 60)
        print("删除新题（通过ID精确删除，同时从历史题库移除）")
        print("=" * 60)

        # ----------------------------------------------------
        # 参数检查
        # ----------------------------------------------------
        if not isinstance(data, dict):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "参数必须是对象"
                }
            )

        question_id = data.get("id")
        
        if not question_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "缺少 id 参数"
                }
            )

        print(f"📌 要删除的题目ID：{question_id}")

        # ----------------------------------------------------
        # 1. 查找 _new.json 文件
        # ----------------------------------------------------
        json_files = list(
            QUESTIONS_DIR.glob("*_new.json")
        )

        if not json_files:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "没有找到 _new.json 文件"
                }
            )

        json_files.sort(
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        new_file = json_files[0]

        print(f"📄 _new.json 文件：{new_file.name}")

        # ----------------------------------------------------
        # 2. 读取 _new.json 数据
        # ----------------------------------------------------
        new_questions = read_json_file(new_file)

        if new_questions is None:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "读取 _new.json 失败"
                }
            )

        if not isinstance(new_questions, list):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "_new.json 格式不是数组"
                }
            )

        print(f"📌 _new.json 当前有 {len(new_questions)} 道题")

        # ----------------------------------------------------
        # 3. 通过ID查找要删除的题目
        # ----------------------------------------------------
        deleted_question = None
        deleted_index = -1
        
        for i, q in enumerate(new_questions):
            if q.get("id") == question_id:
                deleted_question = q
                deleted_index = i
                break

        if deleted_question is None:
            print(f"⚠️ 在 _new.json 中未找到ID为 {question_id} 的题目")
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": f"未找到ID为 {question_id} 的题目"
                }
            )

        print(f"🗑️ 要删除的题目：")
        print(f"   ID：{question_id}")
        print(f"   文章：{deleted_question.get('article', '')}")
        print(f"   题型：{deleted_question.get('title_category_name', '')}")
        print(f"   题目：{deleted_question.get('title', '')[:30]}...")

        # ----------------------------------------------------
        # 4. 从 _new.json 中删除
        # ----------------------------------------------------
        new_questions.pop(deleted_index)

        try:
            with open(new_file, "w", encoding="utf-8") as f:
                json.dump(new_questions, f, ensure_ascii=False, indent=2)
            print(f"✅ 已从 _new.json 删除，剩余 {len(new_questions)} 道")
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"保存 _new.json 失败：{e}"
                }
            )

        # ----------------------------------------------------
        # 5. 从历史题库中删除（只用ID匹配）
        # ----------------------------------------------------
        history_file = find_question_file()
        
        if history_file is None:
            print("⚠️ 没有找到历史题库文件")
        else:
            print(f"📄 历史题库文件：{history_file.name}")
            
            history_questions = read_json_file(history_file)
            
            if history_questions is not None and isinstance(history_questions, list):
                
                original_count = len(history_questions)
                deleted_from_history = False
                
                # ✅ 只通过ID匹配
                for i, q in enumerate(history_questions):
                    if q.get("id") == question_id:
                        removed = history_questions.pop(i)
                        deleted_from_history = True
                        print(f"✅ 已从历史题库删除（ID匹配）：{removed.get('title', '')[:30]}...")
                        break
                
                if deleted_from_history:
                    try:
                        with open(history_file, "w", encoding="utf-8") as f:
                            json.dump(history_questions, f, ensure_ascii=False, indent=2)
                        print(f"✅ 历史题库更新完成，删除前 {original_count} 道，删除后 {len(history_questions)} 道")
                    except Exception as e:
                        print(f"❌ 保存历史题库失败：{e}")
                        return JSONResponse(
                            status_code=500,
                            content={
                                "success": False,
                                "message": f"保存历史题库失败：{e}"
                            }
                        )
                else:
                    print("ℹ️ 历史题库中没有找到相同ID的题目，跳过")
            else:
                print("⚠️ 无法读取历史题库")

        print("=" * 60)
        print()

        return {
            "success": True,
            "message": f"删除成功，_new.json 剩余 {len(new_questions)} 道题",
            "data": {
                "remaining": len(new_questions),
                "deleted": deleted_question
            }
        }

    except Exception as e:

        print()
        print("=" * 60)
        print("删除新题失败")
        print("=" * 60)
        print(e)
        print()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"删除失败：{e}"
            }
        )
        
 # ============================================================
# 37. 从题库中删除题目（通过ID精确删除，同步删除 _new.json 和历史题库）
#
# POST /api/questions/delete-bank
#
# ============================================================

@app.post("/api/questions/delete-bank")
def delete_bank_question(
    data: dict = Body(...)
):
    """
    通过题目ID精确删除
    同时从 _new.json 和历史题库中删除
    
    请求体：
    {
        "id": "uuid",         // ✅ 题目的唯一ID
        "question": {...}     // 完整的题目对象（备用）
    }
    """
    try:

        print()
        print("=" * 80)
        print("🗑️ 通过ID精确删除题目")
        print("=" * 80)

        # ----------------------------------------------------
        # 参数检查
        # ----------------------------------------------------
        if not isinstance(data, dict):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "参数必须是对象"
                }
            )

        # ✅ 优先使用 id
        question_id = data.get("id")
        question = data.get("question")

        # 如果没有 id，从 question 中取
        if not question_id and question and isinstance(question, dict):
            question_id = question.get("id")

        if not question_id:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "缺少 id 参数，无法精确删除"
                }
            )

        print(f"📌 要删除的题目ID：{question_id}")
        print("=" * 80)

        total_deleted = 0
        deleted_from = []

        # ====================================================
        # 第一步：从 _new.json 中删除
        # ====================================================
        new_files = list(QUESTIONS_DIR.glob("*_new.json"))
        
        if new_files:
            new_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for new_file in new_files:
                print(f"📄 处理 _new.json：{new_file.name}")
                
                try:
                    with open(new_file, "r", encoding="utf-8") as f:
                        new_questions = json.load(f)
                except Exception as e:
                    print(f"   ❌ 读取失败：{e}")
                    continue
                
                if not isinstance(new_questions, list):
                    new_questions = []
                
                original_count = len(new_questions)
                print(f"   _new.json 当前有 {original_count} 道题")
                
                # ✅ 通过ID查找并删除
                deleted = False
                for i, q in enumerate(new_questions):
                    if q.get("id") == question_id:
                        removed = new_questions.pop(i)
                        deleted = True
                        total_deleted += 1
                        deleted_from.append("_new.json")
                        print(f"   ✅ 从 _new.json 删除：{removed.get('title', '')[:30]}...")
                        break
                
                if deleted:
                    try:
                        with open(new_file, "w", encoding="utf-8") as f:
                            json.dump(new_questions, f, ensure_ascii=False, indent=2)
                        print(f"   ✅ _new.json 保存成功，剩余 {len(new_questions)} 道")
                    except Exception as e:
                        print(f"   ❌ 保存失败：{e}")
                else:
                    print(f"   ⚠️ 在 _new.json 中未找到ID为 {question_id} 的题目")
        else:
            print("ℹ️ 没有找到 _new.json 文件")

        # ====================================================
        # 第二步：从历史题库中删除
        # ====================================================
        history_file = find_question_file()
        
        if history_file:
            print()
            print(f"📄 处理历史题库：{history_file.name}")
            
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history_questions = json.load(f)
            except Exception as e:
                print(f"   ❌ 读取失败：{e}")
                history_questions = []
            
            if not isinstance(history_questions, list):
                history_questions = []
            
            original_count = len(history_questions)
            print(f"   历史题库当前有 {original_count} 道题")
            
            # ✅ 通过ID查找并删除
            deleted = False
            for i, q in enumerate(history_questions):
                if q.get("id") == question_id:
                    removed = history_questions.pop(i)
                    deleted = True
                    total_deleted += 1
                    deleted_from.append("history")
                    print(f"   ✅ 从历史题库删除：{removed.get('title', '')[:30]}...")
                    break
            
            if deleted:
                try:
                    with open(history_file, "w", encoding="utf-8") as f:
                        json.dump(history_questions, f, ensure_ascii=False, indent=2)
                    print(f"   ✅ 历史题库保存成功，剩余 {len(history_questions)} 道")
                except Exception as e:
                    print(f"   ❌ 保存失败：{e}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "message": f"保存历史题库失败：{e}"
                        }
                    )
            else:
                print(f"   ⚠️ 在历史题库中未找到ID为 {question_id} 的题目")
        else:
            print("ℹ️ 没有找到历史题库文件")

        # ====================================================
        # 返回结果
        # ====================================================
        print()
        print("=" * 80)
        if total_deleted > 0:
            print(f"✅ 删除成功，共删除 {total_deleted} 道题")
            print(f"   删除来源：{', '.join(set(deleted_from))}")
        else:
            print(f"⚠️ 未找到ID为 {question_id} 的题目")
        print("=" * 80)
        print()

        return {
            "success": True,
            "message": f"删除完成，共删除 {total_deleted} 道题",
            "data": {
                "deleted_count": total_deleted,
                "deleted_from": list(set(deleted_from))
            }
        }

    except Exception as e:

        print()
        print("=" * 80)
        print("❌ 删除题目失败")
        print("=" * 80)
        print(f"异常类型：{type(e).__name__}")
        print(f"异常信息：{e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"删除失败：{str(e)}"
            }
        )