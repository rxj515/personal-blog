# ============================================================
# import_questions_db.py
# 导入题目到 study_dept_bank_manage 表
#
# ============================================================

import pymysql
from pathlib import Path
from datetime import datetime

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

# ============================================================
# 主函数
# ============================================================

def main(data: dict):
    """
    导入题目到 study_dept_bank_manage 表
    """
    questions = data.get("questions", [])

    if not questions:
        return {
            "total": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": ["没有可导入的题目"]
        }

    connection = None

    try:
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset']
        )

        cursor = connection.cursor()

        # ----------------------------------------------------
        # 获取当前最大 index_num（用于生成序号）
        # ----------------------------------------------------
        cursor.execute("SELECT MAX(index_num) FROM study_dept_bank_manage")
        result = cursor.fetchone()
        max_index = result[0] if result and result[0] else 0

        # ----------------------------------------------------
        # 插入数据
        # ----------------------------------------------------
        inserted_count = 0
        skipped_count = 0
        errors = []

        insert_sql = """
            INSERT INTO study_dept_bank_manage (
                id,
                index_num,
                title_category_id,
                title_category_name,
                subjects,
                plan_A,
                plan_B,
                plan_C,
                plan_D,
                plan_E,
                plan_F,
                options,
                options_content,
                answer,
                analysis,
                content,
                content_text,
                type,
                is_commit,
                is_bookkeeping,
                is_approvalend,
                is_forbidden,
                create_user_id,
                create_user_name,
                create_date,
                update_user_id,
                update_user_name,
                update_date
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                0, 0, 0, 0,
                'system', '系统导入', NOW(),
                'system', '系统导入', NOW()
            )
        """

        for idx, q in enumerate(questions, 1):
            try:
                # ----------------------------------------------------
                # 提取数据 - 映射到表字段
                # ----------------------------------------------------
                
                # 题型
                question_type = (
                    q.get("question_type") or
                    q.get("type") or
                    q.get("title_category_name") or
                    "单选题"
                )

                # 题目内容
                title = (
                    q.get("title") or
                    q.get("subjects") or
                    q.get("question") or
                    q.get("content") or
                    ""
                )

                # 选项
                option_a = q.get("plan_a") or ""
                option_b = q.get("plan_b") or ""
                option_c = q.get("plan_c") or ""
                option_d = q.get("plan_d") or ""
                option_e = q.get("plan_e") or ""
                option_f = q.get("plan_f") or ""

                # 如果选项为空，尝试从 options 字段读取
                if not any([option_a, option_b, option_c, option_d, option_e, option_f]):
                    options_data = q.get("options", {})
                    if isinstance(options_data, dict):
                        option_a = options_data.get("A", "")
                        option_b = options_data.get("B", "")
                        option_c = options_data.get("C", "")
                        option_d = options_data.get("D", "")
                        option_e = options_data.get("E", "")
                        option_f = options_data.get("F", "")

                # 答案
                answer = (
                    q.get("answer") or
                    q.get("correct_answer") or
                    q.get("correctAnswer") or
                    ""
                )

                # 解析
                analysis = (
                    q.get("analysis") or
                    q.get("explanation") or
                    q.get("explain") or
                    ""
                )

                # 法条编号
                article = q.get("article") or ""

                # 法规名称
                law_name = q.get("law_name") or ""

                if not title:
                    skipped_count += 1
                    continue

                # ----------------------------------------------------
                # 检查是否已存在（去重）
                # ----------------------------------------------------
                check_sql = """
                    SELECT id FROM study_dept_bank_manage 
                    WHERE subjects = %s
                    LIMIT 1
                """
                cursor.execute(check_sql, (title,))
                existing = cursor.fetchone()

                if existing:
                    skipped_count += 1
                    print(f"⏭️ 跳过第 {idx} 题（已存在）")
                    continue

                # ----------------------------------------------------
                # 生成 ID（使用 UUID 或时间戳）
                # ----------------------------------------------------
                import uuid
                record_id = str(uuid.uuid4()).replace('-', '')
                
                # 递增 index_num
                max_index += 1

                # 构建 options 字符串（用于 options 字段）
                options_str = f"A:{option_a};B:{option_b};C:{option_c};D:{option_d}"
                if option_e:
                    options_str += f";E:{option_e}"
                if option_f:
                    options_str += f";F:{option_f}"

                # 构建 options_content（用于 options_content 字段）
                options_content = f"{option_a}|{option_b}|{option_c}|{option_d}"
                if option_e:
                    options_content += f"|{option_e}"
                if option_f:
                    options_content += f"|{option_f}"

                # ----------------------------------------------------
                # 执行插入
                # ----------------------------------------------------
                cursor.execute(insert_sql, (
                    record_id,                                    # id
                    max_index,                                    # index_num
                    '1',                                          # title_category_id (默认)
                    question_type,                                # title_category_name (题型)
                    title,                                        # subjects (题目内容)
                    option_a,                                     # plan_A
                    option_b,                                     # plan_B
                    option_c,                                     # plan_C
                    option_d,                                     # plan_D
                    option_e,                                     # plan_E
                    option_f,                                     # plan_F
                    options_str,                                  # options
                    options_content,                              # options_content
                    answer,                                       # answer
                    analysis,                                     # analysis
                    title,                                        # content
                    title,                                        # content_text
                    question_type                                 # type
                ))

                inserted_count += 1
                print(f"✅ 第 {idx} 题导入成功")

            except Exception as e:
                errors.append(f"第 {idx} 题失败：{str(e)}")
                print(f"❌ 第 {idx} 题失败：{e}")

        connection.commit()

        print()
        print("=" * 60)
        print("📊 导入统计")
        print("=" * 60)
        print(f"总数：{len(questions)} 道")
        print(f"成功：{inserted_count} 道 ✅")
        print(f"跳过：{skipped_count} 道 ⏭️")
        if errors:
            print(f"错误：{len(errors)} 条 ❌")
        print("=" * 60)

        return {
            "total": len(questions),
            "inserted": inserted_count,
            "skipped": skipped_count,
            "errors": errors
        }

    except pymysql.Error as e:
        print(f"❌ 数据库错误：{e}")
        if connection:
            connection.rollback()
        return {
            "total": len(questions),
            "inserted": 0,
            "skipped": 0,
            "errors": [f"数据库错误：{str(e)}"]
        }

    except Exception as e:
        print(f"❌ 错误：{e}")
        if connection:
            connection.rollback()
        return {
            "total": len(questions),
            "inserted": 0,
            "skipped": 0,
            "errors": [f"错误：{str(e)}"]
        }

    finally:
        if connection:
            connection.close()
            print("✅ 数据库连接已关闭")