# -*- coding: utf-8 -*-

"""
create_user.py

用法：
    python create_user.py 用户名
    python create_user.py 用户名 --admin

例如：
    python create_user.py zhangsan
    python create_user.py admin --admin

说明：
    默认创建普通用户。
    使用 --admin 参数创建管理员。

程序会要求输入两次密码，
并把密码转换成 PBKDF2-SHA256 哈希后保存到 data/users.json。

不会保存明文密码。
"""

import getpass
import json
import os
import sys
from pathlib import Path

from auth import make_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"


def load_users():
    """
    读取 users.json
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not USERS_FILE.exists():

        USERS_FILE.write_text(
            "[]\n",
            encoding="utf-8"
        )

        try:
            os.chmod(
                USERS_FILE,
                0o600
            )
        except Exception:
            pass

    try:

        data = json.loads(
            USERS_FILE.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as e:

        raise RuntimeError(
            f"users.json 格式错误：{e}"
        )

    if not isinstance(data, list):

        raise RuntimeError(
            "users.json 根节点必须是数组"
        )

    return data


def save_users(users):
    """
    保存 users.json
    """

    USERS_FILE.write_text(
        json.dumps(
            users,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    try:

        os.chmod(
            USERS_FILE,
            0o600
        )

    except Exception:
        pass


def main():

    # ========================================================
    # 1. 检查命令行参数
    # ========================================================

    if len(sys.argv) not in (2, 3):

        print()
        print("用法：")
        print("  python create_user.py 用户名")
        print("  python create_user.py 用户名 --admin")
        print()
        print("例如：")
        print("  python create_user.py zhangsan")
        print("  python create_user.py admin --admin")
        print()

        sys.exit(1)

    username = sys.argv[1].strip()

    # ========================================================
    # 2. 判断是否创建管理员
    # ========================================================

    is_admin = False

    if len(sys.argv) == 3:

        if sys.argv[2].lower() != "--admin":

            print()
            print("❌ 第二个参数只能是 --admin")
            print()

            sys.exit(1)

        is_admin = True

    # ========================================================
    # 3. 检查用户名
    # ========================================================

    if len(username) < 2:

        print("❌ 用户名至少 2 个字符")
        sys.exit(1)

    if len(username) > 50:

        print("❌ 用户名不能超过 50 个字符")
        sys.exit(1)

    if any(
        c.isspace()
        for c in username
    ):

        print("❌ 用户名不能包含空格")
        sys.exit(1)

    # ========================================================
    # 4. 读取现有用户
    # ========================================================

    try:

        users = load_users()

    except Exception as e:

        print(
            f"❌ 读取用户数据失败：{e}"
        )

        sys.exit(1)

    # ========================================================
    # 5. 检查用户名是否已经存在
    # ========================================================

    for user in users:

        old_username = str(
            user.get("username") or ""
        ).strip()

        if old_username.lower() == username.lower():

            print()
            print(
                f"❌ 用户已存在：{username}"
            )
            print()
            print(
                "如果需要修改该用户权限，"
                "请修改现有账户，不要重复创建。"
            )
            print()

            sys.exit(1)

    # ========================================================
    # 6. 输入密码
    # ========================================================

    print()
    print("=" * 50)
    print(
        f"创建 Python 登录账号：{username}"
    )
    print(
        "账户角色："
        + (
            "管理员"
            if is_admin
            else "普通用户"
        )
    )
    print("=" * 50)

    password = getpass.getpass(
        "请输入密码（至少12位）："
    )

    confirm = getpass.getpass(
        "请再次输入密码："
    )

    # ========================================================
    # 7. 确认密码
    # ========================================================

    if password != confirm:

        print(
            "❌ 两次密码不一致"
        )

        sys.exit(1)

    # ========================================================
    # 8. 生成密码 Hash
    # ========================================================

    try:

        password_hash = make_password_hash(
            password
        )

    except ValueError as e:

        print(
            f"❌ {e}"
        )

        sys.exit(1)

    # ========================================================
    # 9. 生成用户 ID
    # ========================================================

    user_id = (
        "python-"
        + os.urandom(8).hex()
    )

    # ========================================================
    # 10. 创建用户
    # ========================================================

    new_user = {

        "user_id": user_id,

        "username": username,

        "password_hash": password_hash,

        # ----------------------------------------------------
        # 默认普通用户
        # 使用 --admin 才创建管理员
        # ----------------------------------------------------

        "role": (
            "管理员"
            if is_admin
            else "普通用户"
        ),

        "enabled": True,

        # ----------------------------------------------------
        # 用户基础信息
        # ----------------------------------------------------

        "user_code": username,

        "phone": None,

        "duties_name": None,

        "post_name": None,

        "subjection_id": None,

        "subjection_name": None,

        "register_dept_id": None,

        "register_dept_name": None,

        "mine_id": None,

        "mine_name": None
    }

    # ========================================================
    # 11. 保存用户
    # ========================================================

    users.append(
        new_user
    )

    try:

        save_users(users)

    except Exception as e:

        print(
            f"❌ 保存用户失败：{e}"
        )

        sys.exit(1)

    # ========================================================
    # 12. 输出结果
    # ========================================================

    print()
    print("=" * 50)
    print("✅ 账号创建成功")
    print("=" * 50)
    print(
        f"👤 用户名：{username}"
    )
    print(
        "🛡️ 角色："
        + (
            "管理员"
            if is_admin
            else "普通用户"
        )
    )
    print(
        "🔐 密码：已保存为 PBKDF2-SHA256 哈希"
    )
    print(
        f"🆔 用户ID：{user_id}"
    )
    print(
        f"📄 文件：{USERS_FILE}"
    )
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
