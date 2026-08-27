# ============================================================
# import_questions_db.py
# 导入题目到 study_dept_bank_manage 表
#
# ============================================================

import pymysql
from datetime import datetime
import uuid
import urllib.parse

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
    
    # 获取分类信息
    dept = data.get("dept", {})
    dept_id = dept.get("id", "")
    dept_name = dept.get("fullName", "")
    
    # 获取当前用户（如果前端没传，用系统默认）
    create_user_id = data.get("create_user_id", "system")
    create_user_name = data.get("create_user_name", "系统导入")
    
    if not questions:
        return {
            "total": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": ["没有可导入的题目"]
        }
    
    if not dept_id:
        return {
            "total": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": ["请先选择所属分类"]
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

        # 使用 DictCursor，这样传参时可以用字典，避免 %s 数量对不上的问题
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        # ----------------------------------------------------
        # 获取当前最大 index_num
        # ----------------------------------------------------
        cursor.execute("SELECT MAX(index_num) AS max_idx FROM study_dept_bank_manage")
        result = cursor.fetchone()
        max_index = result['max_idx'] if result and result['max_idx'] else 0

        # ----------------------------------------------------
        # 插入数据
        # ----------------------------------------------------
        inserted_count = 0
        skipped_count = 0
        errors = []

        for idx, q in enumerate(questions, 1):
            try:
                # ----------------------------------------------------
                # 1. 提取数据
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
                option_a = q.get("plan_a") or q.get("plan_A") or ""
                option_b = q.get("plan_b") or q.get("plan_B") or ""
                option_c = q.get("plan_c") or q.get("plan_C") or ""
                option_d = q.get("plan_d") or q.get("plan_D") or ""
                option_e = q.get("plan_e") or q.get("plan_E") or ""
                option_f = q.get("plan_f") or q.get("plan_F") or ""

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

                if not title:
                    skipped_count += 1
                    continue

                # ----------------------------------------------------
                # 2. 检查是否已存在（去重）
                # ----------------------------------------------------
                check_sql = """
                    SELECT id FROM study_dept_bank_manage 
                    WHERE subjects = %s 
                      AND title_category_name = %s
                      AND dept_type_name = %s
                    LIMIT 1
                """
                cursor.execute(check_sql, (title, question_type, dept_name))
                existing = cursor.fetchone()

                if existing:
                    skipped_count += 1
                    print(f"⏭️ 跳过第 {idx} 题（已存在）")
                    continue

                # ----------------------------------------------------
                # 3. 生成 ID 和序号
                # ----------------------------------------------------
                record_id = str(uuid.uuid4()).replace('-', '')
                max_index += 1

                # ----------------------------------------------------
                # 4. 构建 options 和 options_content
                # ----------------------------------------------------
                options_str = f"A:{option_a};B:{option_b};C:{option_c};D:{option_d}"
                if option_e:
                    options_str += f";E:{option_e}"
                if option_f:
                    options_str += f";F:{option_f}"

                options_content = f"{option_a}|{option_b}|{option_c}|{option_d}"
                if option_e:
                    options_content += f"|{option_e}"
                if option_f:
                    options_content += f"|{option_f}"

                # ----------------------------------------------------
                # 5. 构建 content（URL 编码后的 HTML）
                # ----------------------------------------------------
                if analysis:
                    content_html = f"<p>{analysis}</p>"
                    content = urllib.parse.quote(content_html)
                else:
                    content = None

                # content_text（纯文本）
                content_text = title

                # ----------------------------------------------------
                # 6. 执行插入（用字典传参，绝对不会报参数数量错误）
                # ----------------------------------------------------
                insert_data = {
                    'id': record_id,
                    'index_num': max_index,

                    'create_user_id': create_user_id,
                    'create_user_name': create_user_name,
                    'create_date': datetime.now(),
                    
                    # 'subjection_id': dept.get("subjectionId", ""),
                    # 'subjection_name': dept.get("subjectionName", ""),
                    # 'title_category_id': '1',
                    'title_category_name': question_type,
                    'dept_type_id': dept_id,
                    'dept_type_name': dept_name,
                    'subjects': title,
                    'plan_A': option_a,
                    'plan_B': option_b,
                    'plan_C': option_c,
                    'plan_D': option_d,
                    'plan_E': option_e,
                    'plan_F': option_f,
                    # 'options': options_str,
                    # 'options_content': options_content,
                    'answer': answer,
                    'analysis': analysis,
                    'content': content,
                    # 'content_text': content_text,
                    # 'illustrate': '',
                    # 'type': question_type
                }
                
                # 把字典转换成元组，直接插入
                fields = list(insert_data.keys())
                values = list(insert_data.values())
                placeholders = ", ".join(["%s"] * len(fields))
                
                sql = f"""
                    INSERT INTO study_dept_bank_manage (
                        {", ".join(fields)}
                    ) VALUES (
                        {placeholders}
                    )
                """
                
                cursor.execute(sql, tuple(values))

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