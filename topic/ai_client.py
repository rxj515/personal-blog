# ============================================================
# ai_client.py
# 通用 AI 调用模块
#
# 所有AI配置统一从 ai_config.py 获取
#
# 支持：
# 1. Ollama
# 2. DeepSeek
# 3. OpenAI
# 4. 通义千问 (Qwen)
# 5. 智谱AI (GLM)
# 6. 其他OpenAI兼容接口 (custom)
#
# 重要：
# AI模型完全由 config/ai_config.json 决定。
#
# 前端出题页面：
# 不传model
# 不传provider
# 不修改AI配置
# ============================================================

import requests

from ai_config import get_ai_config


# ============================================================
# 兼容旧代码的变量
# ============================================================

_ai_type = None


# ============================================================
# 获取当前AI配置
# ============================================================

def _get_config():

    config = get_ai_config()

    if not isinstance(config, dict):

        raise ValueError(
            "AI配置格式错误"
        )

    provider = str(
        config.get("provider", "")
    ).strip().lower()

    model = str(
        config.get("model", "")
    ).strip()

    base_url = str(
        config.get("base_url", "")
    ).strip()

    api_key = str(
        config.get("api_key", "")
    ).strip()

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key
    }


# ============================================================
# 兼容旧代码
# ============================================================

def set_ai_type(ai_type=None):
    """
    兼容旧版本。

    注意：
    这个函数不会修改真正AI配置。

    真正配置永远来自：

    config/ai_config.json
    """

    global _ai_type

    _ai_type = ai_type

    config = _get_config()

    print("=" * 60)
    print("set_ai_type() 兼容调用")
    print("传入值        :", ai_type)
    print("实际Provider   :", config["provider"])
    print("实际Model      :", config["model"])
    print("=" * 60)

    return config["provider"]


# ============================================================
# 获取当前Provider
# ============================================================

def get_ai_type():

    config = _get_config()

    return config["provider"]


# ============================================================
# 获取当前模型
# ============================================================

def get_ai_model():

    config = _get_config()

    return config["model"]


# ============================================================
# Ollama
# ============================================================

def _ask_ollama(prompt, config):

    base_url = config["base_url"]

    if not base_url:

        base_url = "http://localhost:11434"

    base_url = base_url.rstrip("/")

    # --------------------------------------------------------
    # ✅ 修复：如果以 /v1 结尾，去掉 /v1
    # Ollama 的 API 路径是 /api/generate，不是 /v1/api/generate
    # --------------------------------------------------------

    if base_url.endswith("/v1"):

        base_url = base_url[:-3]  # 去掉 /v1

    # --------------------------------------------------------
    # 自动补充 /api/generate
    # --------------------------------------------------------

    if not base_url.endswith("/api/generate"):

        base_url += "/api/generate"

    model = config["model"]

    if not model:

        raise ValueError(
            "没有配置Ollama模型"
        )

    # --------------------------------------------------------
    # 请求数据
    # --------------------------------------------------------

    data = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }

    print("=" * 60)
    print("调用 Ollama")
    print("URL   :", base_url)
    print("Model :", model)
    print("=" * 60)

    try:

        response = requests.post(
            base_url,
            json=data,
            timeout=300
        )

    except requests.exceptions.Timeout as e:

        raise RuntimeError(
            "Ollama请求超时"
        ) from e

    except requests.exceptions.ConnectionError as e:

        raise RuntimeError(
            "无法连接Ollama，请检查Ollama是否启动"
        ) from e

    except requests.exceptions.RequestException as e:

        raise RuntimeError(
            f"Ollama请求失败：{e}"
        ) from e

    # --------------------------------------------------------
    # HTTP错误
    # --------------------------------------------------------

    try:

        response.raise_for_status()

    except requests.exceptions.HTTPError as e:

        try:
            error_data = response.json()
        except Exception:
            error_data = response.text

        raise RuntimeError(
            f"Ollama请求失败：HTTP "
            f"{response.status_code}，"
            f"返回：{error_data}"
        ) from e

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:

        result = response.json()

    except Exception as e:

        raise RuntimeError(
            f"Ollama返回不是有效JSON："
            f"{response.text}"
        ) from e

    print("=" * 60)
    print("Ollama返回")
    print(result)
    print("=" * 60)

    # --------------------------------------------------------
    # response
    # --------------------------------------------------------

    if "response" not in result:

        raise RuntimeError(
            f"Ollama返回数据异常：{result}"
        )

    content = result["response"]

    if not content:

        raise RuntimeError(
            "Ollama返回内容为空"
        )

    return content


# ============================================================
# OpenAI / DeepSeek / Qwen / Zhipu / Custom
# ============================================================

def _build_chat_url(base_url):

    base_url = str(
        base_url or ""
    ).strip().rstrip("/")

    if not base_url:

        raise ValueError(
            "没有配置AI API地址"
        )

    # --------------------------------------------------------
    # 已经是完整地址
    # --------------------------------------------------------

    if base_url.endswith(
        "/chat/completions"
    ):

        return base_url

    # --------------------------------------------------------
    # /v1
    # --------------------------------------------------------

    if base_url.endswith("/v1"):

        return (
            base_url
            + "/chat/completions"
        )

    # --------------------------------------------------------
    # 默认
    # --------------------------------------------------------

    return (
        base_url
        + "/v1/chat/completions"
    )


def _ask_openai_compatible(prompt, config):

    base_url = config["base_url"]

    model = config["model"]

    api_key = config["api_key"]

    if not model:

        raise ValueError(
            "没有配置AI模型"
        )

    url = _build_chat_url(
        base_url
    )

    # --------------------------------------------------------
    # 请求数据
    # --------------------------------------------------------

    data = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7
    }

    # --------------------------------------------------------
    # 请求头
    # --------------------------------------------------------

    headers = {
        "Content-Type": "application/json"
    }

    if api_key:

        headers["Authorization"] = (
            f"Bearer {api_key}"
        )

    print("=" * 60)
    print("调用OpenAI兼容接口")
    print("URL   :", url)
    print("Model :", model)
    print(
        "API Key:",
        "已配置" if api_key else "未配置"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # 请求
    # --------------------------------------------------------

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=300
        )

    except requests.exceptions.Timeout as e:

        raise RuntimeError(
            "AI接口请求超时"
        ) from e

    except requests.exceptions.ConnectionError as e:

        raise RuntimeError(
            f"无法连接AI接口：{url}"
        ) from e

    except requests.exceptions.RequestException as e:

        raise RuntimeError(
            f"AI接口请求失败：{e}"
        ) from e

    # --------------------------------------------------------
    # HTTP错误
    # --------------------------------------------------------

    try:

        response.raise_for_status()

    except requests.exceptions.HTTPError as e:

        try:

            error_data = response.json()

        except Exception:

            error_data = response.text

        raise RuntimeError(
            f"AI接口请求失败："
            f"HTTP {response.status_code}，"
            f"返回：{error_data}"
        ) from e

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    try:

        result = response.json()

    except Exception as e:

        raise RuntimeError(
            "AI接口返回的不是有效JSON："
            f"{response.text}"
        ) from e

    print("=" * 60)
    print("AI接口返回")
    print(result)
    print("=" * 60)

    # --------------------------------------------------------
    # 获取content
    # --------------------------------------------------------

    try:

        content = (
            result
            ["choices"][0]
            ["message"]
            ["content"]
        )

    except Exception as e:

        raise RuntimeError(
            f"AI返回数据格式异常：{result}"
        ) from e

    if not content:

        raise RuntimeError(
            "AI返回内容为空"
        )

    return content


# ============================================================
# 通用AI调用
# ============================================================

def ask_ai(prompt):
    """
    统一AI调用入口。

    重要：

    不接收model参数。

    不接收provider参数。

    每次调用都会重新读取：

        config/ai_config.json
    """

    config = _get_config()

    provider = config["provider"]

    print()
    print("=" * 60)
    print("当前AI配置")
    print("=" * 60)
    print("Provider :", provider)
    print("Model    :", config["model"])
    print("Base URL :", config["base_url"])
    print(
        "API Key  :",
        "已配置" if config["api_key"] else "未配置"
    )
    print("=" * 60)

    # ========================================================
    # Ollama
    # ========================================================

    if provider == "ollama":

        return _ask_ollama(
            prompt,
            config
        )

    # ========================================================
    # DeepSeek
    # ========================================================

    elif provider == "deepseek":

        return _ask_openai_compatible(
            prompt,
            config
        )

    # ========================================================
    # OpenAI
    # ========================================================

    elif provider == "openai":

        return _ask_openai_compatible(
            prompt,
            config
        )

    # ========================================================
    # 通义千问 (Qwen)
    # ========================================================

    elif provider == "qwen":

        return _ask_openai_compatible(
            prompt,
            config
        )

    # ========================================================
    # 智谱AI (GLM)
    # ========================================================

    elif provider == "zhipu":

        return _ask_openai_compatible(
            prompt,
            config
        )

    # ========================================================
    # Custom
    # ========================================================

    elif provider == "custom":

        return _ask_openai_compatible(
            prompt,
            config
        )

    # ========================================================
    # 未知
    # ========================================================

    else:

        raise ValueError(
            f"不支持的AI类型：{provider}"
        )


# ============================================================
# 兼容 generate_questions.py
# ============================================================

def generate(prompt):

    return ask_ai(prompt)


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("AI Client测试")
    print("=" * 60)

    config = _get_config()

    print(
        "Provider:",
        config["provider"]
    )

    print(
        "Model:",
        config["model"]
    )

    print(
        "Base URL:",
        config["base_url"]
    )

    print("=" * 60)