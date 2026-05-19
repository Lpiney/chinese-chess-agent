"""DeepSeek API 客户端。"""

from __future__ import annotations

from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config(config_path: str | None = None) -> dict:
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    if not path.exists():
        raise RuntimeError("缺少 config.yaml，请先参考 config.example.yaml 创建。")

    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("缺少 pyyaml，请先执行 pip install -r requirements.txt。") from exc

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if config is None:
        raise RuntimeError("config.yaml 内容为空。")

    api_key = config.get("deepseek", {}).get("api_key", "")
    if not api_key or api_key.startswith("在这里填写"):
        raise RuntimeError("DeepSeek API Key 未填写，请先修改 config.yaml。")
    return config


def create_client(config: dict):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("缺少 openai 依赖，请先执行 pip install -r requirements.txt。") from exc

    ds_config = config["deepseek"]
    return OpenAI(
        api_key=ds_config["api_key"],
        base_url=ds_config.get("base_url", "https://api.deepseek.com"),
        timeout=ds_config.get("timeout", 60),
    )


def chat_completion(
    client,
    config: dict,
    system_prompt: str,
    user_prompt: str,
):
    ds_config = config["deepseek"]
    response = client.chat.completions.create(
        model=ds_config.get("model_name", "deepseek-v4-flash"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=ds_config.get("temperature", 0.2),
        max_tokens=ds_config.get("max_tokens", 1200),
        stream=True,
    )

    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            yield content
