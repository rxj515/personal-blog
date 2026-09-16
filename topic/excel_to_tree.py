import pandas as pd
import os


def safe_value(value):

    """
    处理Excel空值
    防止 NaN 导致 FastAPI JSON报错
    """

    if pd.isna(value):
        return ""

    return str(value)



def load_category_tree():

    """
    读取属性结构Excel生成树
    """

    excel_path = os.path.join(
        os.path.dirname(__file__),
        "data",
        "study_dept_bank_type.xlsx"
    )


    print("读取Excel:", excel_path)


    # 读取Excel
    df = pd.read_excel(
        excel_path
    )


    # 所有空值转为空字符串
    df = df.fillna("")


    nodes = {}


    # 创建节点
    for _, row in df.iterrows():


        dept_id = safe_value(
            row["id"]
        )


        nodes[dept_id] = {


            "id": dept_id,


            "name": safe_value(
                row["name"]
            ),


            "code": safe_value(
                row.get("code", "")
            ),


            "parentId": safe_value(
                row.get("parent_id", "")
            ),


            "superiorId": safe_value(
                row.get("superior_id", "")
            ),


            "superiorName": safe_value(
                row.get("superior_name", "")
            ),


            "subjectionId": safe_value(
                row.get("subjection_id", "")
            ),


            "subjectionName": safe_value(
                row.get("subjection_name", "")
            ),


            "children": []

        }



    tree = []


    # 构建父子关系

    for dept_id, dept in nodes.items():


        parent_id = dept["parentId"]


        # 兼容0和空

        if (
            parent_id
            and parent_id != "0"
            and parent_id in nodes
        ):


            nodes[parent_id]["children"].append(
                dept
            )


        else:

            tree.append(
                dept
            )



    # 删除空children

    def clean_children(items):


        for item in items:


            if item["children"]:

                clean_children(
                    item["children"]
                )


            else:

                item.pop(
                    "children"
                )



    clean_children(tree)


    print(
        "生成分类数量:",
        len(tree)
    )


    return tree