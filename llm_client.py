"""OpenAI 兼容 LLM 客户端，默认接入阿里云百炼。"""

from __future__ import annotations

from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL_NAME = "qwen3.6-max-preview"


def load_config(config_path: str | None = None) -> dict:
    """加载并校验配置文件。"""
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

    llm_config = config.get("llm", {})
    api_key = llm_config.get("api_key", "")
    if not api_key or api_key.startswith("在这里填写"):
        raise RuntimeError("LLM API Key 未填写，请先修改 config.yaml。")

    return config


def create_client(config: dict):
    """创建 OpenAI 兼容客户端。"""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("缺少 openai 依赖，请先执行 pip install -r requirements.txt。") from exc

    llm_config = config["llm"]
    return OpenAI(
        api_key=llm_config["api_key"],
        base_url=llm_config.get("base_url", DEFAULT_BASE_URL),
        timeout=llm_config.get("timeout", 60),
    )


def chat_completion(client, config: dict, system_prompt: str, user_prompt: str):
    """流式调用聊天补全；若空流则自动回退到非流式调用。"""
    llm_config = config["llm"]
    response = client.chat.completions.create(
        model=llm_config.get("model_name", DEFAULT_MODEL_NAME),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=llm_config.get("temperature", 0.2),
        max_tokens=llm_config.get("max_tokens", 1200),
        extra_body=_build_extra_body(llm_config),
        stream=True,
    )

    emitted = False
    for chunk in response:
        content = _extract_stream_chunk_text(chunk)
        if content:
            emitted = True
            yield content

    if not emitted:
        fallback_text = _chat_completion_non_stream(
            client=client,
            config=config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if fallback_text:
            yield fallback_text


def _chat_completion_non_stream(client, config: dict, system_prompt: str, user_prompt: str) -> str:
    """非流式兜底调用。"""
    llm_config = config["llm"]
    response = client.chat.completions.create(
        model=llm_config.get("model_name", DEFAULT_MODEL_NAME),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=llm_config.get("temperature", 0.2),
        max_tokens=llm_config.get("max_tokens", 1200),
        extra_body=_build_extra_body(llm_config),
        stream=False,
    )
    if not response.choices:
        return ""
    message = response.choices[0].message
    return _normalize_message_content(getattr(message, "content", None))


def _extract_stream_chunk_text(chunk) -> str:
    """提取流式 chunk 的最终可见正文。"""
    if not getattr(chunk, "choices", None):
        return ""

    delta = chunk.choices[0].delta
    return _normalize_message_content(getattr(delta, "content", None))


def _normalize_message_content(content) -> str:
    """兼容不同返回格式，统一转成字符串。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
                continue
            text = getattr(item, "text", None) or getattr(item, "content", None)
            if text:
                parts.append(str(text))
        return "".join(parts)
    return str(content)


def _build_extra_body(llm_config: dict) -> dict:
    """构造百炼兼容扩展参数，默认关闭思考模式。"""
    extra_body = {
        "enable_thinking": llm_config.get("enable_thinking", False),
        "preserve_thinking": llm_config.get("preserve_thinking", False),
    }
    thinking_budget = llm_config.get("thinking_budget")
    if thinking_budget is not None:
        extra_body["thinking_budget"] = thinking_budget
    return extra_body
