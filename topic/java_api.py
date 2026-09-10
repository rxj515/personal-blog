import os
import requests


JAVA_BASE_URL = os.getenv(
    "JAVA_BASE_URL",
    "http://localhost:1100"
)


def get_java_user():
    """
    从 Java 获取当前用户信息
    """

    url = f"{JAVA_BASE_URL}/python/user-info"

    try:
        response = requests.get(
            url,
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        if result.get("code") != 200:
            return None

        return result.get("data")

    except Exception as e:
        print(f"❌ 获取Java用户失败: {e}")
        return None