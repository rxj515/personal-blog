import requests

token = "gwCdrjJyaQCC5mKafh18AnErzwf8bWxeR19FwDC1w1GPCOsapuJyHMVr4XLHK8S0"
url = "http://localhost:60853/deptBankType/getExcelTypeSelect"

# 测试不同的 Header 名称
headers_list = {
    "satoken": {"Content-Type": "application/json", "satoken": token},
    "token": {"Content-Type": "application/json", "token": token},
    "Authorization": {"Content-Type": "application/json", "Authorization": token},
    "Bearer": {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    "Cookie": {"Cookie": f"satoken={token}"},
}

for name, headers in headers_list.items():
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"【{name}】 状态码: {response.status_code}")
        print(f"   响应内容: {response.text[:300]}")
        print("-" * 60)
        
        if response.status_code == 200:
            print(f"✅ 成功！使用 {name} 头可以访问！")
            break
    except Exception as e:
        print(f"【{name}】 请求出错: {e}")