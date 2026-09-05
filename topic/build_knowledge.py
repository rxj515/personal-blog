# import fitz
import pymupdf
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime


# =========================================================
# 1. 项目目录配置
# =========================================================

# 当前 Python 项目目录
BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# PDF 文件夹
# =========================================================

PDF_DIR = BASE_DIR / "pdf"


# =========================================================
# ✅ 修改：知识库根目录（每个 PDF 独立存储）
# =========================================================

KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"


# =========================================================
# JSON 备份（保留，用于兼容）
# =========================================================

BACKUP_DIR = BASE_DIR / "data" / "backup"


# =========================================================
# 原始 TXT
# =========================================================

RAW_TXT_DIR = BASE_DIR / "data" / "raw_txt"


# =========================================================
# 清洗后的 TXT
# =========================================================

CLEAN_TXT_DIR = BASE_DIR / "data" / "clean_txt"


# =========================================================
# 2. 创建目录
# =========================================================

def create_directories():

    PDF_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    KNOWLEDGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    RAW_TXT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    CLEAN_TXT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================================
# 3. 安全处理文件名
# =========================================================

def safe_filename(name):

    name = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        name
    )

    name = name.strip()

    if not name:
        name = "未知法规"

    return name


# =========================================================
# 4. 自动识别法规名称
# =========================================================

def detect_law_name(doc, pdf_path):

    if len(doc) == 0:
        return pdf_path.stem

    page = doc[0]

    try:

        data = page.get_text("dict")

    except Exception:

        return pdf_path.stem

    candidates = []

    exclude_keywords = [

        "中华人民共和国",

        "人民政府",

        "国务院",

        "国家矿山安全监察局",

        "国家安全生产监督管理总局",

        "应急管理部",

        "司法部",

        "公安部",

        "住房和城乡建设部",

        "工业和信息化部",

        "交通运输部",

        "农业农村部",

        "教育部",

        "卫生健康委员会",

        "人力资源和社会保障部",

        "人力资源和社会保障厅",

        "文件",

        "发文机关",

    ]

    for block in data.get("blocks", []):

        if "lines" not in block:
            continue

        for line in block["lines"]:

            line_text_parts = []

            line_sizes = []

            line_y = None

            for span in line.get("spans", []):

                text = span.get(
                    "text",
                    ""
                ).strip()

                if not text:
                    continue

                line_text_parts.append(text)

                line_sizes.append(
                    span.get(
                        "size",
                        0
                    )
                )

                if line_y is None:

                    bbox = span.get(
                        "bbox",
                        [0, 0, 0, 0]
                    )

                    line_y = bbox[1]

            if not line_text_parts:
                continue

            text = "".join(
                line_text_parts
            ).strip()

            text = re.sub(
                r"\s+",
                "",
                text
            )

            if not text:
                continue

            if len(text) < 3:
                continue

            if len(text) > 80:
                continue

            if re.fullmatch(
                r"[0-9０-９一二三四五六七八九十百千万]+",
                text
            ):
                continue

            if re.fullmatch(
                r"[0-9０-９]{4}年"
                r"[0-9０-９]{1,2}月"
                r"[0-9０-９]{1,2}日?",
                text
            ):
                continue

            skip = False

            for keyword in exclude_keywords:

                if keyword in text:

                    skip = True
                    break

            if skip:
                continue

            if re.search(
                r"(规|办|发|函|令|公告|通知|决定)"
                r".{0,10}[0-9０-９]+号$",
                text
            ):
                continue

            if re.match(
                r"^第[一二三四五六七八九十百千万0-9]+"
                r"(编|章|节|条)",
                text
            ):
                continue

            if text in [
                "目录",
                "附件",
                "附录",
                "附则",
            ]:
                continue

            if line_sizes:

                avg_size = (
                    sum(line_sizes)
                    / len(line_sizes)
                )

            else:

                avg_size = 0

            candidates.append({

                "text": text,

                "size": avg_size,

                "y": (
                    line_y
                    if line_y is not None
                    else 0
                )

            })

    # =====================================================
    # 如果没有找到候选标题
    # =====================================================

    if not candidates:

        return pdf_path.stem

    # =====================================================
    # 给候选标题评分
    # =====================================================

    for item in candidates:

        text = item["text"]

        size = item["size"]

        y = item["y"]

        score = 0

        # 字体大小

        score += size * 5

        # 页面上方

        if y < 300:

            score += 20

        if y < 200:

            score += 10

        # 法规名称关键词

        if re.search(
            r"(法|条例|规程|规定|办法|细则|规则|标准|规范)",
            text
        ):

            score += 100

        # 常见法规名称长度

        if 4 <= len(text) <= 30:

            score += 20

        # 太长降低

        if len(text) > 40:

            score -= 20

        # 公文关键词

        if re.search(
            r"(文件|通知|公告|决定|批复|函)",
            text
        ):

            score -= 100

        item["score"] = score

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    title = candidates[0]["text"]

    title = re.sub(
        r"\s+",
        "",
        title
    )

    # =====================================================
    # 最终安全检查
    # =====================================================

    bad_patterns = [

        r"^中华人民共和国",

        r".*人民政府文件$",

        r".*政府文件$",

        r".*部文件$",

        r".*厅文件$",

    ]

    for pattern in bad_patterns:

        if re.match(
            pattern,
            title
        ):

            for candidate in candidates:

                candidate_text = candidate["text"]

                if re.search(
                    r"(法|条例|规程|规定|办法|细则|规则|标准|规范)",
                    candidate_text
                ):

                    title = candidate_text
                    break

    return title


# =========================================================
# 5. 判断法规结构
# =========================================================

def is_structure_line(line):

    line = line.strip()

    pattern = (

        r"^第\s*"
        r"[一二三四五六七八九十百千万零〇0-9]+"
        r"\s*"
        r"(编|章|节|条)"
    )

    return bool(
        re.match(
            pattern,
            line
        )
    )


# =========================================================
# 6. 判断附则
# =========================================================

def is_appendix_section(line):

    line = line.strip()

    return bool(
        re.fullmatch(
            r"附\s*则",
            line
        )
    )


# =========================================================
# 7. 判断附录
# =========================================================

def is_definitions_title(line):

    line = line.strip()

    return bool(
        re.match(
            r"^附录\s*[　 ]*主要名词解释",
            line
        )
    )


# =========================================================
# 8. 统一条文编号
# =========================================================

def normalize_article_number(text):

    match = re.match(

        r"^第\s*"
        r"([一二三四五六七八九十百千万零〇0-9]+)"
        r"\s*条",

        text
    )

    if not match:

        return None

    number = match.group(1)

    if number.isdigit():

        return f"第{number}条"

    return f"第{number}条"


# =========================================================
# 9. 判断是否为法规条文
# =========================================================

def parse_article(text):

    match = re.match(

        r"^(第\s*"
        r"[一二三四五六七八九十百千万零〇0-9]+"
        r"\s*条)",

        text
    )

    if not match:

        return None, None

    raw_article = match.group(1)

    article = normalize_article_number(
        raw_article
    )

    content = text[
        len(raw_article):
    ].strip()

    return article, content


# =========================================================
# 10. 删除页码
# =========================================================

def remove_page_number(lines):

    result = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if re.fullmatch(
            r"[—\-－_]+",
            line
        ):
            continue

        if re.fullmatch(
            r"[0-9０-９]+",
            line
        ):
            continue

        result.append(line)

    return result


# =========================================================
# 11. PDF → 文本
# =========================================================

def extract_pdf(pdf_path):

    print()
    print("正在读取：")
    print(pdf_path)

    doc = pymupdf.open(pdf_path)

    try:

        law_name = detect_law_name(
            doc,
            pdf_path
        )

        all_lines = []

        for page in doc:

            text = page.get_text(
                "text"
            )

            text = text.replace(
                "\r\n",
                "\n"
            )

            text = text.replace(
                "\r",
                "\n"
            )

            lines = text.split(
                "\n"
            )

            lines = remove_page_number(
                lines
            )

            all_lines.extend(
                lines
            )

        return law_name, all_lines

    finally:

        doc.close()


# =========================================================
# 12. 保存原始 TXT
# =========================================================

def save_raw_txt(
    pdf_path,
    all_lines
):

    output_path = (
        RAW_TXT_DIR
        / f"{safe_filename(pdf_path.stem)}_原始.txt"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        for line in all_lines:

            f.write(
                line
            )

            f.write("\n")

    return output_path


# =========================================================
# 13. 清洗 + 合并断行
# =========================================================

def clean_text(all_lines):

    result = []

    current_text = ""

    current_section = ""

    for line in all_lines:

        line = line.strip()

        if not line:
            continue

        if is_appendix_section(line):

            if current_text:

                result.append({

                    "text": current_text,

                    "section": current_section

                })

                current_text = ""

            current_section = "附则"

            continue

        if is_definitions_title(line):

            if current_text:

                result.append({

                    "text": current_text,

                    "section": current_section

                })

                current_text = ""

            result.append({

                "text": line,

                "section": "附录"

            })

            current_section = "附录"

            continue

        if is_structure_line(line):

            if current_text:

                result.append({

                    "text": current_text,

                    "section": current_section

                })

                current_text = ""

            current_text = line

            continue

        if current_text:

            current_text += line

        else:

            current_text = line

    if current_text:

        result.append({

            "text": current_text,

            "section": current_section

        })

    return result


# =========================================================
# 14. 保存清洗 TXT
# =========================================================

def save_clean_txt(
    pdf_path,
    cleaned
):

    output_path = (
        CLEAN_TXT_DIR
        / f"{safe_filename(pdf_path.stem)}_清洗后.txt"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        for item in cleaned:

            f.write(
                item["text"]
            )

            f.write("\n")

    return output_path


# =========================================================
# 15. 创建法规条文唯一 ID
# =========================================================

def make_article_id(
    law_name,
    article
):

    raw = (
        f"{law_name}_{article}"
    )

    return hashlib.md5(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()[:16]


# =========================================================
# 16. 清洗数据 → JSON
# =========================================================

def build_json(
    cleaned,
    law_name,
    source_file
):

    articles = []

    in_definitions = False

    definitions_title = ""

    definitions_content = []

    for item in cleaned:

        text = item["text"]

        section = item["section"]

        if is_definitions_title(text):

            if in_definitions:

                if definitions_content:

                    articles.append({

                        "id": make_article_id(
                            law_name,
                            definitions_title
                        ),

                        "type": "definitions",

                        "law_name": law_name,

                        "title": definitions_title,

                        "content": "".join(
                            definitions_content
                        ),

                        "source_file": source_file

                    })

            definitions_title = text

            definitions_content = []

            in_definitions = True

            continue

        if in_definitions:

            if section == "附录":

                definitions_content.append(
                    text
                )

                continue

            else:

                if definitions_content:

                    articles.append({

                        "id": make_article_id(
                            law_name,
                            definitions_title
                        ),

                        "type": "definitions",

                        "law_name": law_name,

                        "title": definitions_title,

                        "content": "".join(
                            definitions_content
                        ),

                        "source_file": source_file

                    })

                in_definitions = False

                definitions_content = []

        article, content = parse_article(
            text
        )

        if not article:
            continue

        if not content:
            continue

        data = {

            "id": make_article_id(
                law_name,
                article
            ),

            "type": "article",

            "law_name": law_name,

            "article": article,

            "content": content,

            "source_file": source_file

        }

        if section:

            data["section"] = section

        articles.append(
            data
        )

    if in_definitions:

        if definitions_content:

            articles.append({

                "id": make_article_id(
                    law_name,
                    definitions_title
                ),

                "type": "definitions",

                "law_name": law_name,

                "title": definitions_title,

                "content": "".join(
                    definitions_content
                ),

                "source_file": source_file

            })

    return articles


# =========================================================
# 17. 去重
# =========================================================

def deduplicate_articles(articles):

    result = []

    seen = set()

    for item in articles:

        item_id = item.get(
            "id"
        )

        if not item_id:

            result.append(
                item
            )

            continue

        if item_id in seen:
            continue

        seen.add(
            item_id
        )

        result.append(
            item
        )

    return result


# =========================================================
# 18. 检查单个法规
# =========================================================

def check_law_json(
    articles,
    law_name
):

    article_count = sum(

        1

        for item in articles

        if item.get(
            "type"
        ) == "article"

    )

    appendix_count = sum(

        1

        for item in articles

        if item.get(
            "section"
        ) == "附则"

    )

    definitions_count = sum(

        1

        for item in articles

        if item.get(
            "type"
        ) == "definitions"

    )

    print()
    print("------------------------------------")
    print(
        f"法规：{law_name}"
    )
    print(
        f"法规条文：{article_count} 条"
    )
    print(
        f"附则条文：{appendix_count} 条"
    )
    print(
        f"附录：{definitions_count} 个"
    )
    print("------------------------------------")

    return article_count > 0


# =========================================================
# 19. ✅ 新增：保存单个 PDF 的知识库到独立目录
# =========================================================

def save_pdf_knowledge(articles, source_file):
    """
    保存单个 PDF 的知识库到独立目录
    """
    pdf_name = Path(source_file).stem
    pdf_name = safe_filename(pdf_name)

    pdf_knowledge_dir = KNOWLEDGE_DIR / pdf_name
    pdf_knowledge_dir.mkdir(parents=True, exist_ok=True)

    json_path = pdf_knowledge_dir / "articles.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print()
    print(f"   ✅ 保存知识库：{pdf_name}")
    print(f"      📁 {json_path.resolve()}")
    print(f"      📊 {len(articles)} 条记录")

    return json_path


# =========================================================
# 20. ✅ 新增：保存知识库索引
# =========================================================

def save_index(pdf_results):
    """
    保存所有 PDF 的索引文件
    """
    index_path = KNOWLEDGE_DIR / "index.json"

    index_data = []
    for result in pdf_results:
        if result["success"]:
            index_data.append({
                "name": result["pdf_name"],
                "source_file": result["source_file"],
                "article_count": result["article_count"],
                "path": str(result["json_path"]),
                "created": datetime.now().isoformat()
            })

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print()
    print(f"📋 索引保存成功：{index_path.resolve()}")
    print(f"   共 {len(index_data)} 个 PDF 知识库")


# =========================================================
# 21. 获取 PDF 文件
# =========================================================

def find_pdf_files():

    pdf_files = sorted(
        PDF_DIR.glob("*.pdf")
    )

    return pdf_files


# =========================================================
# 22. 显示知识库统计
# =========================================================

def show_statistics(
    articles
):

    laws = {}

    for item in articles:

        law_name = item.get(
            "law_name",
            "未知法规"
        )

        if law_name not in laws:

            laws[law_name] = {

                "articles": 0,

                "definitions": 0

            }

        if item.get(
            "type"
        ) == "article":

            laws[law_name]["articles"] += 1

        elif item.get(
            "type"
        ) == "definitions":

            laws[law_name]["definitions"] += 1

    print()
    print(
        "===================================="
    )
    print(
        "知识库统计"
    )
    print(
        "===================================="
    )

    print(
        f"法规数量：{len(laws)}"
    )

    print(
        f"总记录数：{len(articles)}"
    )

    print()

    for law_name, info in laws.items():

        print(
            f"【{law_name}】"
        )

        print(
            f"  条文：{info['articles']} 条"
        )

        print(
            f"  附录：{info['definitions']} 个"
        )


# =========================================================
# 23. ✅ 修改后的主程序
# =========================================================

def main():

    print()
    print(
        "===================================="
    )
    print(
        "       通用法规知识库构建程序"
    )
    print(
        "===================================="
    )

    # 创建目录
    create_directories()

    print()
    print(
        "PDF目录："
    )

    print(
        PDF_DIR.resolve()
    )

    # 查找 PDF
    pdf_files = find_pdf_files()

    if not pdf_files:

        print()
        print(
            "❌ 没有找到 PDF 文件。"
        )

        print()
        print(
            "请把法规 PDF 放到："
        )

        print(
            PDF_DIR.resolve()
        )

        print()
        print(
            "例如："
        )

        print(
            "  安全生产法.pdf"
        )

        print(
            "  消防法.pdf"
        )

        print(
            "  建筑法.pdf"
        )

        return

    # 显示 PDF
    print()
    print(
        f"发现 {len(pdf_files)} 个 PDF："
    )

    for index, pdf_path in enumerate(
        pdf_files,
        start=1
    ):

        print(
            f"{index}. {pdf_path.name}"
        )

    # ✅ 本次处理结果
    pdf_results = []
    success_count = 0
    failed_count = 0

    # 逐个处理 PDF
    for index, pdf_path in enumerate(
        pdf_files,
        start=1
    ):

        print()
        print(
            "===================================="
        )

        print(
            f"正在处理 [{index}/{len(pdf_files)}]"
        )

        print(
            pdf_path.name
        )

        print(
            "===================================="
        )

        try:

            # ---------------------------------------------
            # PDF提取
            # ---------------------------------------------

            law_name, all_lines = extract_pdf(
                pdf_path
            )

            print()
            print(
                f"识别法规名称：{law_name}"
            )

            print(
                f"提取文本：{len(all_lines)} 行"
            )

            # ---------------------------------------------
            # 原始TXT
            # ---------------------------------------------

            try:

                raw_path = save_raw_txt(
                    pdf_path,
                    all_lines
                )

                print(
                    f"原始TXT：{raw_path.resolve()}"
                )

            except Exception as e:

                print(
                    f"⚠️ 原始TXT保存失败：{e}"
                )

            # ---------------------------------------------
            # 清洗
            # ---------------------------------------------

            cleaned = clean_text(
                all_lines
            )

            print(
                f"清洗后：{len(cleaned)} 段"
            )

            # ---------------------------------------------
            # 清洗TXT
            # ---------------------------------------------

            try:

                clean_path = save_clean_txt(
                    pdf_path,
                    cleaned
                )

                print(
                    f"清洗TXT：{clean_path.resolve()}"
                )

            except Exception as e:

                print(
                    f"⚠️ 清洗TXT保存失败：{e}"
                )

            # ---------------------------------------------
            # JSON
            # ---------------------------------------------

            articles = build_json(

                cleaned,

                law_name,

                pdf_path.name

            )

            # ---------------------------------------------
            # 检查
            # ---------------------------------------------

            if not check_law_json(
                articles,
                law_name
            ):

                print()
                print(
                    "❌ 这个 PDF 没有识别到法规条文。"
                )

                print(
                    "为了安全，本文件不会加入知识库。"
                )

                failed_count += 1

                continue

            # ---------------------------------------------
            # ✅ 去重
            # ---------------------------------------------

            articles = deduplicate_articles(
                articles
            )

            # ---------------------------------------------
            # ✅ 保存到独立目录
            # ---------------------------------------------

            json_path = save_pdf_knowledge(
                articles,
                pdf_path.name
            )

            pdf_results.append({
                "success": True,
                "pdf_name": Path(pdf_path.name).stem,
                "source_file": pdf_path.name,
                "article_count": len(articles),
                "json_path": json_path
            })

            success_count += 1

        except Exception as e:

            failed_count += 1

            print()
            print(
                f"❌ 处理失败：{e}"
            )

            import traceback
            traceback.print_exc()

    # ✅ 保存索引
    if pdf_results:
        save_index(pdf_results)

    # =====================================================
    # 最终结果
    # =====================================================

    print()
    print(
        "===================================="
    )
    print(
        "处理完成"
    )
    print(
        "===================================="
    )

    print(
        f"成功处理 PDF：{success_count} 个"
    )

    print(
        f"处理失败 PDF：{failed_count} 个"
    )

    print()
    print(
        "📁 知识库目录："
    )

    print(
        KNOWLEDGE_DIR.resolve()
    )

    print()
    print(
        "📁 PDF目录："
    )

    print(
        PDF_DIR.resolve()
    )

    print()
    print(
        "📁 原始TXT目录："
    )

    print(
        RAW_TXT_DIR.resolve()
    )

    print()
    print(
        "📁 清洗TXT目录："
    )

    print(
        CLEAN_TXT_DIR.resolve()
    )

    print()
    print(
        "===================================="
    )
    print(
        "✅ 通用法规知识库构建完成！"
    )
    print(
        "===================================="
    )


# =========================================================
# 24. 程序入口
# =========================================================

if __name__ == "__main__":

    main()