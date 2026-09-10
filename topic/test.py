import requests

url = "http://localhost:1100/deptBankManage/python/import"

data = {
    "dept": {
        "id": "test-dept-002",
        "fullName": "测试分类11"
    },
    "create_user_id": "test2",
    "create_user_name": "测试用户333",
    "questions": [
        {
            "question_type": "单选题",
            "title": "Python本地接口测试题，请删除",
            "plan_a": "选项A",
            "plan_b": "选项B",
            "plan_c": "选项C",
            "plan_d": "选项D",
            "answer": "A",
            "analysis": "这是本地Python接口测试解析"
        }
    ]
}

response = requests.post(
    url,
    json=data,
    timeout=120
)

print(response.status_code)
print(response.json())