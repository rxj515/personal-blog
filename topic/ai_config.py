# ============================================================
# ai_config.py
# AI统一配置管理
#
# 职责：
# 1. 读取 config/ai_config.json
# 2. 保存 config/ai_config.json
# 3. 提供统一AI配置
#
# 不负责：
# 1. 调用AI
# 2. 生成题目
# 3. HTTP请求
# ============================================================

from pathlib import Path
import json


# ============================================================
# 1. 项目根目录
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# 2. 配置目录
# ============================================================

CONFIG_DIR = BASE_DIR / "config"


# ============================================================
# 3. AI配置文件
# ============================================================

CONFIG_FILE = CONFIG_DIR / "ai_config.json"


# ============================================================
# 4. 默认配置
# ============================================================

DEFAULT_CONFIG = {
    "provider": "ollama",
    "model": "qwen3:8b",
    "base_url": "http://localhost:11434",
    "api_key": ""
}


# ============================================================
# 5. 支持的AI
# ============================================================

SUPPORTED_PROVIDERS = {
    "ollama",
    "deepseek",
    "openai",
    "qwen",
    "zhipu",
    "custom"
}


# ============================================================
# 6. 默认配置
# ============================================================

def _get_default_config_by_provider(provider):
    """
    根据Provider获取默认配置。
    """

    provider = str(provider or "").lower().strip()

    if provider == "ollama":
        return {
            "provider": "ollama",
            "model": "qwen3:8b",
            "base_url": "http://localhost:11434",
            "api_key": ""
        }

    if provider == "deepseek":
        return {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": ""
        }

    if provider == "openai":
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key": ""
        }

    if provider == "qwen":
        return {
            "provider": "qwen",
            "model": "qwen-plus",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": ""
        }

    if provider == "zhipu":
        return {
            "provider": "zhipu",
            "model": "glm-4-plus",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key": ""
        }

    return {
        "provider": "custom",
        "model": "",
        "base_url": "",
        "api_key": ""
    }


# ============================================================
# 7. 确保配置目录
# ============================================================

def _ensure_config_dir():
    """
    确保config目录存在。
    """

    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# 8. 规范化Provider
# ============================================================

def normalize_provider(provider):
    """
    Provider统一转换。

    支持：

    ollama
    deepseek
    openai
    qwen
    zhipu
    custom

    同时兼容旧配置：

    ai
    """

    if provider is None:
        return None

    provider = str(provider).strip().lower()

    mapping = {
        "ollama": "ollama",
        "deepseek": "deepseek",
        "openai": "openai",
        "qwen": "qwen",
        "zhipu": "zhipu",
        "custom": "custom",

        # 兼容旧名称
        "ai": "ollama"
    }

    return mapping.get(provider)


# ============================================================
# 9. 规范化配置
# ============================================================

def _normalize_config(data):
    """
    将各种旧格式统一成：

    {
        "provider": "...",
        "model": "...",
        "base_url": "...",
        "api_key": "..."
    }
    """

    if not isinstance(data, dict):
        raise ValueError("AI配置必须是对象")

    # --------------------------------------------------------
    # Provider
    # --------------------------------------------------------

    provider = (
        data.get("provider")
        or data.get("ai")
        or DEFAULT_CONFIG["provider"]
    )

    provider = normalize_provider(provider)

    if provider is None:
        raise ValueError(
            f"不支持的AI类型：{data.get('provider')}"
        )

    defaults = _get_default_config_by_provider(provider)

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = str(
        data.get("model")
        or defaults["model"]
        or ""
    ).strip()

    # --------------------------------------------------------
    # Base URL
    # --------------------------------------------------------

    base_url = str(
        data.get("base_url")
        or defaults["base_url"]
        or ""
    ).strip()

    # --------------------------------------------------------
    # API Key
    # --------------------------------------------------------

    api_key = str(
        data.get("api_key")
        or ""
    ).strip()

    # --------------------------------------------------------
    # 最终配置
    # --------------------------------------------------------

    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key": api_key
    }


# ============================================================
# 10. 获取AI配置
# ============================================================

def get_ai_config():
    """
    获取当前AI配置。

    每次调用都会重新读取配置文件。

    这样网页修改配置以后，
    AI出题模块下一次调用就会自动使用新配置。
    """

    _ensure_config_dir()

    # --------------------------------------------------------
    # 配置文件不存在
    # --------------------------------------------------------

    if not CONFIG_FILE.exists():

        config = DEFAULT_CONFIG.copy()

        save_ai_config(config)

        return config

    # --------------------------------------------------------
    # 读取配置
    # --------------------------------------------------------

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

    except Exception as e:

        print(
            f"⚠️ 读取AI配置失败：{e}"
        )

        config = DEFAULT_CONFIG.copy()

        save_ai_config(config)

        return config

    # --------------------------------------------------------
    # 规范化
    # --------------------------------------------------------

    try:

        config = _normalize_config(data)

    except Exception as e:

        print(
            f"⚠️ AI配置格式错误：{e}"
        )

        config = DEFAULT_CONFIG.copy()

        save_ai_config(config)

        return config

    return config


# ============================================================
# 11. 保存AI配置
# ============================================================

def save_ai_config(data):
    """
    保存AI配置。

    最终只保存：

    {
        "provider": "...",
        "model": "...",
        "base_url": "...",
        "api_key": "..."
    }
    """

    if not isinstance(data, dict):

        raise ValueError(
            "AI配置必须是对象"
        )

    _ensure_config_dir()

    # --------------------------------------------------------
    # 统一配置
    # --------------------------------------------------------

    config = _normalize_config(data)

    # --------------------------------------------------------
    # Provider
    # --------------------------------------------------------

    provider = config["provider"]

    if provider not in SUPPORTED_PROVIDERS:

        raise ValueError(
            f"不支持的AI类型：{provider}"
        )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    if not config["model"]:

        raise ValueError(
            "AI模型不能为空"
        )

    # --------------------------------------------------------
    # Base URL
    # --------------------------------------------------------

    if not config["base_url"]:

        raise ValueError(
            "AI API地址不能为空"
        )

    # --------------------------------------------------------
    # 保存
    # --------------------------------------------------------

    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            config,
            f,
            ensure_ascii=False,
            indent=4
        )

    print()
    print("=" * 60)
    print("AI配置保存成功")
    print("=" * 60)
    print("Provider :", config["provider"])
    print("Model    :", config["model"])
    print("Base URL :", config["base_url"])
    print(
        "API Key  :",
        "已配置" if config["api_key"] else "未配置"
    )
    print("=" * 60)
    print()

    return config


# ============================================================
# 12. 获取配置文件路径
# ============================================================

def get_ai_config_file():
    """
    返回AI配置文件绝对路径。
    """

    return str(
        CONFIG_FILE.resolve()
    )


# ============================================================
# 13. 测试
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("AI配置测试")
    print("=" * 60)

    config = get_ai_config()

    print(
        json.dumps(
            config,
            ensure_ascii=False,
            indent=4
        )
    )

    print()
    print(
        "配置文件：",
        CONFIG_FILE.resolve()
    )