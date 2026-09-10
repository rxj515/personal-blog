# auth.py - 认证模块
#
# 当前架构：
# Java 负责登录、密码验证、Sa-Token
# Python 不再直接连接 MySQL
# Python 不再验证用户名和密码
#
# 登录流程：
#
# Java 登录
#     ↓
# Java Token
#     ↓
# 点击菜单进入 Python
#     ↓
# Python /sso/login?token=xxx
#     ↓
# Java /python/user-info 验证 Token
#     ↓
# Python 清理旧 Session
#     ↓
# Python 暂存 sso_user
#     ↓
# Python /login 登录页
#     ↓
# 用户输入密码点击【登录】
#     ↓
# Python 调用 Java /python/verify-password
#     ↓
# Java 验证密码
#     ↓
# 验证成功
#     ↓
# Python 正式 Session
#     ↓
# Python 首页


import os
import requests

from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse


# ============================================================
# Java 服务配置
# ============================================================

JAVA_BASE_URL = os.getenv(
    "JAVA_BASE_URL",
    "http://localhost:1100"
)

JAVA_USER_INFO_URL = (
    f"{JAVA_BASE_URL}/python/user-info"
)

JAVA_VERIFY_PASSWORD_URL = (
    f"{JAVA_BASE_URL}/python/verify-password"
)


# ============================================================
# 从请求中获取 Java Sa-Token
# ============================================================

def get_java_token(request: Request):
    """
    从请求 Header 中获取 Java 登录 Token。

    当前兼容：
    1. Authorization: token
    2. Authorization: Bearer token
    3. satoken: token
    4. token: token

    Java 实际验证使用 satoken。
    """

    # --------------------------------------------------------
    # 1. Authorization
    # --------------------------------------------------------

    authorization = request.headers.get("Authorization")

    if authorization:
        authorization = authorization.strip()

        if authorization.lower().startswith("bearer "):
            return authorization[7:].strip()

        return authorization

    # --------------------------------------------------------
    # 2. satoken
    # --------------------------------------------------------

    token = request.headers.get("satoken")

    if token:
        return token.strip().strip('"')

    # --------------------------------------------------------
    # 3. token
    # --------------------------------------------------------

    token = request.headers.get("token")

    if token:
        return token.strip().strip('"')

    return None


# ============================================================
# 调用 Java 获取当前登录用户
# ============================================================

async def get_current_user(request: Request):

    # --------------------------------------------------------
    # ① 优先从 Python Session 获取用户
    # --------------------------------------------------------
    session_user = request.session.get("user")

    if session_user:
        print(
            f"✅ 从 Python Session 获取当前用户: "
            f"{session_user.get('user_name')}"
        )
        return session_user

    # --------------------------------------------------------
    # ② Session 没有，再从请求 Header 获取 Java Token
    # --------------------------------------------------------

    token = get_java_token(request)

    if not token:
        print("❌ 当前请求没有 Java Token")
        return None

    # 防止 localStorage 序列化后出现：
    # "LGITBgKtCl2..."
    token = token.strip().strip('"')

    # --------------------------------------------------------
    # ③ 调用 Java
    # --------------------------------------------------------

    try:

        print("========================================")
        print("       获取 Java 当前登录用户")
        print("========================================")

        print(
            f"🔗 Java 用户接口: "
            f"{JAVA_USER_INFO_URL}"
        )

        response = requests.get(
            JAVA_USER_INFO_URL,
            headers={
                "satoken": token
            },
            timeout=10
        )

        print(
            f"📡 Java HTTP状态: "
            f"{response.status_code}"
        )

        # ----------------------------------------------------
        # HTTP状态检查
        # ----------------------------------------------------

        if response.status_code != 200:

            print(
                f"❌ Java 用户接口返回 HTTP "
                f"{response.status_code}"
            )

            print(
                f"返回内容: "
                f"{response.text[:500]}"
            )

            return None

        # ----------------------------------------------------
        # JSON解析
        # ----------------------------------------------------

        result = response.json()

        print(
            f"📦 Java 用户接口返回: "
            f"{result}"
        )

        # ----------------------------------------------------
        # SaResult 判断
        # ----------------------------------------------------

        if result.get("code") != 200:

            print(
                f"❌ Java 用户验证失败: "
                f"{result.get('msg')}"
            )

            return None

        # ----------------------------------------------------
        # 获取用户数据
        # ----------------------------------------------------

        user = result.get("data")

        if not user:

            print(
                "❌ Java 没有返回用户信息"
            )

            return None

        # ----------------------------------------------------
        # 转换成 Python 项目原来的用户结构
        # ----------------------------------------------------

        current_user = {

            # 用户ID
            "id": user.get("user_id"),
            "user_id": user.get("user_id"),

            # 用户名
            "user_name": user.get("user_name"),

            # 用户编码
            "user_code": user.get("user_code"),

            # 手机号
            "phone": user.get("phone"),

            # 职务
            "duties_name": user.get("duties_name"),

            # 岗位
            "post_name": user.get("post_name"),

            # 所属部门
            "subjection_id": user.get("subjection_id"),
            "subjection_name": user.get("subjection_name"),

            # 注册矿井 / 部门
            "register_dept_id": user.get("register_dept_id"),
            "register_dept_name": user.get("register_dept_name"),

            # 兼容原 Python 项目
            "mine_id": user.get("register_dept_id"),
            "mine_name": user.get("register_dept_name"),

            # 保存 Java Token
            "_java_token": token
        }

        # ----------------------------------------------------
        # 打印用户
        # ----------------------------------------------------

        print("----------------------------------------")

        print(
            f"用户ID   : "
            f"{current_user.get('user_id')}"
        )

        print(
            f"登录人   : "
            f"{current_user.get('user_name')}"
        )

        print(
            f"部门ID   : "
            f"{current_user.get('subjection_id')}"
        )

        print(
            f"部门     : "
            f"{current_user.get('subjection_name')}"
        )

        print(
            f"矿井ID   : "
            f"{current_user.get('register_dept_id')}"
        )

        print(
            f"矿井     : "
            f"{current_user.get('register_dept_name')}"
        )

        print("----------------------------------------")

        print(
            "✅ Java 当前登录用户获取成功"
        )

        print("========================================")

        return current_user

    # --------------------------------------------------------
    # 网络异常
    # --------------------------------------------------------

    except requests.exceptions.Timeout:

        print(
            "❌ 调用 Java 用户接口超时"
        )

        return None

    except requests.exceptions.ConnectionError as e:

        print(
            f"❌ 无法连接 Java Gateway: {e}"
        )

        return None

    except requests.exceptions.RequestException as e:

        print(
            f"❌ 调用 Java 用户接口失败: {e}"
        )

        return None

    # --------------------------------------------------------
    # JSON / 其它异常
    # --------------------------------------------------------

    except ValueError as e:

        print(
            f"❌ Java 返回的数据不是合法 JSON: {e}"
        )

        return None

    except Exception as e:

        print(
            f"❌ 获取 Java 当前用户失败: {e}"
        )

        import traceback
        traceback.print_exc()

        return None


# ============================================================
# 依赖注入：必须登录
# ============================================================

async def require_login(
    user: dict = Depends(get_current_user)
):

    if not user:

        raise HTTPException(
            status_code=401,
            detail="未登录或 Java 登录已失效"
        )

    return user


# ============================================================
# 依赖注入：页面登录检查
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
# 页面渲染封装
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

    # --------------------------------------------------------
    # 检查 Python 正式登录状态
    # --------------------------------------------------------

    user = await get_current_user(request)

    if not user:

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # --------------------------------------------------------
    # 模板数据
    # --------------------------------------------------------

    data = {
        "request": request
    }

    # --------------------------------------------------------
    # 用户名
    # --------------------------------------------------------

    data["username"] = (
        user.get("user_name")
        or user.get("user_code")
        or user.get("phone")
        or ""
    )

    # --------------------------------------------------------
    # 角色
    # --------------------------------------------------------

    data["role"] = (
        user.get("duties_name")
        or user.get("post_name")
        or "普通用户"
    )

    # --------------------------------------------------------
    # 完整用户
    # --------------------------------------------------------

    data["user"] = user

    # --------------------------------------------------------
    # 额外数据
    # --------------------------------------------------------

    if extra_data:
        data.update(extra_data)

    # --------------------------------------------------------
    # 模板
    # --------------------------------------------------------

    return _templates.TemplateResponse(
        template_name,
        data
    )


# ============================================================
# 设置认证路由
# ============================================================

def setup_auth_routes(app, templates):

    set_templates(templates)

    # ========================================================
    # ① Java → Python SSO
    # ========================================================

    @app.get("/sso/login")
    async def sso_login(
        request: Request
    ):

        print("========================================")
        print("🔗 进入 Python /sso/login")
        print("========================================")

        token = request.query_params.get("token")

        print(
            "是否获取到 token：",
            bool(token)
        )

        if token:
            print(
                "token 长度：",
                len(token)
            )

        print(
            "🔥 当前URL:",
            str(request.url)
        )

        # ----------------------------------------------------
        # 获取 Java Token
        # ----------------------------------------------------

        token = request.query_params.get("token")

        print(
            "🔥 URL Token:",
            bool(token)
        )

        # ----------------------------------------------------
        # 如果 URL 没有 Token
        # 再尝试 Header
        # ----------------------------------------------------

        if not token:
            token = get_java_token(request)

        # ----------------------------------------------------
        # Token 不存在
        # ----------------------------------------------------

        if not token:

            print(
                "❌ SSO 没有获取到 Java Token"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "msg": "没有获取到 Java 登录 Token"
                }
            )

        # ----------------------------------------------------
        # 清理 Token
        # ----------------------------------------------------

        token = token.strip().strip('"')

        print(
            f"🔑 收到 Java Token: "
            f"{token[:10]}..."
        )

        # ----------------------------------------------------
        # 调用 Java 获取用户
        # ----------------------------------------------------

        try:

            response = requests.get(
                JAVA_USER_INFO_URL,
                headers={
                    "satoken": token
                },
                timeout=10
            )

            print(
                f"📡 Java HTTP状态: "
                f"{response.status_code}"
            )

            print(
                f"📦 Java返回内容: "
                f"{response.text[:1000]}"
            )

        except requests.exceptions.Timeout:

            print(
                "❌ Java 用户接口超时"
            )

            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "msg": "连接 Java 系统超时"
                }
            )

        except requests.exceptions.ConnectionError as e:

            print(
                f"❌ 无法连接 Java Gateway: {e}"
            )

            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "msg": "无法连接 Java 系统"
                }
            )

        except Exception as e:

            print(
                f"❌ 调用 Java 用户接口失败: {e}"
            )

            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "msg": "调用 Java 用户接口失败"
                }
            )

        # ----------------------------------------------------
        # Java Token 验证失败
        # ----------------------------------------------------

        if response.status_code != 200:

            print(
                f"❌ Java Token 无效，HTTP "
                f"{response.status_code}"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "msg": "Java 登录已失效，请重新登录"
                }
            )

        # ----------------------------------------------------
        # 解析 Java 返回
        # ----------------------------------------------------

        try:

            result = response.json()

        except ValueError:

            print(
                "❌ Java 返回的数据不是 JSON"
            )

            return JSONResponse(
                status_code=500,
                content={
                    "code": 500,
                    "msg": "Java 返回数据格式错误"
                }
            )

        print(
            f"📦 Java 用户信息: "
            f"{result}"
        )

        # ----------------------------------------------------
        # 判断 Java SaResult
        # ----------------------------------------------------

        if result.get("code") != 200:

            print(
                f"❌ Java 登录验证失败: "
                f"{result.get('msg')}"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "msg": "Java 登录已失效，请重新登录"
                }
            )

        # ----------------------------------------------------
        # 获取用户
        # ----------------------------------------------------

        user = result.get("data")

        if not user:

            print(
                "❌ Java 没有返回用户信息"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "code": 401,
                    "msg": "Java 没有返回用户信息"
                }
            )

        # ----------------------------------------------------
        # 转换成 Python 用户结构
        # ----------------------------------------------------

        current_user = {

            "id":
                user.get("user_id"),

            "user_id":
                user.get("user_id"),

            "user_name":
                user.get("user_name"),

            "user_code":
                user.get("user_code"),

            "phone":
                user.get("phone"),

            "duties_name":
                user.get("duties_name"),

            "post_name":
                user.get("post_name"),

            "subjection_id":
                user.get("subjection_id"),

            "subjection_name":
                user.get("subjection_name"),

            "register_dept_id":
                user.get("register_dept_id"),

            "register_dept_name":
                user.get("register_dept_name"),

            "mine_id":
                user.get("register_dept_id"),

            "mine_name":
                user.get("register_dept_name"),

            "_java_token":
                token
        }

        # ====================================================
        # ⭐ 重点：进入 SSO 时强制清理旧 Python 登录状态
        # ====================================================

        print("----------------------------------------")
        print("🧹 清理旧 Python Session")
        print("----------------------------------------")

        old_user = request.session.get("user")

        if old_user:

            print(
                f"⚠️ 发现旧 Python 用户："
                f"{old_user.get('user_name')}"
            )

        request.session.pop(
            "user",
            None
        )

        request.session.pop(
            "user_id",
            None
        )

        request.session.pop(
            "user_name",
            None
        )

        request.session.pop(
            "java_token",
            None
        )

        # ----------------------------------------------------
        # 清掉之前暂存的 SSO 用户
        # ----------------------------------------------------

        request.session.pop(
            "sso_user",
            None
        )

        request.session.pop(
            "sso_java_token",
            None
        )

        # ----------------------------------------------------
        # 保存本次 Java 登录用户
        # ----------------------------------------------------

        request.session["sso_user"] = current_user

        request.session["sso_java_token"] = token

        print("----------------------------------------")
        print("🔥 Java 用户身份验证成功")

        print(
            f"用户 : "
            f"{current_user.get('user_name')}"
        )

        print(
            f"用户ID : "
            f"{current_user.get('user_id')}"
        )

        print(
            f"部门 : "
            f"{current_user.get('subjection_name')}"
        )

        print("----------------------------------------")

        print(
            "🔥 已清理旧 Python 登录状态"
        )

        print(
            "🔥 暂存新的 sso_user"
        )

        print(
            "➡️ 跳转 Python 登录页"
        )

        print("========================================")

        # ----------------------------------------------------
        # 进入 Python 登录页
        # ----------------------------------------------------

        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # ========================================================
    # ② Python 登录页面 GET
    # ========================================================

    @app.get("/login")
    async def login_page(
        request: Request
    ):

        # ----------------------------------------------------
        # 获取当前正式 Python 用户
        # ----------------------------------------------------

        user = request.session.get("user")

        # ----------------------------------------------------
        # 获取当前 Java SSO 用户
        # ----------------------------------------------------

        sso_user = request.session.get("sso_user")

        # ====================================================
        # ⭐ 重点：防止旧用户 Session 与新 Java 用户不一致
        # ====================================================

        if user:

            if sso_user:

                old_user_id = user.get("user_id")
                new_user_id = sso_user.get("user_id")

                # --------------------------------------------
                # 用户相同
                # --------------------------------------------

                if (
                    old_user_id
                    and new_user_id
                    and old_user_id == new_user_id
                ):

                    print(
                        f"✅ Python 已登录："
                        f"{user.get('user_name')}"
                    )

                    return RedirectResponse(
                        url="/",
                        status_code=303
                    )

                # --------------------------------------------
                # 用户不同
                # --------------------------------------------

                print("----------------------------------------")
                print("⚠️ 检测到 Java 用户发生变化")
                print(
                    f"旧 Python 用户："
                    f"{user.get('user_name')}"
                )
                print(
                    f"新 Java 用户："
                    f"{sso_user.get('user_name')}"
                )
                print("----------------------------------------")

                # 清掉旧 Python Session
                request.session.pop(
                    "user",
                    None
                )

                request.session.pop(
                    "user_id",
                    None
                )

                request.session.pop(
                    "user_name",
                    None
                )

                request.session.pop(
                    "java_token",
                    None
                )

            else:

                # --------------------------------------------
                # 有 Python 用户，但是没有 SSO 用户
                #
                # 这里保留原逻辑：
                # Python 自己已经登录，可以继续使用
                # --------------------------------------------

                print(
                    f"✅ Python 已正式登录："
                    f"{user.get('user_name')}"
                )

                return RedirectResponse(
                    url="/",
                    status_code=303
                )

        # ----------------------------------------------------
        # Java SSO 已经验证成功
        # ----------------------------------------------------

        sso_user = request.session.get("sso_user")

        if sso_user:

            print(
                "✅ /login 获取到 sso_user："
                f"{sso_user.get('user_name')}"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user
                }
            )

        # ----------------------------------------------------
        # 没有 Java SSO
        # ----------------------------------------------------

        print(
            "❌ /login 没有 sso_user"
        )

        return templates.TemplateResponse(
            "pages/login.html",
            {
                "request": request,
                "sso_login": False,
                "error":
                    "请先通过 Java 系统进入本系统"
            }
        )

    # ========================================================
    # ③ Python 登录 POST
    # ========================================================

    @app.post("/login")
    async def login(
        request: Request
    ):

        print("========================================")
        print("🔐 Python 登录 POST")
        print("========================================")

        # ----------------------------------------------------
        # 必须先有 Java SSO 用户
        # ----------------------------------------------------

        sso_user = request.session.get("sso_user")

        if not sso_user:

            print(
                "❌ 没有 sso_user"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": False,
                    "error":
                        "请先通过 Java 系统进入本系统"
                },
                status_code=401
            )

        # ----------------------------------------------------
        # 获取表单
        # ----------------------------------------------------

        try:

            form = await request.form()

            password = str(
                form.get("password") or ""
            ).strip()

        except Exception as e:

            print(
                f"❌ 获取登录参数失败: {e}"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "登录参数错误"
                },
                status_code=400
            )

        # ----------------------------------------------------
        # 密码不能为空
        # ----------------------------------------------------

        if not password:

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "请输入密码"
                },
                status_code=400
            )

        # ----------------------------------------------------
        # 获取用户ID
        # ----------------------------------------------------

        user_id = sso_user.get("user_id")

        if not user_id:

            print(
                "❌ sso_user 中没有 user_id"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "当前登录用户信息异常，请重新进入"
                },
                status_code=400
            )

        print(
            f"👤 当前用户："
            f"{sso_user.get('user_name')}"
        )

        print(
            f"🆔 用户ID："
            f"{user_id}"
        )

        # ----------------------------------------------------
        # 调用 Java 验证密码
        # ----------------------------------------------------

        try:

            java_token = (
                request.session.get(
                    "sso_java_token"
                )
            )

            if not java_token:

                print(
                    "❌ 当前没有 Java SSO Token"
                )

                return templates.TemplateResponse(
                    "pages/login.html",
                    {
                        "request": request,
                        "sso_login": True,
                        "sso_user": sso_user,
                        "error":
                            "Java 登录已失效，请重新进入"
                    },
                    status_code=401
                )

            response = requests.post(
                JAVA_VERIFY_PASSWORD_URL,
                headers={
                    "satoken": java_token
                },
                json={
                    "user_id":
                        user_id,

                    "phone":
                        sso_user.get("phone"),

                    "password":
                        password
                },
                timeout=10
            )

            print(
                f"📡 Java 密码验证 HTTP："
                f"{response.status_code}"
            )

            print(
                f"📦 Java 密码验证返回："
                f"{response.text}"
            )

        except requests.exceptions.Timeout:

            print(
                "❌ Java 密码验证超时"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "连接 Java 系统超时"
                },
                status_code=500
            )

        except requests.exceptions.ConnectionError as e:

            print(
                f"❌ 无法连接 Java：{e}"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "无法连接 Java 系统"
                },
                status_code=500
            )

        except Exception as e:

            print(
                f"❌ 密码验证异常：{e}"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "密码验证失败"
                },
                status_code=500
            )

        # ----------------------------------------------------
        # Java HTTP 非 200
        # ----------------------------------------------------

        if response.status_code != 200:

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "密码验证失败"
                },
                status_code=401
            )

        # ----------------------------------------------------
        # 解析 Java 返回
        # ----------------------------------------------------

        try:

            result = response.json()

        except ValueError:

            print(
                "❌ Java 返回数据不是 JSON"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        "Java 返回数据格式错误"
                },
                status_code=500
            )

        # ----------------------------------------------------
        # 密码错误
        # ----------------------------------------------------

        if result.get("code") != 200:

            print(
                f"❌ 密码验证失败："
                f"{result.get('msg')}"
            )

            return templates.TemplateResponse(
                "pages/login.html",
                {
                    "request": request,
                    "sso_login": True,
                    "sso_user": sso_user,
                    "error":
                        result.get(
                            "msg",
                            "账户或密码错误"
                        )
                },
                status_code=401
            )

        # ----------------------------------------------------
        # 密码正确
        # ----------------------------------------------------

        print(
            "✅ Java 密码验证成功"
        )

        print(
            "✅ 建立 Python 正式 Session"
        )

        request.session["user"] = sso_user

        request.session["user_id"] = (
            sso_user.get("user_id")
        )

        request.session["user_name"] = (
            sso_user.get("user_name")
        )

        # ----------------------------------------------------
        # 暂存 Java Token
        # ----------------------------------------------------

        request.session["java_token"] = (
            request.session.get(
                "sso_java_token"
            )
        )

        # ----------------------------------------------------
        # 删除临时 SSO Session
        # ----------------------------------------------------

        request.session.pop(
            "sso_user",
            None
        )

        request.session.pop(
            "sso_java_token",
            None
        )

        print("========================================")

        print(
            "🎉 Python 登录成功"
        )

        print(
            f"👤 用户："
            f"{sso_user.get('user_name')}"
        )

        print(
            "➡️ 进入 Python 首页"
        )

        print("========================================")

        return RedirectResponse(
            url="/",
            status_code=303
        )

    # ========================================================
    # ④ Python 退出
    # ========================================================

    @app.get("/logout")
    async def logout(
        request: Request
    ):

        print("========================================")
        print("👋 Python 退出登录")
        print("========================================")

        try:

            request.session.clear()

        except Exception as e:

            print(
                f"⚠️ 清理 Python Session 失败: {e}"
            )

        # ----------------------------------------------------
        # 重新进入 Java SSO
        # ----------------------------------------------------

        JAVA_SSO_URL = (
            f"{JAVA_BASE_URL}/python/sso"
        )

        print(
            f"➡️ 重新进入 Java SSO: "
            f"{JAVA_SSO_URL}"
        )

        return RedirectResponse(
            url=JAVA_SSO_URL,
            status_code=303
        )

    # ========================================================
    # ⑤ 登录状态检查
    # ========================================================

    @app.get("/api/auth/check")
    async def check_auth(
        request: Request
    ):

        session_user = (
            request.session.get("user")
        )

        if session_user:

            return {
                "success": True,

                "data": {

                    "is_login": True,

                    "user_id":
                        session_user.get(
                            "user_id"
                        ),

                    "username": (
                        session_user.get(
                            "user_name"
                        )
                        or session_user.get(
                            "user_code"
                        )
                        or ""
                    ),

                    "phone":
                        session_user.get(
                            "phone"
                        ),

                    "role": (
                        session_user.get(
                            "duties_name"
                        )
                        or session_user.get(
                            "post_name"
                        )
                        or "普通用户"
                    )
                }
            }

        # ----------------------------------------------------
        # 没有 Python Session
        #
        # 注意：
        # 这里不能自动通过 Java Token 登录
        # 必须点击 Python 登录按钮
        # ----------------------------------------------------

        return {

            "success": False,

            "data": {

                "is_login": False
            },

            "message":
                "未登录，请先登录"
        }

    # ========================================================
    # ⑥ 获取当前用户信息
    # ========================================================

    @app.get("/api/user/info")
    async def get_user_info(
        request: Request
    ):

        # ----------------------------------------------------
        # 只使用 Python 正式 Session
        # ----------------------------------------------------

        user = request.session.get("user")

        if not user:

            print(
                "❌ 当前没有登录用户"
            )

            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message":
                        "未登录或 Java 登录已失效"
                }
            )

        # ----------------------------------------------------
        # Python 前端真正需要的数据
        # ----------------------------------------------------

        user_info = {

            "user_id":
                user.get("user_id"),

            "user_name":
                user.get("user_name"),

            "subjection_id":
                user.get("subjection_id"),

            "subjection_name":
                user.get("subjection_name"),

            "mine_id":
                user.get("register_dept_id"),

            "mine_name":
                user.get("register_dept_name")
        }

        # ----------------------------------------------------
        # 打印
        # ----------------------------------------------------

        print("========================================")
        print("       当前登录用户信息")
        print("========================================")

        print(
            f"用户ID   : "
            f"{user_info['user_id']}"
        )

        print(
            f"登录人   : "
            f"{user_info['user_name']}"
        )

        print(
            f"部门ID   : "
            f"{user_info['subjection_id']}"
        )

        print(
            f"部门     : "
            f"{user_info['subjection_name']}"
        )

        print(
            f"矿井ID   : "
            f"{user_info['mine_id']}"
        )

        print(
            f"矿井     : "
            f"{user_info['mine_name']}"
        )

        print("========================================")

        return {

            "success": True,

            "data": user_info
        }

    # ========================================================
    # 认证路由注册完成
    # ========================================================

    print(
        "✅ 认证路由注册完成"
    )