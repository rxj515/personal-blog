# ============================================================
# import_questions_db.py
#
# Python AI题库
# 调用 Java 接口导入 study_dept_bank_manage
#
# Python → Java Gateway → bs-local → MySQL
# ============================================================

import os
import requests


# ============================================================
# Java 接口地址
# ============================================================

JAVA_IMPORT_URL = os.getenv(
    "JAVA_IMPORT_URL",
    "http://localhost:1100/deptBankManage/python/import"
)


# ============================================================
# 主函数
# ============================================================

def main(data: dict, java_token: str = None):

    """
    调用 Java 接口导入题目

    参数：
        data:
        {
            "dept": {
                "id": "xxx",
                "fullName": "xxx"
            },
            "create_user_id": "xxx",
            "create_user_name": "xxx",
            "questions": [
                {
                    "question_type": "单选题",
                    "title": "题目",
                    "plan_a": "选项A",
                    "plan_b": "选项B",
                    "plan_c": "选项C",
                    "plan_d": "选项D",
                    "answer": "A",
                    "analysis": "解析"
                }
            ]
        }

        java_token:
            当前 Java 登录用户的 Sa-Token
    """

    # ========================================================
    # 1. 检查 Java Token
    # ========================================================

    if not java_token:

        print("❌ 当前没有 Java 登录 Token")

        return {
            "total": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": [
                "Java登录状态已失效，请重新进入通用法规 AI"
            ]
        }

    # ========================================================
    # 2. 获取题目
    # ========================================================

    questions = data.get("questions", [])

    if not questions:

        return {
            "total": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": [
                "没有可导入的题目"
            ]
        }

    # ========================================================
    # 3. 获取分类
    # ========================================================

    dept = data.get("dept", {})

    dept_id = dept.get("id", "")
    dept_name = dept.get("fullName", "")

    if not dept_id:

        return {
            "total": len(questions),
            "inserted": 0,
            "skipped": 0,
            "errors": [
                "请先选择所属分类"
            ]
        }

    # ========================================================
    # 4. 获取创建用户
    #
    # 当前先兼容你原来的方式。
    #
    # 后续如果 Java 导入接口直接从 Sa-Token 获取用户，
    # 这里甚至可以不再传 create_user_id / create_user_name。
    # ========================================================

    create_user_id = data.get(
        "create_user_id",
        "system"
    )

    create_user_name = data.get(
        "create_user_name",
        "系统导入"
    )

    # ========================================================
    # 5. 组装给 Java 的数据
    # ========================================================

    java_data = {

        "dept": {
            "id": dept_id,
            "fullName": dept_name
        },

        "create_user_id": create_user_id,

        "create_user_name": create_user_name,

        "questions": questions
    }

    # ========================================================
    # 6. 调用 Java
    # ========================================================

    try:

        print("=" * 60)
        print("🔗 正在调用 Java 题库导入接口")
        print("=" * 60)

        print(f"Java接口：{JAVA_IMPORT_URL}")
        print(f"题目数量：{len(questions)}")
        print(f"分类ID：{dept_id}")
        print(f"分类名称：{dept_name}")
        print(f"创建用户ID：{create_user_id}")
        print(f"创建用户名：{create_user_name}")

        # ====================================================
        # 重要：
        # 把当前 Java 登录用户的 Sa-Token 传给 Gateway
        # ====================================================

        headers = {
            "satoken": java_token
        }

        response = requests.post(

            JAVA_IMPORT_URL,

            headers=headers,

            json=java_data,

            timeout=120
        )

        print(
            f"Java HTTP状态码：{response.status_code}"
        )

        # ====================================================
        # 7. HTTP错误
        # ====================================================

        response.raise_for_status()

        # ====================================================
        # 8. 解析 Java 返回结果
        # ====================================================

        result = response.json()

        print("Java返回：")
        print(result)

        # ====================================================
        # 9. Java正常返回
        # ====================================================

        if result.get("code") == 200:

            java_result = result.get(
                "data",
                {}
            )

            inserted = java_result.get(
                "inserted",
                0
            )

            skipped = java_result.get(
                "skipped",
                0
            )

            errors = java_result.get(
                "errors",
                []
            )

            print()

            print("=" * 60)
            print("📊 导入统计")
            print("=" * 60)

            print(
                f"总数：{len(questions)} 道"
            )

            print(
                f"成功：{inserted} 道 ✅"
            )

            print(
                f"跳过：{skipped} 道 ⏭️"
            )

            if errors:

                print(
                    f"错误：{len(errors)} 条 ❌"
                )

                for error in errors:

                    print(
                        f"  - {error}"
                    )

            print("=" * 60)

            # =================================================
            # 返回给 Python 上层
            # =================================================

            return {

                "total": java_result.get(
                    "total",
                    len(questions)
                ),

                "inserted": inserted,

                "skipped": skipped,

                "errors": errors
            }

        # ====================================================
        # 10. Java业务错误
        # ====================================================

        else:

            msg = result.get(
                "msg",
                "Java接口返回失败"
            )

            print(
                f"❌ Java导入失败：{msg}"
            )

            return {

                "total": len(questions),

                "inserted": 0,

                "skipped": 0,

                "errors": [
                    msg
                ]
            }

    # ========================================================
    # 11. 网络超时
    # ========================================================

    except requests.exceptions.Timeout:

        print(
            "❌ 调用 Java 接口超时"
        )

        return {

            "total": len(questions),

            "inserted": 0,

            "skipped": 0,

            "errors": [
                "调用 Java 题库导入接口超时"
            ]
        }

    # ========================================================
    # 12. Java连接失败
    # ========================================================

    except requests.exceptions.ConnectionError as e:

        print(
            f"❌ 无法连接 Java：{e}"
        )

        return {

            "total": len(questions),

            "inserted": 0,

            "skipped": 0,

            "errors": [
                "无法连接 Java 服务器"
            ]
        }

    # ========================================================
    # 13. HTTP错误
    # ========================================================

    except requests.exceptions.HTTPError as e:

        print(
            f"❌ Java HTTP错误：{e}"
        )

        return {

            "total": len(questions),

            "inserted": 0,

            "skipped": 0,

            "errors": [
                f"Java接口HTTP错误：{str(e)}"
            ]
        }

    # ========================================================
    # 14. JSON解析错误
    # ========================================================

    except ValueError as e:

        print(
            f"❌ Java返回的数据不是合法JSON：{e}"
        )

        return {

            "total": len(questions),

            "inserted": 0,

            "skipped": 0,

            "errors": [
                "Java返回的数据格式错误"
            ]
        }

    # ========================================================
    # 15. 其他异常
    # ========================================================

    except Exception as e:

        print(
            f"❌ 导入失败：{e}"
        )

        return {

            "total": len(questions),

            "inserted": 0,

            "skipped": 0,

            "errors": [
                f"导入失败：{str(e)}"
            ]
        }