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
import os
from pathlib import Path
import asyncio

from fastapi import FastAPI, Body, Request, UploadFile, File, Depends
import shutil 
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ai_config import (
    get_ai_config,
    get_public_ai_config,
    save_ai_config
)

import uvicorn

from auth import require_login, get_current_user

import secrets
from starlette.middleware.sessions import SessionMiddleware


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

# ✅ 新增：知识库目录（每个 PDF 独立存储）
KNOWLEDGE_DIR = DATA_DIR / "knowledge"

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

# ✅ 新增：创建 knowledge 目录
KNOWLEDGE_DIR.mkdir(
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

# ✅ 新增：挂载PDF目录
app.mount(
    "/pdfs",  # URL访问路径
    StaticFiles(
        directory=str(PDF_DIR)  
    ),
    name="pdfs"
)

print(f"\n✅ 静态目录挂载完成：")
print(f"  /static → {STATIC_DIR}")
print(f"  /pdfs   → {PDF_DIR}\n")

# ============================================================
# 8. HTML模板
# ============================================================

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR)
)

# ============================================================
# Session 中间件
# ============================================================

SECRET_KEY = os.environ.get(
    'SESSION_SECRET_KEY',
    secrets.token_urlsafe(32)
)


# ============================================================
# 全局登录拦截
# ============================================================

from starlette.middleware.base import BaseHTTPMiddleware


class LoginMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        path = request.url.path

        # ==========================================
        # 1. 不需要登录的地址
        # ==========================================
        public_paths = [
            "/login",
            "/sso/login",
            "/favicon.ico",
        ]

        # ==========================================
        # 2. 静态资源放行
        # ==========================================
        if path.startswith("/static/"):
            return await call_next(request)

        # ==========================================
        # 3. 登录页、SSO入口放行
        # ==========================================
        if path in public_paths:
            return await call_next(request)

        # ==========================================
        # 4. 检查当前登录用户
        # ==========================================
        user = await get_current_user(request)

        # ==========================================
        # 5. 没有登录
        # ==========================================
        if not user:

            # API 返回 401
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "message": "未登录，请先登录"
                    }
                )

            # 页面跳转到登录页
            return RedirectResponse(
                url="/login",
                status_code=303
            )

        # ==========================================
        # 6. 已登录
        # ==========================================
        return await call_next(request)



# ============================================================
# 注册中间件
# ============================================================

# 先注册 LoginMiddleware
app.add_middleware(LoginMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    max_age=3600 * 24 * 7,
    same_site="lax",
    https_only=False,
    path="/"
)

print("✅ Session中间件已启用")
print("✅ 全局登录拦截已启用")


# ============================================================
# 导入认证模块并注册路由
# ============================================================

from auth import setup_auth_routes, render_page

setup_auth_routes(app, templates)

print("✅ 认证路由已注册")


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

async def check_page_login(request: Request):
    user = await get_current_user(request)

    if not user:
        return RedirectResponse(url="/login")

    return None


@app.get("/")
async def index(request: Request):
    user = await get_current_user(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.get("/dashboard")
async def dashboard(request: Request):
    return await render_page(
        request,
        "pages/dashboard.html"
    )

@app.get("/knowledge")
async def knowledge(request: Request):
    return await render_page(
        request,
        "pages/knowledge.html"
    )

@app.get("/ai-question")
async def ai_question(request: Request):
    return await render_page(
        request,
        "pages/ai_question.html"
    )

@app.get("/question-bank")
async def question_bank(request: Request):
    return await render_page(
        request,
        "pages/question_bank.html"
    )

@app.get("/system")
async def system(request: Request):
    return await render_page(
        request,
        "pages/system.html"
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

        return {
            "success": True,
            "data": {
                "python": sys.version.split()[0],

                "project_dir": str(BASE_DIR),

                "provider": provider,

                "model": model,

                "base_url": base_url,

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

        config = get_public_ai_config()

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
            "data": {
                "provider": config["provider"],
                "model": config["model"],
                "base_url": config["base_url"],
                "api_key": "******" if config.get("api_key") else ""
            }
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
            "data": {
                "provider": config["provider"],
                "model": config["model"],
                "base_url": config["base_url"],
                "api_key": "******" if config.get("api_key") else ""
            }
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
# ============================================================

@app.get("/api/knowledge/data")
def get_knowledge_data(source: str = None):
    """
    获取知识库数据
    - source: PDF名称（不传则返回所有合并）
    """
    try:
        # 如果没有指定 source，返回所有合并
        if not source:
            all_data = []
            for dir_path in KNOWLEDGE_DIR.iterdir():
                if dir_path.is_dir():
                    json_file = dir_path / "articles.json"
                    if json_file.exists():
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                all_data.extend(data)
            # 过滤有效条文
            article_data = [
                item for item in all_data
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
        
        # 指定了 source，读取对应的知识库
        json_file = KNOWLEDGE_DIR / source / "articles.json"
        if not json_file.exists():
            return {
                "success": True,
                "data": [],
                "count": 0
            }
        
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 过滤有效条文
        article_data = [
            item for item in data
            if isinstance(item, dict)
            and item.get("article")
            and item.get("content")
        ]
        
        return {
            "success": True,
            "message": "读取成功",
            "count": len(article_data),
            "data": article_data,
            "source": source
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"读取知识库失败：{e}",
            "count": 0,
            "data": []
        }


# ============================================================
# ✅ 新增：获取知识库来源列表
# GET /api/knowledge/sources
# ============================================================
# ============================================================
# 25. 读取法规知识库
#
# GET /api/knowledge/data
# ============================================================

@app.get("/api/knowledge/data")
def get_knowledge_data(source: str = None):
    """
    获取知识库数据
    - source: PDF名称（不传则返回所有合并）
    """
    try:
        # 如果没有指定 source，返回所有合并
        if not source:
            all_data = []
            for dir_path in KNOWLEDGE_DIR.iterdir():
                if dir_path.is_dir():
                    json_file = dir_path / "articles.json"
                    if json_file.exists():
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                all_data.extend(data)
            article_data = [
                item for item in all_data
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
        
        # ✅ 处理 source：去掉 .pdf 后缀，因为目录名没有 .pdf
        source_name = source
        if source_name.endswith('.pdf'):
            source_name = source_name[:-4]  # 去掉 .pdf
        
        # 尝试查找目录
        target_dir = None
        
        # 1. 直接查找去掉 .pdf 的目录名
        for dir_path in KNOWLEDGE_DIR.iterdir():
            if dir_path.is_dir() and dir_path.name == source_name:
                target_dir = dir_path
                break
        
        # 2. 如果没找到，尝试模糊匹配
        if not target_dir:
            for dir_path in KNOWLEDGE_DIR.iterdir():
                if dir_path.is_dir() and source_name in dir_path.name:
                    target_dir = dir_path
                    break
        
        if not target_dir:
            # 返回空数据
            return {
                "success": True,
                "data": [],
                "count": 0,
                "source": source,
                "message": f"未找到知识库：{source_name}"
            }
        
        json_file = target_dir / "articles.json"
        if not json_file.exists():
            return {
                "success": True,
                "data": [],
                "count": 0
            }
        
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        article_data = [
            item for item in data
            if isinstance(item, dict)
            and item.get("article")
            and item.get("content")
        ]
        
        return {
            "success": True,
            "message": "读取成功",
            "count": len(article_data),
            "data": article_data,
            "source": source_name
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
# ============================================================

@app.get("/api/knowledge/statistics")
def get_knowledge_statistics(
     user: dict = Depends(require_login)
):
    print("当前用户:", user.get("user_name"))
    print("当前部门:", user.get("subjection_name"))
    print("当前矿井:", user.get("register_dept_Name"))
    try:
        total = 0
        sources = []
        
        for dir_path in KNOWLEDGE_DIR.iterdir():
            if dir_path.is_dir():
                json_file = dir_path / "articles.json"
                if json_file.exists():
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            count = len(data)
                            total += count
                            sources.append({
                                "name": dir_path.name,
                                "count": count
                            })
        
        return {
            "success": True,
            "data": {
                "total": total,
                "sources": sources
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"统计失败：{e}",
            "data": {
                "total": 0,
                "sources": []
            }
        }

        

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
        # 3. 接收分类（工种）信息
        # ----------------------------------------------------

        dept = data.get("dept", {})
        dept_id = dept.get("id", "")
        dept_name = dept.get("fullName", "")
        superior_name = dept.get("superiorName", "")

        # ----------------------------------------------------
        # 4. ✅ 获取当前选中的 PDF（从请求中读取 source）
        # ----------------------------------------------------

        source = data.get("source", "")

        # 如果没有传 source，从配置读取当前使用的 PDF
        if not source:
            config_file = CONFIG_DIR / "pdf_config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    source = config.get("current_pdf", "")

        # ----------------------------------------------------
        # 5. 设置AI服务商
        # ----------------------------------------------------

        import ai_client

        ai_client.set_ai_type(provider)

        # ----------------------------------------------------
        # 6. 导入出题模块
        # ----------------------------------------------------

        import generate_questions as question_generator

        # ----------------------------------------------------
        # 7. 创建 SSE 流式生成器
        # ----------------------------------------------------

        async def event_generator():

            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'message': '开始生成题目...', 'total': count})}\n\n"

            # 用于收集所有题目
            all_questions = []
            success_count = 0
            failed_count = 0

            # ====================================================
            # ✅ 8. 根据 source 读取对应的知识库
            # ====================================================

            articles = []
            law_name = "法规"

            if source:
                # 去掉 .pdf 后缀
                source_name = source
                if source_name.endswith('.pdf'):
                    source_name = source_name[:-4]

                # 读取对应目录的知识库
                json_file = KNOWLEDGE_DIR / source_name / "articles.json"
                if json_file.exists():
                    with open(json_file, "r", encoding="utf-8") as f:
                        articles = json.load(f)
                    print(f"📄 出题使用知识库：{source_name}")
                    law_name = source_name
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'找不到知识库：{source_name}'})}\n\n"
                    return
            else:
                # 没有指定 source，合并所有知识库
                for dir_path in KNOWLEDGE_DIR.iterdir():
                    if dir_path.is_dir():
                        json_file = dir_path / "articles.json"
                        if json_file.exists():
                            with open(json_file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    articles.extend(data)
                print(f"📄 出题使用全部知识库，共 {len(articles)} 条")

            if not articles:
                yield f"data: {json.dumps({'type': 'error', 'message': '没有找到可用的法规知识库'})}\n\n"
                return

            if not isinstance(articles, list):
                yield f"data: {json.dumps({'type': 'error', 'message': '法规知识库格式错误'})}\n\n"
                return

            # 获取法规名称（从第一条数据中提取）
            law_names = {
                item.get("law_name")
                for item in articles
                if isinstance(item, dict) and item.get("law_name")
            }

            if law_names:
                law_name = list(law_names)[0]
            else:
                law_name = source if source else "法规"

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
            # ✅ 根据上级名称（大类）过滤法条
            # ----------------------------------------------------

            if superior_name:
                dept_category = get_category_by_superior_name(superior_name)

                article_list = [
                    item for item in article_list
                    if item.get("dept_type_name") == dept_category
                    or item.get("dept_type_name") == "全部工种"
                ]

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

                if question.get("title_category_name") != current_type:
                    failed_questions.add((article, current_type))
                    failed_count += 1
                    continue

                new_questions.append(question)
                used_questions.add((article, current_type))
                success_count += 1

                try:
                    with open(new_questions_file, "w", encoding="utf-8") as f:
                        json.dump(new_questions, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'保存新题失败：{e}'})}\n\n"
                    return

                yield f"data: {json.dumps({'type': 'question', 'question': question, 'index': success_count, 'total': count, 'success': success_count, 'failed': failed_count})}\n\n"

                await asyncio.sleep(0.1)

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
    request: Request,
    data: dict = Body(...),
    user: dict = Depends(require_login)
):
    """
    将题目导入到MySQL数据库

    当前登录用户：
        Python Session 中的用户

    Java Token：
        Python Session 中的 java_token

    调用链：
        Python → Java Gateway → Java导入接口 → MySQL
    """

    try:

        # ====================================================
        # 1. 当前登录用户
        # ====================================================

        user_id = user.get("id")
        user_name = user.get("user_name")
        dept_name = user.get("subjection_name")

        # 这里你原来写的是 register_dept_Name
        # 注意大小写应该和 get_current_user() 返回的数据一致
        mine_name = user.get("register_dept_name")

        print("========================================")
        print("       当前导入操作用户")
        print("========================================")
        print(f"用户ID   : {user_id}")
        print(f"用户     : {user_name}")
        print(f"部门     : {dept_name}")
        print(f"矿井     : {mine_name}")
        print("========================================")

        # ====================================================
        # 2. 获取当前 Java 登录 Token
        # ====================================================

        java_token = request.session.get("java_token")

        if not java_token:

            print("❌ 当前 Python Session 没有 Java Token")

            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "Java登录状态已失效，请重新进入通用法规 AI"
                }
            )

        print("✅ 当前 Java Token：已获取")

        # ====================================================
        # 3. 强制使用当前登录用户
        # ====================================================

        data["create_user_id"] = user_id
        data["create_user_name"] = user_name
        data["create_dept_name"] = dept_name
        data["create_mine_name"] = mine_name

        print()

        print("=" * 60)
        print("开始导入题目到数据库")
        print("=" * 60)

        # ====================================================
        # 4. 参数检查
        # ====================================================

        if not isinstance(data, dict):

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "导入参数必须是对象"
                }
            )

        # ====================================================
        # 5. 获取题目
        # ====================================================

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

        # ====================================================
        # 6. 数量检查
        # ====================================================

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

        # ====================================================
        # 7. 导入数据库模块
        # ====================================================

        import import_questions_db

        # ====================================================
        # 8. 调用 Java 导入函数
        #
        # 关键：
        # 把当前 Java Token 传进去
        # ====================================================

        result = import_questions_db.main(
            data=data,
            java_token=java_token
        )

        # ====================================================
        # 9. 检查返回
        # ====================================================

        if result is None:

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "导入程序没有返回结果"
                }
            )

        # ====================================================
        # 10. 返回结果
        # ====================================================

        print()

        print("=" * 60)
        print("导入完成")
        print()
        print(
            f"处理：{result.get('total', 0)} 道"
        )
        print(
            f"成功：{result.get('inserted', 0)} 道"
        )
        print(
            f"跳过：{result.get('skipped', 0)} 道"
        )
        print("=" * 60)
        print()

        return {
            "success": True,
            "message": (
                f"成功导入 "
                f"{result.get('inserted', 0)} 道题"
            ),
            "data": result
        }

    # ========================================================
    # 11. 找不到导入模块
    # ========================================================

    except ModuleNotFoundError as e:

        print()
        print("找不到 import_questions_db.py")
        print(e)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": (
                    "找不到 import_questions_db.py，"
                    "请检查文件是否存在"
                )
            }
        )

    # ========================================================
    # 12. 其他异常
    # ========================================================

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
                "message": (
                    f"导入数据库失败：{e}"
                )
            }
        )


# ============================================================
# 获取题库分类列表（从 Java 后端获取）
#
# GET /api/dept/list
#
# ============================================================

@app.get("/api/dept/list")
def get_dept_list(request: Request):
    """
    从 Java 后端获取题库分类列表（包含层级结构）
    根据当前 Java 登录用户所在矿井过滤分类
    """
    try:
        import requests

        user = request.session.get("user")

        print("当前用户:", user.get("user_name"))
        print("当前部门:", user.get("subjection_name"))
        print("当前矿井ID:", user.get("register_dept_id"))
        print("当前矿井:", user.get("register_dept_name"))

        # 从环境变量读取 Java 后端地址
        java_host = os.environ.get('JAVA_HOST', 'localhost')
        java_port = os.environ.get('JAVA_PORT', '1100')

        # 改为调用原来的登录接口
        java_api_url = (
            f"http://{java_host}:{java_port}"
            f"/deptBankType/getExcelTypeSelect"
        )

        print(f"🔗 连接 Java 后端：{java_api_url}")

        # 获取当前 Python Session 中保存的 Java Token
        java_token = request.session.get("java_token")

        if not java_token:
            print("❌ 当前 Python Session 没有 Java Token")

            return {
                "success": False,
                "message": "Java登录状态已失效，请重新进入通用法规 AI",
                "data": []
            }

        print("✅ 当前 Java Token：已获取")

        # 携带 Java Token 调用原接口
        response = requests.get(
            java_api_url,
            timeout=10,
            headers={
                "Content-Type": "application/json",
                "satoken": java_token
            }
        )
        print("Java HTTP状态:", response.status_code)
        print("Java原始返回:")
        print(response.text[:5000])

        if response.status_code == 200:

            # Java 原接口直接返回数组
            data = response.json()

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

            print(
                f"✅ 成功获取当前用户矿井分类："
                f"{len(root_list)} 个根节点"
            )

            return {
                "success": True,
                "data": root_list
            }

        else:

            print(
                f"⚠️ Java 返回错误："
                f"{response.status_code}"
            )

            # 这里建议不要再使用本地假数据
            # 否则 Java Token 失效后可能看到错误矿井的数据
            return {
                "success": False,
                "message": (
                    f"获取分类失败：HTTP "
                    f"{response.status_code}"
                ),
                "data": []
            }

    except requests.exceptions.ConnectionError:

        print("❌ Java 后端未连接")

        return {
            "success": False,
            "message": "Java 后端未连接",
            "data": []
        }

    except Exception as e:

        print(f"❌ 获取分类异常：{e}")

        return {
            "success": False,
            "message": f"获取分类失败：{str(e)}",
            "data": []
        }

    
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
# PDF 上传接口
# POST /api/pdf/upload
# ============================================================

import hashlib

@app.post("/api/pdf/upload")
async def upload_pdf(
    files: list[UploadFile] = File(...)
):
    """
    上传 PDF 文件到服务器
    """
    try:
        # ✅ 如果没有上传任何文件
        if not files:
            return {
                "success": False,
                "message": "没有选择任何文件",
                "data": []
            }
        
        uploaded_files = []
        duplicate_files = []
        skipped_files = []  # 非PDF文件
        
        for file in files:
            # 检查是否是 PDF
            if not file.filename.endswith('.pdf'):
                skipped_files.append({
                    "filename": file.filename,
                    "reason": "不是PDF文件"
                })
                continue
            
            # ✅ 安全处理文件名
            filename = file.filename.replace('/', '_').replace('\\', '_').replace(' ', '_')
            
            # ✅ 读取文件内容
            content = await file.read()
            
            # ✅ 计算文件 MD5
            md5_hash = hashlib.md5(content).hexdigest()
            
            # ✅ 检查是否存在相同 MD5 的文件
            is_duplicate = False
            duplicate_info = None
            for existing_file in PDF_DIR.iterdir():
                if existing_file.is_file() and existing_file.suffix == '.pdf':
                    with open(existing_file, 'rb') as f:
                        existing_md5 = hashlib.md5(f.read()).hexdigest()
                        if existing_md5 == md5_hash:
                            is_duplicate = True
                            duplicate_info = {
                                "filename": file.filename,
                                "existing_file": existing_file.name,
                                "reason": "文件内容完全相同"
                            }
                            break
            
            if is_duplicate:
                duplicate_files.append(duplicate_info)
                continue
            
            # ✅ 如果文件名已存在，添加序号
            file_path = PDF_DIR / filename
            if file_path.exists():
                base = file_path.stem
                ext = file_path.suffix
                counter = 1
                while file_path.exists():
                    file_path = PDF_DIR / f"{base}_{counter}{ext}"
                    counter += 1
            
            # 保存文件
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            uploaded_files.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "md5": md5_hash
            })
        
        # ✅ 构建详细的返回信息
        total = len(files)
        uploaded_count = len(uploaded_files)
        duplicate_count = len(duplicate_files)
        skipped_count = len(skipped_files)
        
        # ✅ 智能构建消息
        if uploaded_count == 0 and duplicate_count > 0:
            # 所有文件都是重复的
            message = f"所有 {duplicate_count} 个文件均为重复文件，已跳过上传"
        elif uploaded_count == 0 and skipped_count > 0:
            # 所有文件都不是PDF
            message = f"所有 {skipped_count} 个文件都不是PDF格式，已跳过"
        elif uploaded_count == 0 and duplicate_count == 0 and skipped_count == 0:
            # 理论上不会发生，但以防万一
            message = "没有文件被上传"
        elif uploaded_count > 0 and duplicate_count > 0:
            # 部分上传，部分重复
            message = f"成功上传 {uploaded_count} 个文件，{duplicate_count} 个文件重复被跳过"
            if skipped_count > 0:
                message += f"，{skipped_count} 个非PDF文件被忽略"
        elif uploaded_count > 0:
            # 全部成功上传
            message = f"成功上传 {uploaded_count} 个文件"
            if skipped_count > 0:
                message += f"，{skipped_count} 个非PDF文件被忽略"
        else:
            message = "没有文件被上传"
        
        return {
            "success": uploaded_count > 0 or duplicate_count > 0,  # 如果有文件处理就算成功
            "message": message,
            "data": uploaded_files,  # 成功上传的文件
            "summary": {
                "total": total,
                "uploaded": uploaded_count,
                "duplicates": duplicate_count,
                "skipped": skipped_count
            },
            "duplicates": duplicate_files,  # 重复文件列表
            "skipped": skipped_files  # 跳过的文件列表
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"上传失败：{e}",
            "data": []
        }

        
# ============================================================
# 获取 PDF 列表
# GET /api/pdf/list
# ============================================================

@app.get("/api/pdf/list")
def list_pdfs():
    """
    获取所有 PDF 文件列表
    """
    try:
        pdfs = []
        for f in PDF_DIR.glob("*.pdf"):
            pdfs.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime
            })
        return {
            "success": True,
            "data": pdfs
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取列表失败：{e}"
        }


# ============================================================
# 选择当前使用的 PDF
# POST /api/pdf/select
# ============================================================

@app.post("/api/pdf/select")
def select_pdf(data: dict = Body(...)):
    """
    选择当前使用的 PDF
    """
    try:
        filename = data.get("filename")
        if not filename:
            return {
                "success": False,
                "message": "缺少 filename 参数"
            }
        
        # 保存到配置文件
        config_file = CONFIG_DIR / "pdf_config.json"
        config = {}
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        
        config["current_pdf"] = filename
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": f"已切换到：{filename}",
            "data": {"current_pdf": filename}
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"切换失败：{e}"
        }


# ============================================================
# 获取当前使用的 PDF
# GET /api/pdf/current
# ============================================================

@app.get("/api/pdf/current")
def get_current_pdf():
    """
    获取当前使用的 PDF
    """
    try:
        config_file = CONFIG_DIR / "pdf_config.json"
        current_pdf = None
        
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                current_pdf = config.get("current_pdf")
        
        # ✅ 检查文件是否存在
        if current_pdf:
            file_path = PDF_DIR / current_pdf
            if not file_path.exists():
                # ✅ 文件不存在，清除配置
                if config_file.exists():
                    with open(config_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    config["current_pdf"] = None
                    with open(config_file, "w", encoding="utf-8") as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                current_pdf = None
        
        return {
            "success": True,
            "data": {"current_pdf": current_pdf}
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取失败：{e}"
        }

# ============================================================
# 删除 PDF（增强版）
# DELETE /api/pdf/delete
# ============================================================

@app.delete("/api/pdf/delete")
def delete_pdf(filename: str):
    """
    删除 PDF 文件
    """
    try:
        # ✅ 安全检查：防止路径遍历攻击
        import re
        if not re.match(r'^[\w\u4e00-\u9fa5\-_.]+$', filename):
            return {
                "success": False,
                "message": "文件名包含非法字符"
            }
        
        # ✅ 确保文件名以 .pdf 结尾
        if not filename.lower().endswith('.pdf'):
            return {
                "success": False,
                "message": "只能删除 PDF 文件"
            }
        
        file_path = PDF_DIR / filename
        
        # ✅ 检查文件是否存在
        if not file_path.exists():
            return {
                "success": False,
                "message": f"文件不存在：{filename}"
            }
        
        # ✅ 检查是否是文件（不是目录）
        if not file_path.is_file():
            return {
                "success": False,
                "message": f"{filename} 不是文件"
            }
        
        # ✅ 删除文件
        file_path.unlink()
        
        # ✅ 如果删除的是当前使用的 PDF，清除配置
        config_file = CONFIG_DIR / "pdf_config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            if config.get("current_pdf") == filename:
                config["current_pdf"] = None
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": f"已删除：{filename}"
        }
        
    except PermissionError:
        return {
            "success": False,
            "message": f"没有权限删除文件：{filename}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"删除失败：{e}"
        }



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
        "http://127.0.0.1:8765"  # ← 8765 → 8765
    )

    print()

    print(
        "工作台："
    )

    print(
        "http://127.0.0.1:8765/dashboard"  # ← 8765 → 8765
    )

    print()

    print(
        "法规知识库："
    )

    print(
        "http://127.0.0.1:8765/knowledge"  # ← 8765 → 8765
    )

    print()

    print(
        "AI智能出题："
    )

    print(
        "http://127.0.0.1:8765/ai-question"  # ← 8765 → 8765
    )

    print()

    print(
        "题库管理："
    )

    print(
        "http://127.0.0.1:8765/question-bank"  # ← 8765 → 8765
    )

    print()

    print(
        "系统设置："
    )

    print(
        "http://127.0.0.1:8765/system"  # ← 8765 → 8765
    )

    print()

    print(
        "API文档："
    )

    print(
        "http://127.0.0.1:8765/docs"  # ← 8765 → 8765
    )

    print()

    print("=" * 60)
    print()

    # ============================================================
    # 启动服务
    # ============================================================
    import os
    
    port = int(os.environ.get('PORT', 8765))  # ← 这个也要确认是 8765
    
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    if debug_mode:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=True
        )
    else:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port
        )

