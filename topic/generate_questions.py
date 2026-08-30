# ============================================================
# generate_questions.py
# AI法规出题模块
#
# 职责：
# 1. 读取法规知识库
# 2. 调用AI
# 3. 生成题目
# 4. 验证题目
# 5. 保存JSON题库
#
# 不负责：
# 1. AI配置
# 2. AI模型选择
# 3. Excel导出
#
# AI配置统一由：
#
#     ai_config.py
#
# AI调用统一由：
#
#     ai_client.py
#
# ============================================================

import json
import random
import re
import uuid  # ✅ 新增：导入uuid
from pathlib import Path

import ai_client


# ============================================================
# 1. 项目根目录
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent


# ============================================================
# 2. 法规知识库
# ============================================================

ARTICLES_FILE = (
    BASE_DIR
    / "data"
    / "articles.json"
)


# ============================================================
# 3. JSON题库目录
# ============================================================

QUESTIONS_DIR = (
    BASE_DIR
    / "questions"
)


# ============================================================
# 4. 分组
# ============================================================

GROUP_NAME = "煤矿"

CATEGORY_NAME = "法规"


# ============================================================
# 5. AI最大重试次数
# ============================================================

MAX_RETRY = 3


# ============================================================
# 6. 创建题库目录
# ============================================================

QUESTIONS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 7. 标准化题型
# ============================================================

def normalize_question_type(question_type):

    if question_type is None:
        return None

    value = str(
        question_type
    ).strip()

    if not value:
        return None

    mapping = {

        "判断": "判断题",
        "判断题": "判断题",
        "judge": "判断题",
        "truefalse": "判断题",
        "true_false": "判断题",

        "单选": "单选题",
        "单选题": "单选题",
        "single": "单选题",
        "single_choice": "单选题",

        "多选": "多选题",
        "多选题": "多选题",
        "multiple": "多选题",
        "multiple_choice": "多选题"
    }

    return mapping.get(
        value.lower()
    )


# ============================================================
# 8. 标准化题目数量
# ============================================================

def normalize_count(count):

    if count is None:

        raise ValueError(
            "网页没有传入题目数量 count"
        )

    value = str(
        count
    ).strip()

    if not value:

        raise ValueError(
            "网页传入的题目数量为空"
        )

    try:

        number = int(value)

    except Exception:

        raise ValueError(
            f"题目数量无效：{count}"
        )

    if number <= 0:

        raise ValueError(
            "题目数量必须大于0"
        )

    if number > 100:

        raise ValueError(
            "一次最多生成100道题"
        )

    return number


# ============================================================
# 9. 获取题库文件
# ============================================================

def get_question_file(law_name, use_new=False):

    safe_name = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        str(law_name)
    )

    if use_new:
        filename = f"{safe_name}_new.json"
    else:
        filename = f"{safe_name}.json"

    return (
        QUESTIONS_DIR
        / filename
    )


# ============================================================
# 10. Prompt
# ============================================================

def build_prompt(
    article,
    content,
    question_type
):

    prompt = f"""
你是一名专业的法律法规考试出题专家。

请严格根据下面提供的法规原文生成1道考试题。

==================================================
【法规条文】
==================================================
{article}

==================================================
【法规原文】
==================================================
{content}

==================================================
【本题指定题型】
==================================================

本题必须生成：

{question_type}

【非常重要】

你只能生成：

{question_type}

绝对禁止生成其他题型。

==================================================
【判断题要求】
==================================================

如果本题是判断题：

plan_a必须填写：

正确

plan_b必须填写：

错误

plan_c必须为空。

plan_d必须为空。

plan_e必须为空。

plan_f必须为空。

answer只能是：

A

或者：

B

==================================================
【单选题要求】
==================================================

如果本题是单选题：

必须有：

plan_a
plan_b
plan_c
plan_d

四个选项。

plan_e必须为空。

plan_f必须为空。

必须只有一个正确答案。

answer只能是：

A
B
C
D

==================================================
【多选题要求】
==================================================

如果本题是多选题：

至少生成3个有效选项。

可以使用：

A
B
C
D
E
F

必须至少有2个正确答案。

答案格式必须是：

A,B

或者：

A,C,D

或者：

A,B,D,E

必须使用英文逗号。

不要使用：

ABC

不要使用：

A、B、C

==================================================
【所有题型共同要求】
==================================================

1. 只能生成1道题。
2. 必须严格依据法规原文。
3. 不允许编造法规原文没有出现的规定。
4. 题目必须具有考试价值。
5. 选项之间不能重复。
6. 解析必须严格依据法规原文。
7. 解析必须只写一句话。
8. 解析控制在20～40字以内。
9. 直接说明正确答案的法律依据。
10. 禁止分段。
11. 禁止列举。
12. 禁止重复题目内容。
13. 禁止输出长篇解释。
14. 不要输出思考过程。
15. 不要输出Thinking。
16. 不要输出Markdown。
17. 最终只能输出JSON。

==================================================
【JSON格式】
==================================================

{{
    "title_category_name": "{question_type}",
    "subjects": "题目",
    "plan_a": "选项A",
    "plan_b": "选项B",
    "plan_c": "选项C",
    "plan_d": "选项D",
    "plan_e": "选项E",
    "plan_f": "选项F",
    "analysis": "一句话法律依据解析",
    "answer": "A"
}}

==================================================
【最终强制要求】
==================================================

title_category_name必须严格等于：

{question_type}

只输出JSON。
"""

    return prompt


# ============================================================
# 11. 调用AI
# ============================================================

def ask_ai(
    article,
    content,
    question_type
):

    prompt = build_prompt(
        article,
        content,
        question_type
    )

    return ai_client.generate(
        prompt
    )


# ============================================================
# 12. 清理AI JSON
# ============================================================

def clean_ai_json(text):

    text = str(
        text
    ).strip()

    # --------------------------------------------------------
    # 去掉Markdown代码块
    # --------------------------------------------------------

    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

    return text.strip()


# ============================================================
# 13. 验证题目（✅ 已添加ID生成）
# ============================================================

def validate_question(
    text,
    article,
    expected_type
):

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:

        text = clean_ai_json(
            text
        )

        question = json.loads(
            text
        )

    except json.JSONDecodeError:

        print(
            "❌ AI返回内容不是合法JSON"
        )

        print(text)

        return None

    except Exception as e:

        print(
            f"❌ AI返回结果处理失败：{e}"
        )

        return None

    # --------------------------------------------------------
    # 必须字段
    # --------------------------------------------------------

    required_fields = [

        "title_category_name",
        "subjects",

        "plan_a",
        "plan_b",
        "plan_c",
        "plan_d",

        "analysis",
        "answer"
    ]

    for field in required_fields:

        if field not in question:

            print(
                f"❌ 缺少字段：{field}"
            )

            return None

    # --------------------------------------------------------
    # E/F
    # --------------------------------------------------------

    if "plan_e" not in question:

        question["plan_e"] = ""

    if "plan_f" not in question:

        question["plan_f"] = ""

    # --------------------------------------------------------
    # 字符串统一
    # --------------------------------------------------------

    for field in [

        "subjects",
        "plan_a",
        "plan_b",
        "plan_c",
        "plan_d",
        "plan_e",
        "plan_f",
        "analysis"
    ]:

        question[field] = str(
            question[field]
        ).strip()

    # --------------------------------------------------------
    # 题型
    # --------------------------------------------------------

    category = str(
        question[
            "title_category_name"
        ]
    ).strip()

    # --------------------------------------------------------
    # 题型必须完全一致
    # --------------------------------------------------------

    if category != expected_type:

        print()
        print(
            "❌❌❌ AI题型错误"
        )

        print(
            f"网页指定题型：{expected_type}"
        )

        print(
            f"AI实际题型：{category}"
        )

        return None

    # --------------------------------------------------------
    # 题目
    # --------------------------------------------------------

    if not question["subjects"]:

        print(
            "❌ 题目为空"
        )

        return None

    # --------------------------------------------------------
    # 解析
    # --------------------------------------------------------

    if not question["analysis"]:

        print(
            "❌ 解析为空"
        )

        return None

    # ========================================================
    # 判断题
    # ========================================================

    if category == "判断题":

        question["plan_a"] = "正确"
        question["plan_b"] = "错误"

        question["plan_c"] = ""
        question["plan_d"] = ""
        question["plan_e"] = ""
        question["plan_f"] = ""

        answer = str(
            question["answer"]
        ).strip().upper()

        if answer not in (
            "A",
            "B"
        ):

            print(
                "❌ 判断题答案必须是A或B"
            )

            return None

        question["answer"] = answer

    # ========================================================
    # 单选题
    # ========================================================

    elif category == "单选题":

        options = [

            question["plan_a"],
            question["plan_b"],
            question["plan_c"],
            question["plan_d"]
        ]

        if any(
            not option
            for option in options
        ):

            print(
                "❌ 单选题必须有A-D四个选项"
            )

            return None

        if len(
            set(options)
        ) != 4:

            print(
                "❌ 单选题存在重复选项"
            )

            return None

        question["plan_e"] = ""
        question["plan_f"] = ""

        answer = str(
            question["answer"]
        ).strip().upper()

        if answer not in (
            "A",
            "B",
            "C",
            "D"
        ):

            print(
                "❌ 单选题答案必须是A-D"
            )

            return None

        question["answer"] = answer

    # ========================================================
    # 多选题
    # ========================================================

    elif category == "多选题":

        options = [

            question["plan_a"],
            question["plan_b"],
            question["plan_c"],
            question["plan_d"],
            question["plan_e"],
            question["plan_f"]
        ]

        valid_options = [

            option
            for option in options
            if option
        ]

        # ----------------------------------------------------
        # 至少3个
        # ----------------------------------------------------

        if len(valid_options) < 3:

            print(
                "❌ 多选题至少需要三个有效选项"
            )

            return None

        # ----------------------------------------------------
        # 不能重复
        # ----------------------------------------------------

        if len(valid_options) != len(
            set(valid_options)
        ):

            print(
                "❌ 多选题存在重复选项"
            )

            return None

        # ----------------------------------------------------
        # 答案
        # ----------------------------------------------------

        answer = str(
            question["answer"]
        ).strip().upper()

        answer = answer.replace(
            "，",
            ","
        )

        answer = answer.replace(
            "、",
            ","
        )

        answer = answer.replace(
            " ",
            ""
        )

        answer_list = [

            x.strip()
            for x in answer.split(",")
            if x.strip()
        ]

        # ----------------------------------------------------
        # 至少两个答案
        # ----------------------------------------------------

        if len(answer_list) < 2:

            print(
                "❌ 多选题至少需要两个正确答案"
            )

            return None

        # ----------------------------------------------------
        # 合法字母
        # ----------------------------------------------------

        valid_letters = [

            "A",
            "B",
            "C",
            "D",
            "E",
            "F"
        ]

        for answer_item in answer_list:

            if answer_item not in valid_letters:

                print(
                    f"❌ 多选题答案非法："
                    f"{answer_item}"
                )

                return None

        # ----------------------------------------------------
        # 去重
        # ----------------------------------------------------

        answer_list = list(
            dict.fromkeys(
                answer_list
            )
        )

        # ----------------------------------------------------
        # 选项映射
        # ----------------------------------------------------

        option_map = {

            "A": question["plan_a"],
            "B": question["plan_b"],
            "C": question["plan_c"],
            "D": question["plan_d"],
            "E": question["plan_e"],
            "F": question["plan_f"]
        }

        # ----------------------------------------------------
        # 答案必须对应有效选项
        # ----------------------------------------------------

        for answer_item in answer_list:

            if not option_map.get(
                answer_item
            ):

                print(
                    f"❌ 多选题答案"
                    f"{answer_item}"
                    f"没有对应选项"
                )

                return None

        question["answer"] = ",".join(
            answer_list
        )

    else:

        print(
            f"❌ 不支持的题型：{category}"
        )

        return None

    # --------------------------------------------------------
    # 保存法规条文
    # --------------------------------------------------------

    question["article"] = article

    # ✅ 新增：生成唯一ID
    if "id" not in question:
        question["id"] = str(uuid.uuid4())

    return question


# ============================================================
# 14. 生成一道题
# ============================================================

def generate_one_question(
    article,
    content,
    question_type
):

    for retry in range(
        1,
        MAX_RETRY + 1
    ):

        print()

        print(
            f"AI生成中……"
            f"题型：{question_type}"
            f" 第{retry}/{MAX_RETRY}次"
        )

        try:

            raw_result = ask_ai(
                article,
                content,
                question_type
            )

            question = validate_question(
                raw_result,
                article,
                question_type
            )

            if question:

                print(
                    f"✅ {question_type}生成成功"
                )

                return question

        except Exception as e:

            print(
                f"❌ AI调用失败：{e}"
            )

        if retry < MAX_RETRY:

            print(
                "正在重新生成……"
            )

    print(
        f"❌ {question_type}"
        f"连续生成失败"
    )

    return None


# ============================================================
# 15. 题型计划
# ============================================================

def create_question_type_plan(
    count,
    question_type=None
):

    # --------------------------------------------------------
    # 指定题型
    # --------------------------------------------------------

    if question_type in (

        "判断题",
        "单选题",
        "多选题"
    ):

        plan = [

            question_type
            for _ in range(count)
        ]

        print()

        print(
            "🔒 已锁定网页指定题型："
            f"{question_type}"
        )

        return plan

    # --------------------------------------------------------
    # 自动混合
    # --------------------------------------------------------

    types = [

        "判断题",
        "单选题",
        "多选题"
    ]

    plan = []

    for i in range(count):

        plan.append(
            types[i % 3]
        )

    random.shuffle(plan)

    return plan


# ============================================================
# 16. 主程序
# ============================================================

def main(
    question_type=None,
    count=None
):

    print()
    print(
        "===================================="
    )

    print(
        "       法规 AI 出题系统"
    )

    print(
        "===================================="
    )

    # ========================================================
    # 网页参数
    # ========================================================

    print()

    print(
        "========== 网页传入参数 =========="
    )

    print(
        f"question_type = {question_type!r}"
    )

    print(
        f"count         = {count!r}"
    )

    print(
        "=================================="
    )

    # ========================================================
    # 题数
    # ========================================================

    try:

        count = normalize_count(
            count
        )

    except Exception as e:

        print(
            f"❌ {e}"
        )

        return {

            "success": False,
            "message": str(e),
            "count": 0
        }

    # ========================================================
    # 题型
    # ========================================================

    original_question_type = (
        question_type
    )

    question_type = (
        normalize_question_type(
            question_type
        )
    )

    print()

    print(
        "========== 参数标准化 =========="
    )

    print(
        f"原始题型："
        f"{original_question_type!r}"
    )

    print(
        f"标准题型："
        f"{question_type!r}"
    )

    print(
        f"标准题数：{count}"
    )

    print(
        "================================"
    )

    # ========================================================
    # 无法识别题型
    # ========================================================

    if (

        original_question_type is not None

        and str(
            original_question_type
        ).strip()

        and question_type is None
    ):

        message = (

            "网页传入了无法识别的题型："
            f"{original_question_type}"
        )

        print(
            f"❌ {message}"
        )

        return {

            "success": False,
            "message": message,
            "count": 0
        }

    # ========================================================
    # 显示当前AI配置
    #
    # 注意：
    # generate_questions.py不修改AI配置。
    # ========================================================

    try:

        current_provider = (
            ai_client.get_ai_type()
        )

        current_model = (
            ai_client.get_ai_model()
        )

        print()

        print(
            "========== 当前AI =========="
        )

        print(
            f"Provider：{current_provider}"
        )

        print(
            f"Model   ：{current_model}"
        )

        print(
            "============================"
        )

    except Exception as e:

        print(
            f"⚠️ 获取AI配置失败：{e}"
        )

    # ========================================================
    # 显示题型
    # ========================================================

    if question_type:

        print(
            f"🔒 题型：{question_type}"
        )

    else:

        print(
            "题型：自动混合"
        )

    print(
        f"题目数量：{count}"
    )

    # ========================================================
    # 法规文件
    # ========================================================

    if not ARTICLES_FILE.exists():

        print()

        print(
            "❌ 找不到法规文件："
        )

        print(
            ARTICLES_FILE.resolve()
        )

        return {

            "success": False,
            "message": "找不到法规知识库",
            "count": 0
        }

    # ========================================================
    # 读取法规
    # ========================================================

    try:

        with open(
            ARTICLES_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            articles = json.load(f)

    except Exception as e:

        print(
            f"❌ 法规JSON读取失败：{e}"
        )

        return {

            "success": False,

            "message":
                f"法规JSON读取失败：{e}",

            "count": 0
        }

    # ========================================================
    # 格式检查
    # ========================================================

    if not isinstance(
        articles,
        list
    ):

        print(
            "❌ 法规JSON格式错误，必须是数组"
        )

        return {

            "success": False,

            "message":
                "法规JSON格式错误，必须是数组",

            "count": 0
        }

    print()

    print(
        f"知识库总记录数："
        f"{len(articles)}"
    )

    # ========================================================
    # 法规名称
    # ========================================================

    law_names = {

        item.get("law_name")

        for item in articles

        if isinstance(item, dict)

        and item.get("law_name")
    }

    if law_names:

        law_name = list(
            law_names
        )[0]

    else:

        law_name = "法规"

    print(
        f"当前法规：{law_name}"
    )

    # ========================================================
    # 可出题条文
    # ========================================================

    article_list = [

        item

        for item in articles

        if isinstance(item, dict)

        and item.get("type") == "article"

        and item.get("article")

        and item.get("content")
    ]

    print()

    print(
        f"可用于出题的法规条文："
        f"{len(article_list)} 条"
    )

    if not article_list:

        print(
            "❌ 没有找到可用于出题的法规条文"
        )

        return {

            "success": False,

            "message":
                "没有找到可用于出题的法规条文",

            "count": 0
        }

    # ========================================================
    # JSON题库
    # ========================================================

    # 使用 _new 后缀，只存本次新题
    new_questions_file = get_question_file(
        law_name,
        use_new=True
    )

    # 历史题库文件（不带 _new）
    history_file = get_question_file(
        law_name,
        use_new=False
    )

    print()

    print(
        "本次新题JSON："
    )

    print(
        new_questions_file.resolve()
    )

    print()

    print(
        "历史题库JSON："
    )

    print(
        history_file.resolve()
    )

    # ========================================================
    # 题型计划
    # ========================================================

    question_type_plan = (
        create_question_type_plan(
            count,
            question_type
        )
    )

    print()

    print(
        "===================================="
    )

    print(
        "本次题型安排："
    )

    for i, current_type in enumerate(
        question_type_plan,
        start=1
    ):

        print(
            f"第{i}题："
            f"{current_type}"
        )

    print(
        "===================================="
    )

    # ========================================================
    # 读取历史题库
    # ========================================================

    history_questions = []

    if history_file.exists():

        try:

            with open(
                history_file,
                "r",
                encoding="utf-8"
            ) as f:

                history_questions = json.load(f)

            if not isinstance(
                history_questions,
                list
            ):

                history_questions = []

        except Exception:

            print(
                "⚠️ 历史题库读取失败，"
                "将创建新的历史题库。"
            )

            history_questions = []

    print()

    print(
        f"当前法规已有历史题目："
        f"{len(history_questions)} 道"
    )

    # ========================================================
    # 去重
    # ========================================================

    used_questions = {

        (
            item.get("article"),
            item.get("title_category_name")
        )

        for item in history_questions

        if isinstance(item, dict)

        and item.get("article")

        and item.get(
            "title_category_name"
        )
    }

    print(
        "已经使用过的"
        "法规条文+题型组合："
        f"{len(used_questions)} 个"
    )

    # ========================================================
    # 临时失败集合
    # ========================================================

    failed_questions = set()

    # ========================================================
    # 开始生成
    # ========================================================

    success_count = 0

    # 新生成的题单独放
    new_questions = []

    while success_count < count:

        current_type = (
            question_type_plan[
                success_count
            ]
        )

        # ----------------------------------------------------
        # 找可用法规（排除历史已有和本次失败的）
        # ----------------------------------------------------

        available = [

            item

            for item in article_list

            if (

                (
                    item.get("article"),
                    current_type
                )

                not in used_questions

            )

            and (

                (
                    item.get("article"),
                    current_type
                )

                not in failed_questions

            )
        ]

        # ----------------------------------------------------
        # 没有可用法规
        # ----------------------------------------------------

        if not available:

            print()

            print(
                "⚠️ 当前题型没有更多"
                "可用法规条文。"
            )

            print(
                f"当前题型：{current_type}"
            )

            print(
                "无法继续生成该题型。"
            )

            break

        # ----------------------------------------------------
        # 随机法规
        # ----------------------------------------------------

        item = random.choice(
            available
        )

        article = item.get(
            "article",
            ""
        )

        content = item.get(
            "content",
            ""
        )

        # ----------------------------------------------------
        # 当前组合
        # ----------------------------------------------------

        current_key = (
            article,
            current_type
        )

        print()

        print(
            "===================================="
        )

        print(
            f"正在生成第"
            f"{success_count + 1}/{count}道题"
        )

        print()

        print(
            f"指定题型：{current_type}"
        )

        print()

        print(
            f"法规：{article}"
        )

        print(
            "===================================="
        )

        # ====================================================
        # 生成
        # ====================================================

        question = generate_one_question(
            article,
            content,
            current_type
        )

        # ----------------------------------------------------
        # AI生成失败
        # ----------------------------------------------------

        if question is None:

            failed_questions.add(
                current_key
            )

            print(
                "⚠️ 本条法规+题型"
                "本次生成失败，"
                "暂时跳过。"
            )

            continue

        # ====================================================
        # 再次强制检查
        # ====================================================

        if question.get(
            "title_category_name"
        ) != current_type:

            print()

            print(
                "❌❌❌ 严重错误"
            )

            print(
                f"计划题型：{current_type}"
            )

            print(
                "实际题型："
                f"{question.get('title_category_name')}"
            )

            failed_questions.add(
                current_key
            )

            continue

        # ====================================================
        # 保存到新题列表
        # ====================================================

        new_questions.append(
            question
        )

        used_questions.add(
            current_key
        )

        success_count += 1

        # ====================================================
        # 显示题目
        # ====================================================

        print()

        print(
            "------------------------------------"
        )

        print(
            f"题型："
            f"{question['title_category_name']}"
        )

        print(
            f"题目："
            f"{question['subjects']}"
        )

        print(
            f"A："
            f"{question['plan_a']}"
        )

        print(
            f"B："
            f"{question['plan_b']}"
        )

        print(
            f"C："
            f"{question['plan_c']}"
        )

        print(
            f"D："
            f"{question['plan_d']}"
        )

        print(
            f"E："
            f"{question['plan_e']}"
        )

        print(
            f"F："
            f"{question['plan_f']}"
        )

        print(
            f"正确答案："
            f"{question['answer']}"
        )

        print(
            f"解析："
            f"{question['analysis']}"
        )

        print(
            f"ID："
            f"{question.get('id', '无ID')}"
        )

        print(
            "------------------------------------"
        )

        # ====================================================
        # 保存 _new.json（只存本次新题，覆盖）
        # ====================================================

        try:

            with open(
                new_questions_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    new_questions,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        except Exception as e:

            print(
                f"❌ _new.json保存失败：{e}"
            )

            return {

                "success": False,

                "message":
                    f"_new.json保存失败：{e}",

                "count":
                    success_count,

                "questions":
                    new_questions,

                "json_file":
                    str(
                        new_questions_file.resolve()
                    )
            }

        print()

        print(
            f"💾 _new.json已保存："
            f"{new_questions_file.resolve()}"
        )

    # ========================================================
    # while 循环结束（所有题目已生成完成）
    # ========================================================

    # ========================================================
    # 统一追加到历史题库（只追加一次）
    # ========================================================

    if new_questions:

        try:

            # 读取历史题库
            current_history = []

            if history_file.exists():

                try:

                    with open(
                        history_file,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        current_history = json.load(f)

                        if not isinstance(
                            current_history,
                            list
                        ):

                            current_history = []

                except Exception:

                    current_history = []

            # 追加新题（只追加一次）
            current_history.extend(
                new_questions
            )

            # 保存历史题库
            with open(
                history_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    current_history,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            print()
            print(
                f"💾 历史题库已追加："
                f"{history_file.resolve()}"
            )

            print(
                f"   历史题库现有："
                f"{len(current_history)} 道"
            )

        except Exception as e:

            print(
                f"❌ 历史题库追加失败：{e}"
            )

            return {

                "success": False,

                "message":
                    f"历史题库追加失败：{e}",

                "count":
                    success_count,

                "questions":
                    new_questions,

                "json_file":
                    str(
                        new_questions_file.resolve()
                    )
            }

    # ========================================================
    # 最终结果
    # ========================================================

    print()

    print(
        "===================================="
    )

    print(
        "             出题完成"
    )

    print(
        "===================================="
    )

    print()

    print(
        f"本次成功生成："
        f"{success_count} 道"
    )

    print(
        f"历史题库总数量："
        f"{len(history_questions) + success_count} 道"
    )

    print(
        f"本次新题数量："
        f"{len(new_questions)} 道"
    )

    print()

    print(
        "📦 历史题库位置："
    )

    print(
        history_file.resolve()
    )

    print()

    print(
        "📦 本次新题位置："
    )

    print(
        new_questions_file.resolve()
    )

    print()

    print(
        "===================================="
    )

    # ========================================================
    # 返回
    # ========================================================

    return {

        "success": True,

        "message": (
            "AI题目生成完成，"
            f"本次成功生成"
            f"{success_count}道"
        ),

        "count":
            success_count,

        "history_count":
            len(history_questions) + success_count,

        "new_count":
            len(new_questions),

        "history_file":
            str(
                history_file.resolve()
            ),

        "json_file":
            str(
                new_questions_file.resolve()
            ),

        "questions":
            new_questions
    }


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":

    print(
        "generate_questions.py"
    )

    print(
        "现在只负责AI出题和JSON保存。"
    )

    print(
        "AI模型由config/ai_config.json统一决定。"
    )

    print()

    # --------------------------------------------------------
    # 本地直接测试
    # --------------------------------------------------------

    result = main(
        question_type="判断题",
        count=1
    )

    print()

    print(
        "测试结果："
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )