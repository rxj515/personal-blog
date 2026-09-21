# ============================================================
# generate_questions.py
# AI法规出题模块（多维度标签 + 一条法规多考点版本）
#
# 职责：
# 1. 读取法规知识库
# 2. 拆解法条为多个考点
# 3. 调用AI生成题目
# 4. 验证题目
# 5. 保存JSON题库
#
# 不负责：
# 1. AI配置
# 2. AI模型选择
# 3. Excel导出
#
# AI配置统一由：
#     ai_config.py
#
# AI调用统一由：
#     ai_client.py
#
# ============================================================

import json
import random
import re
import uuid
import hashlib
from pathlib import Path

import ai_client


# ============================================================
# 1. 项目根目录
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent


# ============================================================
# 2. 法规知识库目录
# ============================================================

KNOWLEDGE_DIR = (
    BASE_DIR
    / "data"
    / "knowledge"
)

ARTICLES_FILE = KNOWLEDGE_DIR


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
# 5.1 ✅ 单条法条最多拆解出的考点数（按长度动态决定）
# ============================================================

MAX_POINTS_PER_ARTICLE = 15   # 兜底上限


def get_max_points_by_length(content):
    """
    根据法条字数，动态决定最多拆几个考点。

    < 200 字   → 3
    < 500 字   → 5
    < 1500 字  → 8
    < 3000 字  → 12
    >= 3000 字 → 15
    """
    length = len(content or "")

    if length < 200:
        return 3
    elif length < 500:
        return 5
    elif length < 1500:
        return 8
    elif length < 3000:
        return 12
    else:
        return 15


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
# 9.1 考点归一化（用于稳定去重）
# ============================================================

def normalize_point(point):
    """
    对考点文本做归一化，避免AI措辞不同导致去重失效。
    """
    p = str(point or "").strip()

    p = re.sub(
        r"[\s，。、；：！？,.;:!?（）()【】\[\]「」『』\"'`]",
        "",
        p
    )

    return p.lower()


def point_hash(point):
    """
    把归一化后的考点转成稳定的短hash。
    """
    normalized = normalize_point(point)

    if not normalized:
        return "__whole__"

    return hashlib.md5(
        normalized.encode("utf-8")
    ).hexdigest()[:12]


# ============================================================
# 9.2 严格模式：按树节点过滤法条（不回退）
# ============================================================

def match_node(item, node_name):
    """
    判断一条法条的 dept_type_name 是否包含指定节点名。
    严格模式：没有标签 = 不匹配
    """
    types = item.get("dept_type_name")

    if types is None or types == "":
        return False

    if isinstance(types, str):
        types = [t.strip() for t in types.split(",") if t.strip()]

    if not isinstance(types, list) or not types:
        return False

    return node_name in types


def filter_articles_by_node(article_list, node_name=None, superior_name=None):
    """
    严格按节点过滤，不回退。
    匹配不到返回空列表。
    """
    if not node_name:
        print(
            f"ℹ️ 未指定节点，使用全部 "
            f"{len(article_list)} 条法条"
        )
        return article_list

    filtered = [
        item for item in article_list
        if match_node(item, node_name)
    ]

    if not filtered:
        print(f"⚠️ 节点 [{node_name}] 没有可用法条")
        return []

    print(
        f"✅ 节点 [{node_name}] 匹配到 "
        f"{len(filtered)} 条法条"
    )
    return filtered


# ============================================================
# 9.3 加载知识库
# ============================================================

def load_articles(knowledge_name=None):
    """
    从 data/knowledge/ 加载 articles.json。
    - 指定 knowledge_name：加载对应目录
    - 未指定：合并所有知识库
    返回 (articles, law_name)
    """
    if not KNOWLEDGE_DIR.exists():
        print(f"❌ 知识库目录不存在：{KNOWLEDGE_DIR}")
        return [], "法规"

    if knowledge_name:
        target = KNOWLEDGE_DIR / knowledge_name / "articles.json"
        if not target.exists():
            print(f"❌ 找不到知识库：{target}")
            return [], "法规"

        with open(target, "r", encoding="utf-8") as f:
            articles = json.load(f)

        print(f"📄 加载知识库：{knowledge_name}")
        return articles, knowledge_name

    # 未指定：合并所有
    all_articles = []
    for dir_path in sorted(KNOWLEDGE_DIR.iterdir()):
        if not dir_path.is_dir():
            continue

        json_file = dir_path / "articles.json"
        if not json_file.exists():
            continue

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                all_articles.extend(data)
        except Exception as e:
            print(f"⚠️ 读取 {json_file} 失败：{e}")

    print(f"📄 合并加载全部知识库，共 {len(all_articles)} 条")
    return all_articles, "全部法规"


# ============================================================
# 10. 出题Prompt（支持聚焦考点）
# ============================================================

def build_prompt(
    article,
    content,
    question_type,
    point=None,
    detail=None
):

    if point:

        focus_block = f"""
==================================================
【本题聚焦考点】
==================================================
{point}

==================================================
【该考点对应原文】
==================================================
{detail or content}

==================================================
【聚焦要求（非常重要）】
==================================================
本题只能围绕"本题聚焦考点"出题。
禁止涉及该法条中与本考点无关的其他规定。
"""

    else:

        focus_block = ""

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
{focus_block}
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

plan_a必须填写：正确

plan_b必须填写：错误

plan_c必须为空。

plan_d必须为空。

plan_e必须为空。

plan_f必须为空。

answer只能是：A 或者 B

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

answer只能是：A B C D

==================================================
【多选题要求】
==================================================

如果本题是多选题：

至少生成3个有效选项。

可以使用：A B C D E F

必须至少有2个正确答案。

答案格式必须是：

A,B

或者：

A,C,D

必须使用英文逗号。

不要使用：ABC

不要使用：A、B、C

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
# 11. 调用AI（支持考点）
# ============================================================

def ask_ai(
    article,
    content,
    question_type,
    point=None,
    detail=None
):

    prompt = build_prompt(
        article,
        content,
        question_type,
        point,
        detail
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
# 13. 验证题目（新增 point 字段保存）
# ============================================================

def validate_question(
    text,
    article,
    expected_type,
    point=None
):

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

    if "plan_e" not in question:

        question["plan_e"] = ""

    if "plan_f" not in question:

        question["plan_f"] = ""

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

    category = str(
        question[
            "title_category_name"
        ]
    ).strip()

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

    if not question["subjects"]:

        print(
            "❌ 题目为空"
        )

        return None

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

        if len(valid_options) < 3:

            print(
                "❌ 多选题至少需要三个有效选项"
            )

            return None

        if len(valid_options) != len(
            set(valid_options)
        ):

            print(
                "❌ 多选题存在重复选项"
            )

            return None

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

        if len(answer_list) < 2:

            print(
                "❌ 多选题至少需要两个正确答案"
            )

            return None

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

        answer_list = list(
            dict.fromkeys(
                answer_list
            )
        )

        option_map = {

            "A": question["plan_a"],
            "B": question["plan_b"],
            "C": question["plan_c"],
            "D": question["plan_d"],
            "E": question["plan_e"],
            "F": question["plan_f"]
        }

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

    question["article"] = article

    question["point"] = str(point or "").strip()
    question["point_hash"] = point_hash(point)

    question["dept_id"] = ""
    question["dept_name"] = ""
    question["superior_name"] = ""
    question["dept_type_name"] = ""

    if "id" not in question:
        question["id"] = str(uuid.uuid4())

    return question


# ============================================================
# 14. 生成一道题（支持考点）
# ============================================================

def generate_one_question(
    article,
    content,
    question_type,
    dept_info=None,
    point=None,
    detail=None
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

        if point:
            print(f"  考点：{point}")

        try:

            raw_result = ask_ai(
                article,
                content,
                question_type,
                point,
                detail
            )

            question = validate_question(
                raw_result,
                article,
                question_type,
                point
            )

            if question and dept_info:

                question["dept_id"] = dept_info.get("id", "")

                question["dept_name"] = dept_info.get("fullName", "")

                question["superior_name"] = dept_info.get("superiorName", "")

                question["dept_type_name"] = dept_info.get("category", "")

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
# 16. 法条拆解为多个考点
# ============================================================

def build_split_prompt(article, content, max_points=8):

    prompt = f"""
你是一名法律法规考试出题专家。

请把下面这条法规拆解成若干个"独立考点"。

==================================================
【法规条文】
==================================================
{article}

==================================================
【法规原文】
==================================================
{content}

==================================================
【拆解要求】
==================================================

1. 每个考点必须是法规原文中一个独立、完整、可单独出题的规定。
2. 一个考点只对应一个法律要求，不要把多个规定混在一起。
3. 如果原文包含"严禁A、严禁B、严禁C"，A/B/C应拆成3个考点。
4. 如果原文有"必须X、禁止Y"，X和Y是两个考点。
5. 如果原文是"禁止...，但...除外"，把这个例外也作为一个独立考点。
6. 最多拆解出 {max_points} 个考点，至少1个。
7. 每个考点用一句话概括，不超过30字，不要直接抄原文。
8. 只输出JSON数组，不要输出其他任何内容。
9. 不要输出Markdown代码块。

==================================================
【JSON格式】
==================================================

[
    {{
        "point": "考点简述（不超过30字）",
        "detail": "该考点对应的法规原文片段"
    }}
]

只输出JSON数组。
"""

    return prompt


def split_article_into_points(
    article,
    content,
    max_points=None
):
    """
    调用AI把一条法条拆解成多个考点。
    max_points 为 None 时，按法条长度自动决定（见 get_max_points_by_length）。
    返回 list[dict]，每个 dict 含 point / detail。
    失败返回 []（调用方应降级为整条作为一个考点）。
    """

    # ✅ 按长度自动决定
    if max_points is None:
        max_points = get_max_points_by_length(content)

    prompt = build_split_prompt(
        article,
        content,
        max_points
    )

    try:

        raw = ai_client.generate(prompt)

        raw = clean_ai_json(raw)

        points = json.loads(raw)

        if not isinstance(points, list):

            print(
                "⚠️ 拆解结果不是数组，降级为整条法条"
            )

            return []

        valid = []

        seen_hashes = set()

        for p in points:

            if not isinstance(p, dict):
                continue

            point = str(
                p.get("point", "")
            ).strip()

            detail = str(
                p.get("detail", "")
            ).strip()

            if not point:
                continue

            h = point_hash(point)

            if h in seen_hashes:
                continue

            seen_hashes.add(h)

            valid.append({
                "point": point,
                "detail": detail or content
            })

        return valid[:max_points]

    except Exception as e:

        print(
            f"❌ 法条拆解失败：{e}"
        )

        return []


# ============================================================
# 17. 主程序
# ============================================================

def main(
    question_type=None,
    count=None,
    knowledge_name=None,
    node_name=None,
    superior_name=None,
):

    print()
    print(
        "===================================="
    )

    print(
        "       法规 AI 出题系统（多考点版）"
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

    print(f"question_type  = {question_type!r}")
    print(f"count          = {count!r}")
    print(f"knowledge_name = {knowledge_name!r}")
    print(f"node_name      = {node_name!r}")
    print(f"superior_name  = {superior_name!r}")

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
    # AI 配置
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
    # 加载知识库
    # ========================================================

    articles, law_name = load_articles(
        knowledge_name
    )

    if not articles:

        return {

            "success": False,
            "message": "没有找到可用的法规知识库",
            "count": 0
        }

    if not isinstance(articles, list):

        return {

            "success": False,
            "message": "法规JSON格式错误，必须是数组",
            "count": 0
        }

    print()
    print(f"知识库总记录数：{len(articles)}")

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

        return {

            "success": False,
            "message": "没有找到可用于出题的法规条文",
            "count": 0
        }

    # ========================================================
    # 严格按节点过滤
    # ========================================================

    article_list = filter_articles_by_node(
        article_list,
        node_name=node_name,
        superior_name=superior_name,
    )

    if not article_list:

        return {

            "success": False,
            "message": f"节点 [{node_name}] 没有可用法条",
            "count": 0
        }

    # ========================================================
    # JSON题库
    # ========================================================

    new_questions_file = get_question_file(
        law_name,
        use_new=True
    )

    history_file = get_question_file(
        law_name,
        use_new=False
    )

    print()
    print("本次新题JSON：")
    print(new_questions_file.resolve())
    print()
    print("历史题库JSON：")
    print(history_file.resolve())

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
    print("本次题型安排：")
    for i, current_type in enumerate(
        question_type_plan,
        start=1
    ):
        print(f"第{i}题：{current_type}")
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

    used_questions = set()

    for item in history_questions:

        if not isinstance(item, dict):
            continue

        art = item.get("article")
        qtype = item.get("title_category_name")

        if not art or not qtype:
            continue

        ph = item.get("point_hash")

        if not ph:
            ph = point_hash(item.get("point", ""))

        used_questions.add((art, qtype, ph))

    print(
        "已经使用过的"
        "法规条文+题型+考点组合："
        f"{len(used_questions)} 个"
    )

    failed_questions = set()

    article_points_cache = {}

    # ========================================================
    # 开始生成
    # ========================================================

    success_count = 0
    new_questions = []

    while success_count < count:

        current_type = (
            question_type_plan[
                success_count
            ]
        )

        shuffled = article_list[:]
        random.shuffle(shuffled)

        candidate = None
        candidate_point = ""
        candidate_detail = ""

        for item in shuffled:

            art = item.get("article", "")
            content = item.get("content", "")

            if not art or not content:
                continue

            if art not in article_points_cache:

                print()
                print(
                    f"🔍 正在拆解法条 "
                    f"{art} 的考点……"
                    f"（长度 {len(content)} 字）"
                )

                # ✅ 不传 max_points，会自动按长度决定
                points = split_article_into_points(
                    art,
                    content
                )

                if not points:

                    print(
                        f"⚠️ 法条 {art} 拆解失败，"
                        f"降级为整条作为一个考点"
                    )

                    points = [{
                        "point": "",
                        "detail": content
                    }]

                else:

                    print(
                        f"✅ 法条 {art} 拆解出 "
                        f"{len(points)} 个考点："
                    )

                    for idx, p in enumerate(points, 1):
                        print(
                            f"   {idx}. {p['point']}"
                        )

                article_points_cache[art] = points

            points = article_points_cache[art]

            for p in points:

                h = point_hash(p["point"])

                key = (art, current_type, h)

                if key in used_questions:
                    continue

                if key in failed_questions:
                    continue

                candidate = item
                candidate_point = p["point"]
                candidate_detail = p["detail"]
                break

            if candidate:
                break

        if not candidate:

            print()
            print(
                "⚠️ 所有法条的可用考点已耗尽，"
                "无法继续生成。"
            )

            break

        article = candidate.get("article", "")
        content = candidate.get("content", "")

        current_key = (
            article,
            current_type,
            point_hash(candidate_point)
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
        print(f"指定题型：{current_type}")
        print()
        print(f"法规：{article}")

        if candidate_point:
            print(f"考点：{candidate_point}")

        print(
            "===================================="
        )

        question = generate_one_question(
            article,
            content,
            current_type,
            point=candidate_point,
            detail=candidate_detail
        )

        if question is None:

            failed_questions.add(
                current_key
            )

            print(
                "⚠️ 该考点本次生成失败，"
                "暂时跳过。"
            )

            continue

        if question.get(
            "title_category_name"
        ) != current_type:

            print()
            print("❌❌❌ 严重错误")
            print(f"计划题型：{current_type}")
            print(
                "实际题型："
                f"{question.get('title_category_name')}"
            )

            failed_questions.add(current_key)
            continue

        new_questions.append(question)
        used_questions.add(current_key)
        success_count += 1

        # ====================================================
        # 显示题目
        # ====================================================

        print()
        print(
            "------------------------------------"
        )
        print(f"题型：{question['title_category_name']}")
        print(f"题目：{question['subjects']}")
        print(f"A：{question['plan_a']}")
        print(f"B：{question['plan_b']}")
        print(f"C：{question['plan_c']}")
        print(f"D：{question['plan_d']}")
        print(f"E：{question['plan_e']}")
        print(f"F：{question['plan_f']}")
        print(f"正确答案：{question['answer']}")
        print(f"解析：{question['analysis']}")
        print(f"考点：{question.get('point', '')}")
        print(f"ID：{question.get('id', '无ID')}")
        print(
            "------------------------------------"
        )

        # ====================================================
        # 保存 _new.json
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
                "message": f"_new.json保存失败：{e}",
                "count": success_count,
                "questions": new_questions,
                "json_file": str(
                    new_questions_file.resolve()
                )
            }

        print()
        print(
            f"💾 _new.json已保存："
            f"{new_questions_file.resolve()}"
        )

    # ========================================================
    # 追加历史题库
    # ========================================================

    final_history_count = len(history_questions)

    if new_questions:

        try:

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

            current_history.extend(new_questions)

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

            final_history_count = len(current_history)

            print()
            print(
                f"💾 历史题库已追加："
                f"{history_file.resolve()}"
            )
            print(
                f"   历史题库现有："
                f"{final_history_count} 道"
            )

        except Exception as e:

            print(
                f"❌ 历史题库追加失败：{e}"
            )

            return {

                "success": False,
                "message": f"历史题库追加失败：{e}",
                "count": success_count,
                "questions": new_questions,
                "json_file": str(
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
    print("             出题完成")
    print(
        "===================================="
    )
    print()
    print(f"本次成功生成：{success_count} 道")
    print(f"历史题库总数量：{final_history_count} 道")
    print(f"本次新题数量：{len(new_questions)} 道")
    print()
    print("📦 历史题库位置：")
    print(history_file.resolve())
    print()
    print("📦 本次新题位置：")
    print(new_questions_file.resolve())
    print()
    print(
        "===================================="
    )

    return {

        "success": True,

        "message": (
            "AI题目生成完成，"
            f"本次成功生成{success_count}道"
        ),

        "count": success_count,

        "history_count": final_history_count,

        "new_count": len(new_questions),

        "history_file": str(
            history_file.resolve()
        ),

        "json_file": str(
            new_questions_file.resolve()
        ),

        "questions": new_questions
    }


# ============================================================
# 程序入口
# ============================================================

if __name__ == "__main__":

    print("generate_questions.py")
    print("现在支持：一条法规拆解多个考点，每个考点独立出题。")
    print("考点数按法条长度动态决定。")
    print("AI模型由config/ai_config.json统一决定。")
    print()

    # --------------------------------------------------------
    # 本地直接测试
    # --------------------------------------------------------

    result = main(
        question_type="判断题",
        count=3,
        knowledge_name="山西统筹煤炭安全新规通知",
        node_name="安全",
    )

    print()
    print("测试结果：")
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )