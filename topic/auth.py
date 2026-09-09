# auth.py - 认证模块（使用 cryptography 库私钥解密）
import pymysql
import hashlib
import base64
from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# ============================================================
# 数据库配置
# ============================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'xlmy_exam',
    'charset': 'utf8mb4'
}

USER_TABLE = 'sys_users'


# ============================================================
# RSA 私钥
# ============================================================
def get_private_key():
    """从文件读取 RSA 私钥"""
    private_key_path = Path(__file__).parent / "private_key.pem"

    if not private_key_path.exists():
        print(f"❌ 找不到私钥文件: {private_key_path}")
        return None

    with open(private_key_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    print("========== 私钥检查 ==========")
    print("私钥文件:", private_key_path)
    print("私钥长度:", len(content))
    print("私钥开头:", repr(content[:80]))
    print("私钥结尾:", repr(content[-80:]))
    print("==============================")

    # 如果文件里的换行被保存成了字面量 \n，则还原
    content = content.replace("\\n", "\n")

    return content

_PRIVATE_KEY_CACHE = None

def get_private_key_cached():
    global _PRIVATE_KEY_CACHE
    if _PRIVATE_KEY_CACHE is None:
        _PRIVATE_KEY_CACHE = get_private_key()
    return _PRIVATE_KEY_CACHE


# ============================================================
# 私钥解密（使用 cryptography 库，支持 PKCS1/PKCS8）
# ============================================================

def rsa_decrypt(encrypted_password):
    try:
        # 1. 读取公钥
        public_key_path = Path(__file__).parent / "public_key.pem"

        public_key_base64 = public_key_path.read_text(
            encoding="utf-8"
        ).strip()

        # 如果有 PEM 头，去掉
        public_key_base64 = (
            public_key_base64
            .replace("-----BEGIN PUBLIC KEY-----", "")
            .replace("-----END PUBLIC KEY-----", "")
            .replace("\n", "")
            .replace("\r", "")
        )

        # 2. Base64 -> DER
        public_key_der = base64.b64decode(public_key_base64)

        # 3. 加载 X509 公钥
        public_key = serialization.load_der_public_key(
            public_key_der,
            backend=default_backend()
        )

        print("✅ RSA 公钥加载成功")
        print(f"🔑 密钥长度: {public_key.key_size} bit")

        # 4. Java:
        # SaBase64Util.decode(users.getPassword())
        #
        # 得到 256 位 HEX 字符串
        hex_content = base64.b64decode(
            encrypted_password
        ).decode("utf-8")

        print(f"🔓 Base64 解码后 HEX 长度: {len(hex_content)}")
        print(f"🔓 HEX 开头: {hex_content[:40]}")

        # 5. HEX -> RSA 密文
        encrypted_data = bytes.fromhex(hex_content)

        print(f"🔓 RSA 密文长度: {len(encrypted_data)} 字节")

        # 6. 获取 RSA 公钥参数
        numbers = public_key.public_numbers()

        n = numbers.n
        e = numbers.e

        key_size_bytes = public_key.key_size // 8

        result = b""

        # 7. 按 Java rsaDecryptByPublic 的方式处理
        for i in range(0, len(encrypted_data), key_size_bytes):

            chunk = encrypted_data[i:i + key_size_bytes]

            print(
                f"  解密第 {i // key_size_bytes + 1} 段: "
                f"{len(chunk)} 字节"
            )

            if len(chunk) != key_size_bytes:
                raise ValueError(
                    f"RSA 密文长度错误: {len(chunk)} != {key_size_bytes}"
                )

            # RSA 公钥运算：
            # m = c^e mod n
            c = int.from_bytes(chunk, byteorder="big")

            if c >= n:
                raise ValueError("RSA 密文大于模数")

            m = pow(c, e, n)

            decrypted = m.to_bytes(
                key_size_bytes,
                byteorder="big"
            )

            print(
                f"🔍 RSA 运算后字节: {decrypted[:20]!r}"
            )

            # PKCS#1 v1.5 解包
            #
            # 正常格式：
            # 00 01 FF FF FF ... FF 00 DATA
            if not decrypted.startswith(b"\x00\x01"):
                raise ValueError(
                    f"RSA PKCS#1 格式不正确，开头: "
                    f"{decrypted[:10].hex()}"
                )

            separator = decrypted.find(b"\x00", 2)

            if separator == -1:
                raise ValueError(
                    "RSA PKCS#1 数据中没有找到分隔符"
                )

            padding_bytes = decrypted[2:separator]

            # PKCS#1 v1.5 的 padding 至少 8 个 FF
            if len(padding_bytes) < 8:
                raise ValueError(
                    "RSA PKCS#1 padding 长度异常"
                )

            result += decrypted[separator + 1:]

        print(f"🔍 最终解密字节: {result!r}")

        # 8. Java new String(cipher.doFinal(array))
        password = result.decode("utf-8")

        print(f"✅ RSA 解密成功: {password!r}")
        print("🔐 RSA 解密成功")

        return password

    except Exception as e:
        print(f"❌ RSA 解密失败: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================
# 数据库连接
# ============================================================

def get_db_connection():
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset'],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return None


# ============================================================
# 用户查询
# ============================================================

def get_user_by_phone(phone: str):
    conn = get_db_connection()

    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            sql = f"""
                SELECT
                    id,
                    user_name,
                    user_code,
                    phone,
                    password,
                    duties_name,
                    post_name,
                    is_forbidden,
                    subjection_id,
                    subjection_name,
                    register_dept_id,
                    register_dept_Name
                FROM {USER_TABLE}
                WHERE phone = %s
                LIMIT 1
            """

            cursor.execute(sql, (phone,))
            result = cursor.fetchone()

            print("========== 登录用户查询结果 ==========")
            print(f"用户ID   : {result.get('id') if result else None}")
            print(f"登录人   : {result.get('user_name') if result else None}")
            print(f"部门ID   : {result.get('subjection_id') if result else None}")
            print(f"部门     : {result.get('subjection_name') if result else None}")
            print(f"矿井ID   : {result.get('register_dept_id') if result else None}")
            print(f"矿井     : {result.get('register_dept_Name') if result else None}")
            print("======================================")

            return result

    except Exception as e:
        print(f"❌ 查询用户失败: {e}")
        return None

    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db_connection()

    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            sql = f"""
                SELECT
                    id,
                    user_name,
                    user_code,
                    phone,
                    password,
                    duties_name,
                    post_name,
                    is_forbidden,
                    subjection_id,
                    subjection_name,
                    register_dept_id,
                    register_dept_Name
                FROM {USER_TABLE}
                WHERE id = %s
                LIMIT 1
            """

            cursor.execute(sql, (user_id,))
            result = cursor.fetchone()

            if result:
                print("========== 当前用户查询 ==========")
                print(f"用户ID : {result.get('id')}")
                print(f"登录人 : {result.get('user_name')}")
                print(f"部门   : {result.get('subjection_name')}")
                print(f"矿井   : {result.get('register_dept_Name')}")
                print("================================")

            return result

    except Exception as e:
        print(f"❌ 获取用户失败: {e}")
        return None

    finally:
        if conn:
            conn.close()

# ============================================================
# 密码验证
# ============================================================

def verify_password(password: str, password_hash: str) -> bool:
    # 1. 私钥解密
    decrypted = rsa_decrypt(password_hash)
    if decrypted is not None and password == decrypted:
        print("✅ 私钥解密验证成功")
        return True
    
    # 2. MD5
    if hashlib.md5(password.encode('utf-8')).hexdigest() == password_hash:
        print("✅ MD5 验证成功")
        return True
    
    # 3. 明文
    if password == password_hash:
        print("✅ 明文验证成功")
        return True
    
    return False


# ============================================================
# 获取当前用户
# ============================================================

async def get_current_user(request: Request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    return get_user_by_id(user_id)


# ============================================================
# 依赖注入
# ============================================================

async def require_login(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


async def require_login_redirect(request: Request, user: dict = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
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
    # 检查登录
    user = await get_current_user(request)

    if not user:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    # 保持原来的模板 request
    data = {
        "request": request
    }

    # 登录用户信息
    data["username"] = (
        user.get("user_name")
        or user.get("user_code")
        or user.get("phone")
        or ""
    )

    data["role"] = (
        user.get("duties_name")
        or user.get("post_name")
        or "普通用户"
    )

    data["user"] = user

    # 额外数据
    if extra_data:
        data.update(extra_data)

    return _templates.TemplateResponse(
        template_name,
        data
    )

# ============================================================
# 设置认证路由
# ============================================================

def setup_auth_routes(app, templates):
    
    set_templates(templates)
    
    @app.get("/login")
    async def login_page(request: Request):
        user = await get_current_user(request)
        if user:
            return RedirectResponse(url="/dashboard")
        return templates.TemplateResponse("pages/login.html", {"request": request})
    
    @app.post("/login")
    async def login(request: Request):
        form = await request.form()
        phone = form.get('username', '').strip()
        password = form.get('password', '').strip()
        
        print(f"📱 登录尝试: phone={phone}")
        
        if not phone or not password:
            print("❌ 手机号或密码为空")
            return templates.TemplateResponse(
                "pages/login.html", 
                {"request": request, "error": "请输入手机号和密码"}
            )
        
        user_data = get_user_by_phone(phone)
        
        if not user_data:
            print(f"❌ 用户不存在: {phone}")
            return templates.TemplateResponse(
                "pages/login.html", 
                {"request": request, "error": "用户不存在"}
            )
        
        print(f"👤 找到用户: {user_data.get('user_name')}")
        
        if user_data.get('is_forbidden', 0) == 1:
            print("❌ 账号被禁用")
            return templates.TemplateResponse(
                "pages/login.html", 
                {"request": request, "error": "账号已被禁用，请联系管理员"}
            )
        
        password_hash = user_data.get('password', '')
        print(f"🔐 验证密码: 输入长度={len(password)}, 哈希长度={len(password_hash)}")
        
        if not password_hash or not verify_password(password, password_hash):
            print("❌ 密码错误")
            return templates.TemplateResponse(
                "pages/login.html", 
                {"request": request, "error": "密码错误"}
            )
        
        request.session['user_id'] = str(user_data.get('id'))
        request.session['username'] = (
            user_data.get('user_name')
            or user_data.get('user_code')
            or phone
        )
        request.session['role'] = (
            user_data.get('duties_name')
            or user_data.get('post_name')
            or '普通用户'
        )
        request.session['phone'] = phone

        print("========================================")
        print("              登录成功")
        print("========================================")
        print(f"用户ID   : {user_data.get('id')}")
        print(f"登录人   : {user_data.get('user_name')}")
        print(f"部门     : {user_data.get('subjection_name')}")
        print(f"矿井     : {user_data.get('register_dept_Name')}")
        print("========================================")

        return RedirectResponse(url="/", status_code=303)

    
    @app.get("/logout")
    async def logout(request: Request):
        username = request.session.get('username', '')
        request.session.clear()
        print(f"👋 用户退出: {username}")
        return RedirectResponse(url="/login")
    
    @app.get("/api/auth/check")
    async def check_auth(request: Request):
        user = await get_current_user(request)
        if user:
            return {
                "success": True,
                "data": {
                    "is_login": True,
                    "user_id": user.get('id'),
                    "username": user.get('user_name') or user.get('user_code'),
                    "phone": user.get('phone'),
                    "role": user.get('duties_name') or user.get('post_name') or '普通用户'
                }
            }
        return {
            "success": False,
            "data": {"is_login": False},
            "message": "未登录"
        }
    
    @app.get("/api/user/info")
    async def get_user_info(request: Request):

        user = await get_current_user(request)

        if not user:
            print("❌ 当前没有登录用户")

            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "未登录，请先登录"
                }
            )

        # 只取需要的信息
        user_info = {
            "user_id": user.get("id"),
            "user_name": user.get("user_name"),
            "subjection_id": user.get("subjection_id"),
            "subjection_name": user.get("subjection_name"),
            "mine_id": user.get("register_dept_id"),
            "mine_name": user.get("register_dept_Name")
        }

        # 打印当前登录人信息
        print("========================================")
        print("       当前登录用户信息")
        print("========================================")
        print(f"用户ID   : {user_info['user_id']}")
        print(f"登录人   : {user_info['user_name']}")
        print(f"部门ID   : {user_info['subjection_id']}")
        print(f"部门     : {user_info['subjection_name']}")
        print(f"矿井ID   : {user_info['mine_id']}")
        print(f"矿井     : {user_info['mine_name']}")
        print("========================================")

        return {
            "success": True,
            "data": user_info
        }
        
    @app.get("/api/test-db")
    async def test_db():
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                conn.close()
                return {
                    "success": True,
                    "message": "数据库连接成功",
                    "database": DB_CONFIG['database']
                }
            except Exception as e:
                return {"success": False, "message": f"查询失败: {e}"}
        return {
            "success": False,
            "message": "数据库连接失败",
            "config": {
                "host": DB_CONFIG['host'],
                "port": DB_CONFIG['port'],
                "database": DB_CONFIG['database']
            }
        }
    
    print("✅ 认证路由注册完成")
