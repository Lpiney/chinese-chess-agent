"""兼容旧导入路径，实际实现已经迁移到 llm_client。"""

from llm_client import chat_completion, create_client, load_config

__all__ = ["load_config", "create_client", "chat_completion"]
