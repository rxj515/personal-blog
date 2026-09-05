import requests

# 获取工种列表
response = requests.get("http://localhost:1100/deptBankType/getExcelTypeSelectPy")
data = response.json()

# 提取所有工种的 superiorName
superior_names = set()
def flatten(nodes):
    for node in nodes:
        superior_names.add(node.get("superiorName", ""))
        if node.get("children"):
            flatten(node["children"])
flatten(data)

print("所有上级名称：")
for name in superior_names:
    print(name)