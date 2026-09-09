import requests

# ✅ 修正 URL：去掉多余的 https://
url = "http://zhongyangtaoyuan.com:1100/deptBankType/getExcelTypeSelectPy"

try:
    response = requests.get(url, timeout=10)
    
    # 检查响应状态
    if response.status_code == 200:
        data = response.json()
        
        # 提取所有工种的 superiorName
        superior_names = set()
        
        def flatten(nodes):
            if not isinstance(nodes, list):
                return
            for node in nodes:
                # 添加 superiorName（如果存在）
                name = node.get("superiorName")
                if name:
                    superior_names.add(name)
                # 递归处理子节点
                if node.get("children"):
                    flatten(node["children"])
        
        # 处理数据（兼容两种返回格式）
        if isinstance(data, dict) and "data" in data:
            flatten(data["data"])
        else:
            flatten(data)
        
        print("所有上级名称：")
        for name in sorted(superior_names):
            print(f"  - {name}")
        print(f"\n共找到 {len(superior_names)} 个不同的上级名称")
        
    else:
        print(f"❌ 请求失败，HTTP 状态码：{response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("❌ 连接失败，请检查：")
    print("  1. URL 是否正确")
    print("  2. Java 后端服务是否启动")
    print("  3. 网络是否可达")
except Exception as e:
    print(f"❌ 发生错误：{e}")


    