# # auth.py - 认证模块
# #
# # 当前架构：
# # Java 负责登录、密码验证、Sa-Token
# # Python 不再直接连接 MySQL
# # Python 不再验证用户名和密码
# #
# # 登录流程：
# #
# # Java 登录
# #     ↓
# # Java Token
# #     ↓
# # 点击菜单进入 Python
# #     ↓
# # Python /sso/login?token=xxx
# #     ↓
# # Java /python/user-info 验证 Token
# #     ↓
# # Python 清理旧 Session
# #     ↓
# # Python 暂存 sso_user
# #     ↓
# # Python /login 登录页
# #     ↓
# # 用户输入密码点击【登录】
# #     ↓
# # Python 调用 Java /python/verify-password
# #     ↓
# # Java 验证密码
# #     ↓
# # 验证成功
# #     ↓
# # Python 正式 Session
# #     ↓
# # Python 首页


# import os
# import requests

# from fastapi import Request, Depends, HTTPException
# from fastapi.responses import RedirectResponse, JSONResponse


# # ============================================================
# # Java 服务配置
# # ============================================================

# JAVA_BASE_URL = os.getenv(
#     "JAVA_BASE_URL",
#     "http://localhost:1100"
# )

# JAVA_USER_INFO_URL = (
#     f"{JAVA_BASE_URL}/python/user-info"
# )

# JAVA_VERIFY_PASSWORD_URL = (
#     f"{JAVA_BASE_URL}/python/verify-password"
# )


# # ============================================================
# # 从请求中获取 Java Sa-Token
# # ============================================================

# def get_java_token(request: Request):
#     """
#     从请求 Header 中获取 Java 登录 Token。

#     当前兼容：
#     1. Authorization: token
#     2. Authorization: Bearer token
#     3. satoken: token
#     4. token: token

#     Java 实际验证使用 satoken。
#     """

#     # --------------------------------------------------------
#     # 1. Authorization
#     # --------------------------------------------------------

#     authorization = request.headers.get("Authorization")

#     if authorization:
#         authorization = authorization.strip()

#         if authorization.lower().startswith("bearer "):
#             return authorization[7:].strip()

#         return authorization

#     # --------------------------------------------------------
#     # 2. satoken
#     # --------------------------------------------------------

#     token = request.headers.get("satoken")

#     if token:
#         return token.strip().strip('"')

#     # --------------------------------------------------------
#     # 3. token
#     # --------------------------------------------------------

#     token = request.headers.get("token")

#     if token:
#         return token.strip().strip('"')

#     return None


# # ============================================================
# # 调用 Java 获取当前登录用户
# # ============================================================

# async def get_current_user(request: Request):

#     # --------------------------------------------------------
#     # ① 优先从 Python Session 获取用户
#     # --------------------------------------------------------
#     session_user = request.session.get("user")

#     if session_user:
#         print(
#             f"✅ 从 Python Session 获取当前用户: "
#             f"{session_user.get('user_name')}"
#         )
#         return session_user

#     # --------------------------------------------------------
#     # ② Session 没有，再从请求 Header 获取 Java Token
#     # --------------------------------------------------------

#     token = get_java_token(request)

#     if not token:
#         print("❌ 当前请求没有 Java Token")
#         return None

#     # 防止 localStorage 序列化后出现：
#     # "LGITBgKtCl2..."
#     token = token.strip().strip('"')

#     # --------------------------------------------------------
#     # ③ 调用 Java
#     # --------------------------------------------------------

#     try:

#         print("========================================")
#         print("       获取 Java 当前登录用户")
#         print("========================================")

#         print(
#             f"🔗 Java 用户接口: "
#             f"{JAVA_USER_INFO_URL}"
#         )

#         response = requests.get(
#             JAVA_USER_INFO_URL,
#             headers={
#                 "satoken": token
#             },
#             timeout=10
#         )

#         print(
#             f"📡 Java HTTP状态: "
#             f"{response.status_code}"
#         )

#         # ----------------------------------------------------
#         # HTTP状态检查
#         # ----------------------------------------------------

#         if response.status_code != 200:

#             print(
#                 f"❌ Java 用户接口返回 HTTP "
#                 f"{response.status_code}"
#             )

#             print(
#                 f"返回内容: "
#                 f"{response.text[:500]}"
#             )

#             return None

#         # ----------------------------------------------------
#         # JSON解析
#         # ----------------------------------------------------

#         result = response.json()

#         print(
#             f"📦 Java 用户接口返回: "
#             f"{result}"
#         )

#         # ----------------------------------------------------
#         # SaResult 判断
#         # ----------------------------------------------------

#         if result.get("code") != 200:

#             print(
#                 f"❌ Java 用户验证失败: "
#                 f"{result.get('msg')}"
#             )

#             return None

#         # ----------------------------------------------------
#         # 获取用户数据
#         # ----------------------------------------------------

#         user = result.get("data")

#         if not user:

#             print(
#                 "❌ Java 没有返回用户信息"
#             )

#             return None

#         # ----------------------------------------------------
#         # 转换成 Python 项目原来的用户结构
#         # ----------------------------------------------------

#         current_user = {

#             # 用户ID
#             "id": user.get("user_id"),
#             "user_id": user.get("user_id"),

#             # 用户名
#             "user_name": user.get("user_name"),

#             # 用户编码
#             "user_code": user.get("user_code"),

#             # 手机号
#             "phone": user.get("phone"),

#             # 职务
#             "duties_name": user.get("duties_name"),

#             # 岗位
#             "post_name": user.get("post_name"),

#             # 所属部门
#             "subjection_id": user.get("subjection_id"),
#             "subjection_name": user.get("subjection_name"),

#             # 注册矿井 / 部门
#             "register_dept_id": user.get("register_dept_id"),
#             "register_dept_name": user.get("register_dept_name"),

#             # 兼容原 Python 项目
#             "mine_id": user.get("register_dept_id"),
#             "mine_name": user.get("register_dept_name"),

#             # 保存 Java Token
#             "_java_token": token
#         }

#         # ----------------------------------------------------
#         # 打印用户
#         # ----------------------------------------------------

#         print("----------------------------------------")

#         print(
#             f"用户ID   : "
#             f"{current_user.get('user_id')}"
#         )

#         print(
#             f"登录人   : "
#             f"{current_user.get('user_name')}"
#         )

#         print(
#             f"部门ID   : "
#             f"{current_user.get('subjection_id')}"
#         )

#         print(
#             f"部门     : "
#             f"{current_user.get('subjection_name')}"
#         )

#         print(
#             f"矿井ID   : "
#             f"{current_user.get('register_dept_id')}"
#         )

#         print(
#             f"矿井     : "
#             f"{current_user.get('register_dept_name')}"
#         )

#         print("----------------------------------------")

#         print(
#             "✅ Java 当前登录用户获取成功"
#         )

#         print("========================================")

#         return current_user

#     # --------------------------------------------------------
#     # 网络异常
#     # --------------------------------------------------------

#     except requests.exceptions.Timeout:

#         print(
#             "❌ 调用 Java 用户接口超时"
#         )

#         return None

#     except requests.exceptions.ConnectionError as e:

#         print(
#             f"❌ 无法连接 Java Gateway: {e}"
#         )

#         return None

#     except requests.exceptions.RequestException as e:

#         print(
#             f"❌ 调用 Java 用户接口失败: {e}"
#         )

#         return None

#     # --------------------------------------------------------
#     # JSON / 其它异常
#     # --------------------------------------------------------

#     except ValueError as e:

#         print(
#             f"❌ Java 返回的数据不是合法 JSON: {e}"
#         )

#         return None

#     except Exception as e:

#         print(
#             f"❌ 获取 Java 当前用户失败: {e}"
#         )

#         import traceback
#         traceback.print_exc()

#         return None


# # ============================================================
# # 依赖注入：必须登录
# # ============================================================

# async def require_login(
#     user: dict = Depends(get_current_user)
# ):

#     if not user:

#         raise HTTPException(
#             status_code=401,
#             detail="未登录或 Java 登录已失效"
#         )

#     return user


# # ============================================================
# # 依赖注入：页面登录检查
# # ============================================================

# async def require_login_redirect(
#     request: Request,
#     user: dict = Depends(get_current_user)
# ):

#     if not user:

#         return RedirectResponse(
#             url="/login",
#             status_code=303
#         )

#     return user


# # ============================================================
# # 页面渲染封装
# # ============================================================

# _templates = None


# def set_templates(templates):

#     global _templates

#     _templates = templates


# async def render_page(
#     request: Request,
#     template_name: str,
#     extra_data: dict = None
# ):

#     # --------------------------------------------------------
#     # 检查 Python 正式登录状态
#     # --------------------------------------------------------

#     user = await get_current_user(request)

#     if not user:

#         return RedirectResponse(
#             url="/login",
#             status_code=303
#         )

#     # --------------------------------------------------------
#     # 模板数据
#     # --------------------------------------------------------

#     data = {
#         "request": request
#     }

#     # --------------------------------------------------------
#     # 用户名
#     # --------------------------------------------------------

#     data["username"] = (
#         user.get("user_name")
#         or user.get("user_code")
#         or user.get("phone")
#         or ""
#     )

#     # --------------------------------------------------------
#     # 角色
#     # --------------------------------------------------------

#     data["role"] = (
#         user.get("duties_name")
#         or user.get("post_name")
#         or "普通用户"
#     )

#     # --------------------------------------------------------
#     # 完整用户
#     # --------------------------------------------------------

#     data["user"] = user

#     # --------------------------------------------------------
#     # 额外数据
#     # --------------------------------------------------------

#     if extra_data:
#         data.update(extra_data)

#     # --------------------------------------------------------
#     # 模板
#     # --------------------------------------------------------

#     return _templates.TemplateResponse(
#         template_name,
#         data
#     )


# # ============================================================
# # 设置认证路由
# # ============================================================

# def setup_auth_routes(app, templates):

#     set_templates(templates)

#     # ========================================================
#     # ① Java → Python SSO
#     # ========================================================

#     @app.get("/sso/login")
#     async def sso_login(
#         request: Request
#     ):

#         print("========================================")
#         print("🔗 进入 Python /sso/login")
#         print("========================================")

#         token = request.query_params.get("token")

#         print(
#             "是否获取到 token：",
#             bool(token)
#         )

#         if token:
#             print(
#                 "token 长度：",
#                 len(token)
#             )

#         print(
#             "🔥 当前URL:",
#             str(request.url)
#         )

#         # ----------------------------------------------------
#         # 获取 Java Token
#         # ----------------------------------------------------

#         token = request.query_params.get("token")

#         print(
#             "🔥 URL Token:",
#             bool(token)
#         )

#         # ----------------------------------------------------
#         # 如果 URL 没有 Token
#         # 再尝试 Header
#         # ----------------------------------------------------

#         if not token:
#             token = get_java_token(request)

#         # ----------------------------------------------------
#         # Token 不存在
#         # ----------------------------------------------------

#         if not token:

#             print(
#                 "❌ SSO 没有获取到 Java Token"
#             )

#             return JSONResponse(
#                 status_code=401,
#                 content={
#                     "code": 401,
#                     "msg": "没有获取到 Java 登录 Token"
#                 }
#             )

#         # ----------------------------------------------------
#         # 清理 Token
#         # ----------------------------------------------------

#         token = token.strip().strip('"')

#         print(
#             f"🔑 收到 Java Token: "
#             f"{token[:10]}..."
#         )

#         # ----------------------------------------------------
#         # 调用 Java 获取用户
#         # ----------------------------------------------------

#         try:

#             response = requests.get(
#                 JAVA_USER_INFO_URL,
#                 headers={
#                     "satoken": token
#                 },
#                 timeout=10
#             )

#             print(
#                 f"📡 Java HTTP状态: "
#                 f"{response.status_code}"
#             )

#             print(
#                 f"📦 Java返回内容: "
#                 f"{response.text[:1000]}"
#             )

#         except requests.exceptions.Timeout:

#             print(
#                 "❌ Java 用户接口超时"
#             )

#             return JSONResponse(
#                 status_code=500,
#                 content={
#                     "code": 500,
#                     "msg": "连接 Java 系统超时"
#                 }
#             )

#         except requests.exceptions.ConnectionError as e:

#             print(
#                 f"❌ 无法连接 Java Gateway: {e}"
#             )

#             return JSONResponse(
#                 status_code=500,
#                 content={
#                     "code": 500,
#                     "msg": "无法连接 Java 系统"
#                 }
#             )

#         except Exception as e:

#             print(
#                 f"❌ 调用 Java 用户接口失败: {e}"
#             )

#             return JSONResponse(
#                 status_code=500,
#                 content={
#                     "code": 500,
#                     "msg": "调用 Java 用户接口失败"
#                 }
#             )

#         # ----------------------------------------------------
#         # Java Token 验证失败
#         # ----------------------------------------------------

#         if response.status_code != 200:

#             print(
#                 f"❌ Java Token 无效，HTTP "
#                 f"{response.status_code}"
#             )

#             return JSONResponse(
#                 status_code=401,
#                 content={
#                     "code": 401,
#                     "msg": "Java 登录已失效，请重新登录"
#                 }
#             )

#         # ----------------------------------------------------
#         # 解析 Java 返回
#         # ----------------------------------------------------

#         try:

#             result = response.json()

#         except ValueError:

#             print(
#                 "❌ Java 返回的数据不是 JSON"
#             )

#             return JSONResponse(
#                 status_code=500,
#                 content={
#                     "code": 500,
#                     "msg": "Java 返回数据格式错误"
#                 }
#             )

#         print(
#             f"📦 Java 用户信息: "
#             f"{result}"
#         )

#         # ----------------------------------------------------
#         # 判断 Java SaResult
#         # ----------------------------------------------------

#         if result.get("code") != 200:

#             print(
#                 f"❌ Java 登录验证失败: "
#                 f"{result.get('msg')}"
#             )

#             return JSONResponse(
#                 status_code=401,
#                 content={
#                     "code": 401,
#                     "msg": "Java 登录已失效，请重新登录"
#                 }
#             )

#         # ----------------------------------------------------
#         # 获取用户
#         # ----------------------------------------------------

#         user = result.get("data")

#         if not user:

#             print(
#                 "❌ Java 没有返回用户信息"
#             )

#             return JSONResponse(
#                 status_code=401,
#                 content={
#                     "code": 401,
#                     "msg": "Java 没有返回用户信息"
#                 }
#             )

#         # ----------------------------------------------------
#         # 转换成 Python 用户结构
#         # ----------------------------------------------------

#         current_user = {

#             "id":
#                 user.get("user_id"),

#             "user_id":
#                 user.get("user_id"),

#             "user_name":
#                 user.get("user_name"),

#             "user_code":
#                 user.get("user_code"),

#             "phone":
#                 user.get("phone"),

#             "duties_name":
#                 user.get("duties_name"),

#             "post_name":
#                 user.get("post_name"),

#             "subjection_id":
#                 user.get("subjection_id"),

#             "subjection_name":
#                 user.get("subjection_name"),

#             "register_dept_id":
#                 user.get("register_dept_id"),

#             "register_dept_name":
#                 user.get("register_dept_name"),

#             "mine_id":
#                 user.get("register_dept_id"),

#             "mine_name":
#                 user.get("register_dept_name"),

#             "_java_token":
#                 token
#         }

#         # ====================================================
#         # ⭐ 重点：进入 SSO 时强制清理旧 Python 登录状态
#         # ====================================================

#         print("----------------------------------------")
#         print("🧹 清理旧 Python Session")
#         print("----------------------------------------")

#         old_user = request.session.get("user")

#         if old_user:

#             print(
#                 f"⚠️ 发现旧 Python 用户："
#                 f"{old_user.get('user_name')}"
#             )

#         request.session.pop(
#             "user",
#             None
#         )

#         request.session.pop(
#             "user_id",
#             None
#         )

#         request.session.pop(
#             "user_name",
#             None
#         )

#         request.session.pop(
#             "java_token",
#             None
#         )

#         # ----------------------------------------------------
#         # 清掉之前暂存的 SSO 用户
#         # ----------------------------------------------------

#         request.session.pop(
#             "sso_user",
#             None
#         )

#         request.session.pop(
#             "sso_java_token",
#             None
#         )

#         # ----------------------------------------------------
#         # 保存本次 Java 登录用户
#         # ----------------------------------------------------

#         request.session["sso_user"] = current_user

#         request.session["sso_java_token"] = token

#         print("----------------------------------------")
#         print("🔥 Java 用户身份验证成功")

#         print(
#             f"用户 : "
#             f"{current_user.get('user_name')}"
#         )

#         print(
#             f"用户ID : "
#             f"{current_user.get('user_id')}"
#         )

#         print(
#             f"部门 : "
#             f"{current_user.get('subjection_name')}"
#         )

#         print("----------------------------------------")

#         print(
#             "🔥 已清理旧 Python 登录状态"
#         )

#         print(
#             "🔥 暂存新的 sso_user"
#         )

#         print(
#             "➡️ 跳转 Python 登录页"
#         )

#         print("========================================")

#         # ----------------------------------------------------
#         # 进入 Python 登录页
#         # ----------------------------------------------------

#         return RedirectResponse(
#             url="/login",
#             status_code=303
#         )

#     # ========================================================
#     # ② Python 登录页面 GET
#     # ========================================================

#     @app.get("/login")
#     async def login_page(
#         request: Request
#     ):

#         # ----------------------------------------------------
#         # 获取当前正式 Python 用户
#         # ----------------------------------------------------

#         user = request.session.get("user")

#         # ----------------------------------------------------
#         # 获取当前 Java SSO 用户
#         # ----------------------------------------------------

#         sso_user = request.session.get("sso_user")

#         # ====================================================
#         # ⭐ 重点：防止旧用户 Session 与新 Java 用户不一致
#         # ====================================================

#         if user:

#             if sso_user:

#                 old_user_id = user.get("user_id")
#                 new_user_id = sso_user.get("user_id")

#                 # --------------------------------------------
#                 # 用户相同
#                 # --------------------------------------------

#                 if (
#                     old_user_id
#                     and new_user_id
#                     and old_user_id == new_user_id
#                 ):

#                     print(
#                         f"✅ Python 已登录："
#                         f"{user.get('user_name')}"
#                     )

#                     return RedirectResponse(
#                         url="/",
#                         status_code=303
#                     )

#                 # --------------------------------------------
#                 # 用户不同
#                 # --------------------------------------------

#                 print("----------------------------------------")
#                 print("⚠️ 检测到 Java 用户发生变化")
#                 print(
#                     f"旧 Python 用户："
#                     f"{user.get('user_name')}"
#                 )
#                 print(
#                     f"新 Java 用户："
#                     f"{sso_user.get('user_name')}"
#                 )
#                 print("----------------------------------------")

#                 # 清掉旧 Python Session
#                 request.session.pop(
#                     "user",
#                     None
#                 )

#                 request.session.pop(
#                     "user_id",
#                     None
#                 )

#                 request.session.pop(
#                     "user_name",
#                     None
#                 )

#                 request.session.pop(
#                     "java_token",
#                     None
#                 )

#             else:

#                 # --------------------------------------------
#                 # 有 Python 用户，但是没有 SSO 用户
#                 #
#                 # 这里保留原逻辑：
#                 # Python 自己已经登录，可以继续使用
#                 # --------------------------------------------

#                 print(
#                     f"✅ Python 已正式登录："
#                     f"{user.get('user_name')}"
#                 )

#                 return RedirectResponse(
#                     url="/",
#                     status_code=303
#                 )

#         # ----------------------------------------------------
#         # Java SSO 已经验证成功
#         # ----------------------------------------------------

#         sso_user = request.session.get("sso_user")

#         if sso_user:

#             print(
#                 "✅ /login 获取到 sso_user："
#                 f"{sso_user.get('user_name')}"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user
#                 }
#             )

#         # ----------------------------------------------------
#         # 没有 Java SSO
#         # ----------------------------------------------------

#         print(
#             "❌ /login 没有 sso_user"
#         )

#         return templates.TemplateResponse(
#             "pages/login.html",
#             {
#                 "request": request,
#                 "sso_login": False,
#                 "error":
#                     "请先通过 Java 系统进入本系统"
#             }
#         )

#     # ========================================================
#     # ③ Python 登录 POST
#     # ========================================================

#     @app.post("/login")
#     async def login(
#         request: Request
#     ):

#         print("========================================")
#         print("🔐 Python 登录 POST")
#         print("========================================")

#         # ----------------------------------------------------
#         # 必须先有 Java SSO 用户
#         # ----------------------------------------------------

#         sso_user = request.session.get("sso_user")

#         if not sso_user:

#             print(
#                 "❌ 没有 sso_user"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": False,
#                     "error":
#                         "请先通过 Java 系统进入本系统"
#                 },
#                 status_code=401
#             )

#         # ----------------------------------------------------
#         # 获取表单
#         # ----------------------------------------------------

#         try:

#             form = await request.form()

#             password = str(
#                 form.get("password") or ""
#             ).strip()

#         except Exception as e:

#             print(
#                 f"❌ 获取登录参数失败: {e}"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "登录参数错误"
#                 },
#                 status_code=400
#             )

#         # ----------------------------------------------------
#         # 密码不能为空
#         # ----------------------------------------------------

#         if not password:

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "请输入密码"
#                 },
#                 status_code=400
#             )

#         # ----------------------------------------------------
#         # 获取用户ID
#         # ----------------------------------------------------

#         user_id = sso_user.get("user_id")

#         if not user_id:

#             print(
#                 "❌ sso_user 中没有 user_id"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "当前登录用户信息异常，请重新进入"
#                 },
#                 status_code=400
#             )

#         print(
#             f"👤 当前用户："
#             f"{sso_user.get('user_name')}"
#         )

#         print(
#             f"🆔 用户ID："
#             f"{user_id}"
#         )

#         # ----------------------------------------------------
#         # 调用 Java 验证密码
#         # ----------------------------------------------------

#         try:

#             java_token = (
#                 request.session.get(
#                     "sso_java_token"
#                 )
#             )

#             if not java_token:

#                 print(
#                     "❌ 当前没有 Java SSO Token"
#                 )

#                 return templates.TemplateResponse(
#                     "pages/login.html",
#                     {
#                         "request": request,
#                         "sso_login": True,
#                         "sso_user": sso_user,
#                         "error":
#                             "Java 登录已失效，请重新进入"
#                     },
#                     status_code=401
#                 )

#             response = requests.post(
#                 JAVA_VERIFY_PASSWORD_URL,
#                 headers={
#                     "satoken": java_token
#                 },
#                 json={
#                     "user_id":
#                         user_id,

#                     "phone":
#                         sso_user.get("phone"),

#                     "password":
#                         password
#                 },
#                 timeout=10
#             )

#             print(
#                 f"📡 Java 密码验证 HTTP："
#                 f"{response.status_code}"
#             )

#             print(
#                 f"📦 Java 密码验证返回："
#                 f"{response.text}"
#             )

#         except requests.exceptions.Timeout:

#             print(
#                 "❌ Java 密码验证超时"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "连接 Java 系统超时"
#                 },
#                 status_code=500
#             )

#         except requests.exceptions.ConnectionError as e:

#             print(
#                 f"❌ 无法连接 Java：{e}"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "无法连接 Java 系统"
#                 },
#                 status_code=500
#             )

#         except Exception as e:

#             print(
#                 f"❌ 密码验证异常：{e}"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "密码验证失败"
#                 },
#                 status_code=500
#             )

#         # ----------------------------------------------------
#         # Java HTTP 非 200
#         # ----------------------------------------------------

#         if response.status_code != 200:

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "密码验证失败"
#                 },
#                 status_code=401
#             )

#         # ----------------------------------------------------
#         # 解析 Java 返回
#         # ----------------------------------------------------

#         try:

#             result = response.json()

#         except ValueError:

#             print(
#                 "❌ Java 返回数据不是 JSON"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         "Java 返回数据格式错误"
#                 },
#                 status_code=500
#             )

#         # ----------------------------------------------------
#         # 密码错误
#         # ----------------------------------------------------

#         if result.get("code") != 200:

#             print(
#                 f"❌ 密码验证失败："
#                 f"{result.get('msg')}"
#             )

#             return templates.TemplateResponse(
#                 "pages/login.html",
#                 {
#                     "request": request,
#                     "sso_login": True,
#                     "sso_user": sso_user,
#                     "error":
#                         result.get(
#                             "msg",
#                             "账户或密码错误"
#                         )
#                 },
#                 status_code=401
#             )

#         # ----------------------------------------------------
#         # 密码正确
#         # ----------------------------------------------------

#         print(
#             "✅ Java 密码验证成功"
#         )

#         print(
#             "✅ 建立 Python 正式 Session"
#         )

#         request.session["user"] = sso_user

#         request.session["user_id"] = (
#             sso_user.get("user_id")
#         )

#         request.session["user_name"] = (
#             sso_user.get("user_name")
#         )

#         # ----------------------------------------------------
#         # 暂存 Java Token
#         # ----------------------------------------------------

#         request.session["java_token"] = (
#             request.session.get(
#                 "sso_java_token"
#             )
#         )

#         # ----------------------------------------------------
#         # 删除临时 SSO Session
#         # ----------------------------------------------------

#         request.session.pop(
#             "sso_user",
#             None
#         )

#         request.session.pop(
#             "sso_java_token",
#             None
#         )

#         print("========================================")

#         print(
#             "🎉 Python 登录成功"
#         )

#         print(
#             f"👤 用户："
#             f"{sso_user.get('user_name')}"
#         )

#         print(
#             "➡️ 进入 Python 首页"
#         )

#         print("========================================")

#         return RedirectResponse(
#             url="/",
#             status_code=303
#         )

#     # ========================================================
#     # ④ Python 退出
#     # ========================================================

#     @app.get("/logout")
#     async def logout(
#         request: Request
#     ):

#         print("========================================")
#         print("👋 Python 退出登录")
#         print("========================================")

#         try:

#             request.session.clear()

#         except Exception as e:

#             print(
#                 f"⚠️ 清理 Python Session 失败: {e}"
#             )

#         # ----------------------------------------------------
#         # 重新进入 Java SSO
#         # ----------------------------------------------------

#         JAVA_SSO_URL = (
#             f"{JAVA_BASE_URL}/python/sso"
#         )

#         print(
#             f"➡️ 重新进入 Java SSO: "
#             f"{JAVA_SSO_URL}"
#         )

#         return RedirectResponse(
#             url=JAVA_SSO_URL,
#             status_code=303
#         )

#     # ========================================================
#     # ⑤ 登录状态检查
#     # ========================================================

#     @app.get("/api/auth/check")
#     async def check_auth(
#         request: Request
#     ):

#         session_user = (
#             request.session.get("user")
#         )

#         if session_user:

#             return {
#                 "success": True,

#                 "data": {

#                     "is_login": True,

#                     "user_id":
#                         session_user.get(
#                             "user_id"
#                         ),

#                     "username": (
#                         session_user.get(
#                             "user_name"
#                         )
#                         or session_user.get(
#                             "user_code"
#                         )
#                         or ""
#                     ),

#                     "phone":
#                         session_user.get(
#                             "phone"
#                         ),

#                     "role": (
#                         session_user.get(
#                             "duties_name"
#                         )
#                         or session_user.get(
#                             "post_name"
#                         )
#                         or "普通用户"
#                     )
#                 }
#             }

#         # ----------------------------------------------------
#         # 没有 Python Session
#         #
#         # 注意：
#         # 这里不能自动通过 Java Token 登录
#         # 必须点击 Python 登录按钮
#         # ----------------------------------------------------

#         return {

#             "success": False,

#             "data": {

#                 "is_login": False
#             },

#             "message":
#                 "未登录，请先登录"
#         }

#     # ========================================================
#     # ⑥ 获取当前用户信息
#     # ========================================================

#     @app.get("/api/user/info")
#     async def get_user_info(
#         request: Request
#     ):

#         # ----------------------------------------------------
#         # 只使用 Python 正式 Session
#         # ----------------------------------------------------

#         user = request.session.get("user")

#         if not user:

#             print(
#                 "❌ 当前没有登录用户"
#             )

#             return JSONResponse(
#                 status_code=401,
#                 content={
#                     "success": False,
#                     "message":
#                         "未登录或 Java 登录已失效"
#                 }
#             )

#         # ----------------------------------------------------
#         # Python 前端真正需要的数据
#         # ----------------------------------------------------

#         user_info = {

#             "user_id":
#                 user.get("user_id"),

#             "user_name":
#                 user.get("user_name"),

#             "subjection_id":
#                 user.get("subjection_id"),

#             "subjection_name":
#                 user.get("subjection_name"),

#             "mine_id":
#                 user.get("register_dept_id"),

#             "mine_name":
#                 user.get("register_dept_name")
#         }

#         # ----------------------------------------------------
#         # 打印
#         # ----------------------------------------------------

#         print("========================================")
#         print("       当前登录用户信息")
#         print("========================================")

#         print(
#             f"用户ID   : "
#             f"{user_info['user_id']}"
#         )

#         print(
#             f"登录人   : "
#             f"{user_info['user_name']}"
#         )

#         print(
#             f"部门ID   : "
#             f"{user_info['subjection_id']}"
#         )

#         print(
#             f"部门     : "
#             f"{user_info['subjection_name']}"
#         )

#         print(
#             f"矿井ID   : "
#             f"{user_info['mine_id']}"
#         )

#         print(
#             f"矿井     : "
#             f"{user_info['mine_name']}"
#         )

#         print("========================================")

#         return {

#             "success": True,

#             "data": user_info
#         }

#     # ========================================================
#     # 认证路由注册完成
#     # ========================================================

#     print(
#         "✅ 认证路由注册完成"
#     )




# -*- coding: utf-8 -*-
"""
auth.py - Python 独立多账号认证模块

生产架构：
    多个 Python 本地账号
        ↓
    users.json（只保存 PBKDF2-SHA256 密码哈希）
        ↓
    登录失败 / IP 限流
        ↓
    Python Session
        ↓
    进入系统

特点：
1. 不依赖 Java 登录、Java Token、Sa-Token 或 SSO。
2. 不连接 MySQL。
3. 支持多个账号。
4. users.json 不保存明文密码，只保存 PBKDF2-SHA256 哈希。
5. 每个账号可独立启用/禁用。
6. 登录失败次数、单 IP 限流、全局失败限制。
7. Session 只保存最少必要身份信息。
8. users.json 不应放在 static/ 或任何可被 Nginx 直接访问的目录。

账号文件默认：
    项目目录/data/users.json

首次创建账号：
    python create_user.py admin

建议生产环境：
    Nginx HTTPS + login 限流 + Python 应用层限流
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional

from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse


# ============================================================
# 基础路径
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"


# ============================================================
# 密码配置
# ============================================================

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = int(
    os.getenv("PYTHON_PASSWORD_PBKDF2_ITERATIONS", "600000")
)

# 最低密码长度
MIN_PASSWORD_LENGTH = 12


# ============================================================
# 登录安全配置
# ============================================================

# 同一个 IP 连续失败多少次后锁定
MAX_LOGIN_FAILS = int(
    os.getenv("PYTHON_LOGIN_MAX_FAILS", "5")
)

# IP 锁定时间，默认 15 分钟
LOGIN_LOCK_SECONDS = int(
    os.getenv("PYTHON_LOGIN_LOCK_SECONDS", "900")
)

# 单 IP 时间窗口
LOGIN_RATE_WINDOW = int(
    os.getenv("PYTHON_LOGIN_RATE_WINDOW", "300")
)

# 单 IP 时间窗口最多尝试次数
LOGIN_RATE_MAX_ATTEMPTS = int(
    os.getenv("PYTHON_LOGIN_RATE_MAX_ATTEMPTS", "10")
)

# 全局失败保护
GLOBAL_MAX_FAILS = int(
    os.getenv("PYTHON_LOGIN_GLOBAL_MAX_FAILS", "30")
)

GLOBAL_WINDOW = int(
    os.getenv("PYTHON_LOGIN_GLOBAL_WINDOW", "600")
)

GLOBAL_LOCK_SECONDS = int(
    os.getenv("PYTHON_LOGIN_GLOBAL_LOCK_SECONDS", "900")
)


# ============================================================
# 进程内登录状态
# ============================================================

_login_failures = defaultdict(int)
_login_locked_until = {}
_login_attempt_times = defaultdict(deque)

_global_failure_times = deque()
_global_locked_until = 0.0


# ============================================================
# 用户文件
# ============================================================

def _ensure_users_file():
    """
    确保 data/users.json 存在。

    注意：
    不自动创建默认账号密码，避免出现弱默认账户。
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        USERS_FILE.write_text(
            "[]\n",
            encoding="utf-8"
        )

        try:
            os.chmod(USERS_FILE, 0o600)
        except Exception:
            # Windows 下 chmod 权限语义有限，忽略即可
            pass


def _load_users() -> list:
    """
    读取全部账号。
    """
    _ensure_users_file()

    try:
        text = USERS_FILE.read_text(
            encoding="utf-8"
        )

        data = json.loads(text)

        if not isinstance(data, list):
            raise RuntimeError(
                "data/users.json 格式错误，根节点必须是数组"
            )

        result = []

        for item in data:
            if isinstance(item, dict):
                result.append(item)

        return result

    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"data/users.json JSON 格式错误：{e}"
        )


def _save_users(users: list):
    """
    原子方式保存 users.json。
    避免程序写文件过程中异常导致文件损坏。
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix="users_",
        suffix=".tmp",
        dir=str(DATA_DIR)
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                users,
                f,
                ensure_ascii=False,
                indent=2
            )
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        os.replace(
            temp_name,
            USERS_FILE
        )

        try:
            os.chmod(USERS_FILE, 0o600)
        except Exception:
            pass

    finally:
        if os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except Exception:
                pass


def _find_user(username: str) -> Optional[dict]:
    """
    根据用户名查找启用账号。
    用户名区分大小写。
    """
    users = _load_users()

    for user in users:
        stored_username = str(
            user.get("username") or ""
        ).strip()

        if hmac.compare_digest(
            username,
            stored_username
        ):
            return user

    return None


# ============================================================
# 密码哈希
# ============================================================

def make_password_hash(password: str) -> str:
    """
    生成 PBKDF2-SHA256 密码哈希。

    返回：
        pbkdf2_sha256$iterations$salt$hash
    """
    if not isinstance(password, str):
        raise ValueError("password 必须是字符串")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"生产环境密码至少 {MIN_PASSWORD_LENGTH} 位"
        )

    salt = secrets.token_hex(16)

    derived_key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
        dklen=32
    )

    encoded = base64.urlsafe_b64encode(
        derived_key
    ).decode("ascii").rstrip("=")

    return (
        f"pbkdf2_sha256$"
        f"{PBKDF2_ITERATIONS}$"
        f"{salt}$"
        f"{encoded}"
    )


def verify_password(
    password: str,
    stored_hash: str
) -> bool:
    """
    验证密码。
    """
    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split("$")

        if len(parts) != 4:
            return False

        algorithm, iterations_text, salt, expected = parts

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)

        # 防止异常配置造成非常规计算
        if iterations < 100000 or iterations > 5000000:
            return False

        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
            dklen=32
        )

        actual = base64.urlsafe_b64encode(
            derived_key
        ).decode("ascii").rstrip("=")

        return hmac.compare_digest(
            actual,
            expected
        )

    except Exception:
        return False


# ============================================================
# 用户配置检查
# ============================================================

def _validate_users_config():
    """
    启动/第一次登录时检查账号文件。
    """
    users = _load_users()

    if not users:
        raise RuntimeError(
            "尚未创建系统账号，请先运行：python create_user.py admin"
        )

    usernames = set()

    for user in users:
        username = str(
            user.get("username") or ""
        ).strip()

        password_hash = str(
            user.get("password_hash") or ""
        ).strip()

        if not username:
            raise RuntimeError(
                "users.json 存在空用户名"
            )

        if username in usernames:
            raise RuntimeError(
                f"users.json 存在重复用户名：{username}"
            )

        usernames.add(username)

        if len(username) < 2:
            raise RuntimeError(
                f"用户名无效：{username}"
            )

        if not password_hash.startswith(
            "pbkdf2_sha256$"
        ):
            raise RuntimeError(
                f"账号 {username} 的密码哈希格式无效"
            )


# ============================================================
# IP 获取
# ============================================================

def get_client_ip(request: Request) -> str:
    """
    获取客户端 IP。

    正式环境建议：
    Nginx 只向后端传递可信的 X-Real-IP。
    """
    real_ip = request.headers.get("X-Real-IP")

    if real_ip:
        real_ip = real_ip.strip()

        if real_ip:
            return real_ip[:64]

    forwarded = request.headers.get(
        "X-Forwarded-For"
    )

    if forwarded:
        first_ip = forwarded.split(",")[0].strip()

        if first_ip:
            return first_ip[:64]

    if request.client:
        return request.client.host[:64]

    return "unknown"


# ============================================================
# 时间清理
# ============================================================

def _cleanup_ip_attempts(ip: str, now: float):
    queue = _login_attempt_times[ip]

    while queue and (
        now - queue[0] > LOGIN_RATE_WINDOW
    ):
        queue.popleft()


def _cleanup_global_failures(now: float):
    while _global_failure_times and (
        now - _global_failure_times[0] > GLOBAL_WINDOW
    ):
        _global_failure_times.popleft()


# ============================================================
# 检查是否允许登录
# ============================================================

def _check_login_allowed(ip: str):
    global _global_locked_until

    now = time.time()

    # 全局锁定
    if now < _global_locked_until:
        return False, (
            "登录尝试过于频繁，请稍后再试"
        )

    # IP 锁定
    locked_until = _login_locked_until.get(ip, 0)

    if now < locked_until:
        remaining = int(
            locked_until - now
        )

        minutes = max(
            1,
            (remaining + 59) // 60
        )

        return False, (
            f"登录失败次数过多，请 {minutes} 分钟后再试"
        )

    # IP 频率限制
    _cleanup_ip_attempts(ip, now)

    queue = _login_attempt_times[ip]

    if len(queue) >= LOGIN_RATE_MAX_ATTEMPTS:
        return False, (
            "登录尝试过于频繁，请稍后再试"
        )

    queue.append(now)

    return True, None


# ============================================================
# 登录失败处理
# ============================================================

def _record_login_failure(ip: str):
    global _global_locked_until

    now = time.time()

    _login_failures[ip] += 1

    # IP 达到失败阈值
    if _login_failures[ip] >= MAX_LOGIN_FAILS:
        _login_locked_until[ip] = (
            now + LOGIN_LOCK_SECONDS
        )

        _login_failures[ip] = 0

    # 全局失败计数
    _cleanup_global_failures(now)

    _global_failure_times.append(now)

    if len(_global_failure_times) >= GLOBAL_MAX_FAILS:
        _global_locked_until = (
            now + GLOBAL_LOCK_SECONDS
        )

        _global_failure_times.clear()


# ============================================================
# 登录成功处理
# ============================================================

def _record_login_success(ip: str):
    _login_failures.pop(ip, None)
    _login_locked_until.pop(ip, None)
    _login_attempt_times.pop(ip, None)

    # 成功登录后不清空全局失败记录。
    # 这样可以避免攻击者用成功登录人为降低全局防护计数。


# ============================================================
# 当前用户
# ============================================================

async def get_current_user(request: Request):
    """
    只信任 Python Session。

    不读取：
    - satoken
    - Authorization
    - token
    - Java 用户信息
    - SSO
    """
    user = request.session.get("user")

    if not isinstance(user, dict):
        return None

    if user.get("auth_type") != "python_local":
        return None

    user_id = str(
        user.get("user_id") or ""
    )

    username = str(
        user.get("user_name") or ""
    )

    if not user_id or not username:
        return None

    # Session 中的用户必须仍然存在于 users.json
    # 且账号必须处于启用状态。
    stored_user = _find_user(username)

    if not stored_user:
        return None

    if stored_user.get("enabled", True) is not True:
        return None

    if stored_user.get("user_id") != user_id:
        return None

    return user


# ============================================================
# 必须登录
# ============================================================

async def require_login(
    user: dict = Depends(get_current_user)
):
    if not user:
        raise HTTPException(
            status_code=401,
            detail="未登录，请先登录"
        )

    return user


# ============================================================
# 页面登录检查
# ============================================================

async def require_login_redirect(
    request: Request,
    user: dict = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return user


# ============================================================
# 页面模板
# ============================================================

_templates = None


def set_templates(templates):
    global _templates
    _templates = templates


async def render_page(
    request: Request,
    template_name: str,
    extra_data: dict = None
):
    """
    统一页面渲染。
    """
    user = await get_current_user(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    data = {
        "request": request,
        "username": user.get("user_name") or "",
        "role": user.get("role") or "普通用户",
        "user": user
    }

    if extra_data:
        data.update(extra_data)

    if _templates is None:
        raise RuntimeError(
            "认证模块模板尚未初始化"
        )

    return _templates.TemplateResponse(
        template_name,
        data
    )


# ============================================================
# 认证路由
# ============================================================

def setup_auth_routes(app, templates):
    set_templates(templates)

    # ========================================================
    # ① 登录页面
    # ========================================================

    @app.get("/login")
    async def login_page(request: Request):
        user = await get_current_user(request)

        if user:
            return RedirectResponse(
                url="/",
                status_code=303
            )

        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "sso_login": False,
                "sso_user": None,
                "error": None
            }
        )

    # ========================================================
    # ② 登录
    # ========================================================

    @app.post("/login")
    async def login(request: Request):
        try:
            _validate_users_config()

        except RuntimeError as e:
            print(f"❌ 认证配置错误：{e}")

            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "服务器认证配置错误"
                }
            )

        ip = get_client_ip(request)

        allowed, message = _check_login_allowed(ip)

        if not allowed:
            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": False,
                    "sso_user": None,
                    "error": message
                },
                status_code=429
            )

        # ----------------------------------------------------
        # 获取表单
        # ----------------------------------------------------

        try:
            form = await request.form()

            username = str(
                form.get("username") or ""
            ).strip()

            password = str(
                form.get("password") or ""
            )

        except Exception as e:
            print(
                f"❌ 获取登录参数失败：{e}"
            )

            _record_login_failure(ip)

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": False,
                    "sso_user": None,
                    "error": "登录参数错误"
                },
                status_code=400
            )

        # ----------------------------------------------------
        # 查找账号
        # ----------------------------------------------------

        stored_user = _find_user(username)

        # 不区分“账号不存在”和“密码错误”
        if not stored_user:
            # 使用固定字符串做一次哈希计算，
            # 尽量减少账号枚举导致的明显时间差。
            verify_password(
                password,
                "pbkdf2_sha256$600000$dummy$dummy"
            )

            _record_login_failure(ip)

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": False,
                    "sso_user": None,
                    "error": "账号或密码错误"
                },
                status_code=401
            )

        # ----------------------------------------------------
        # 检查账号状态
        # ----------------------------------------------------

        if stored_user.get("enabled", True) is not True:
            _record_login_failure(ip)

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": False,
                    "sso_user": None,
                    "error": "账号或密码错误"
                },
                status_code=401
            )

        # ----------------------------------------------------
        # 密码校验
        # ----------------------------------------------------

        valid_password = verify_password(
            password,
            str(
                stored_user.get("password_hash") or ""
            )
        )

        if not valid_password:
            _record_login_failure(ip)

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": False,
                    "sso_user": None,
                    "error": "账号或密码错误"
                },
                status_code=401
            )

        # ----------------------------------------------------
        # 登录成功
        # ----------------------------------------------------

        _record_login_success(ip)

        # 清理旧 Session，防止旧身份残留
        request.session.clear()

        user_id = str(
            stored_user.get("user_id")
            or secrets.token_hex(16)
        )

        role = str(
            stored_user.get("role")
            or "普通用户"
        )

        request.session["user"] = {
            "id": user_id,
            "user_id": user_id,
            "user_name": username,
            "user_code": str(
                stored_user.get("user_code")
                or username
            ),
            "phone": stored_user.get("phone"),
            "duties_name": stored_user.get(
                "duties_name"
            ),
            "post_name": stored_user.get(
                "post_name"
            ),
            "subjection_id": stored_user.get(
                "subjection_id"
            ),
            "subjection_name": stored_user.get(
                "subjection_name"
            ),
            "register_dept_id": stored_user.get(
                "register_dept_id"
            ),
            "register_dept_name": stored_user.get(
                "register_dept_name"
            ),
            "mine_id": stored_user.get(
                "mine_id"
            ),
            "mine_name": stored_user.get(
                "mine_name"
            ),
            "role": role,
            "auth_type": "python_local"
        }

        request.session["user_id"] = user_id
        request.session["user_name"] = username

        print("========================================")
        print("🎉 Python 独立登录成功")
        print(f"👤 用户：{username}")
        print(f"🔐 角色：{role}")
        print(f"🌐 IP：{ip}")
        print("========================================")

        return RedirectResponse(
            url="/",
            status_code=303
        )

    # ========================================================
    # ③ 退出
    # ========================================================

    @app.get("/logout")
    async def logout(request: Request):
        try:
            request.session.clear()

        except Exception as e:
            print(
                f"⚠️ 清理 Session 失败：{e}"
            )

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # ========================================================
    # ④ 登录状态检查
    # ========================================================

    @app.get("/api/auth/check")
    async def check_auth(request: Request):
        session_user = await get_current_user(
            request
        )

        if session_user:
            return {
                "success": True,
                "data": {
                    "is_login": True,
                    "user_id": session_user.get(
                        "user_id"
                    ),
                    "username": session_user.get(
                        "user_name"
                    ),
                    "phone": session_user.get(
                        "phone"
                    ),
                    "role": session_user.get(
                        "role"
                    )
                }
            }

        return {
            "success": False,
            "data": {
                "is_login": False
            },
            "message": "未登录，请先登录"
        }

    # ========================================================
    # ⑤ 当前用户信息
    # ========================================================

    @app.get("/api/user/info")
    async def get_user_info(
        request: Request
    ):
        user = await get_current_user(request)

        if not user:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "未登录，请先登录"
                }
            )

        user_info = {
            "user_id": user.get("user_id"),
            "user_name": user.get("user_name"),
            "user_code": user.get("user_code"),
            "phone": user.get("phone"),
            "duties_name": user.get(
                "duties_name"
            ),
            "post_name": user.get(
                "post_name"
            ),
            "subjection_id": user.get(
                "subjection_id"
            ),
            "subjection_name": user.get(
                "subjection_name"
            ),
            "mine_id": user.get("mine_id"),
            "mine_name": user.get(
                "mine_name"
            ),
            "role": user.get(
                "role"
            )
        }

        return {
            "success": True,
            "data": user_info
        }

    print("✅ Python 独立多账号认证路由注册完成")
