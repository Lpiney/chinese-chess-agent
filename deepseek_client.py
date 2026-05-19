"""DeepSeek 客户端，支持流式输出和空响应兜底。"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Python 基础知识点：pathlib.Path
# ---------------------------------------------------------------------------
# pathlib 是 Python 3.4+ 引入的标准库，提供了面向对象的文件路径操作。
# 相比于传统的 os.path 字符串操作，Path 更加直观和跨平台。
#
# Path(__file__).resolve().parent 的含义：
#   1. __file__           → 当前文件的路径（相对路径）
#   2. .resolve()         → 转为绝对路径
#   3. .parent            → 获取父目录（即文件所在目录）
#   4. / "config.yaml"    → Path 对象可以用 / 拼接路径（不需要 os.path.join）
#
# 最终结果：不管脚本从哪个目录运行，都能正确找到 config.yaml。
from pathlib import Path


# 配置文件路径 —— 项目根目录下的 config.yaml
# 这是模块级别的常量，大写命名是 Python 的命名约定（类似其他语言的 CONSTANT_CASE）。
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_config(config_path: str | None = None) -> dict:
    """
    加载并验证配置文件。

    参数：
        config_path: 配置文件路径，默认使用项目根目录下的 config.yaml

    返回：
        解析后的配置字典，结构如下：
        {
            "deepseek": {
                "api_key": "sk-...",
                "base_url": "https://api.deepseek.com",
                "model_name": "deepseek-v4-flash",
                "temperature": 0.2,
                "max_tokens": 1200,
                "timeout": 60
            }
        }

    这个方法会进行多层验证，每一步出错都有清晰的中文错误提示。

    -------------------------------------------------------------------
    Python 基础知识点：条件表达式（三元运算符）
    -------------------------------------------------------------------
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    等价于其他语言的：config_path ? Path(config_path) : CONFIG_PATH
    如果传了 config_path 就包装成 Path 对象，否则用默认路径。
    """
    # 确定使用哪个配置文件路径
    path = Path(config_path) if config_path is not None else CONFIG_PATH

    # 检查配置文件是否存在
    if not path.exists():
        raise RuntimeError("缺少 config.yaml，请先参考 config.example.yaml 创建。")

    # 尝试导入 yaml 库（PyYAML 是第三方依赖，需要 pip install）
    # -------------------------------------------------------------------
    # Python 基础知识点：exception chaining（异常链）
    # -------------------------------------------------------------------
    # raise ... from exc 可以把原始异常关联到新异常上，
    # 方便排查时追溯根本原因。
    # 如果直接用 raise RuntimeError(...) 而没有 from exc，
    # 原始异常信息会丢失。
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("缺少 pyyaml，请先执行 pip install -r requirements.txt。") from exc

    # -------------------------------------------------------------------
    # Python 基础知识点：with 语句管理文件资源
    # -------------------------------------------------------------------
    # with open(...) as file:  会在进入时打开文件，退出时自动关闭文件。
    # 即使发生异常，文件也会被正确关闭。
    # 这比手写 file = open(...) / file.close() 安全得多。
    with path.open("r", encoding="utf-8") as file:
        # yaml.safe_load() 安全解析 YAML（不会执行任意代码）
        # 永远不要用 yaml.load() 加载不可信的 YAML，它有安全漏洞
        config = yaml.safe_load(file)

    # 空文件或纯注释文件会返回 None
    if config is None:
        raise RuntimeError("config.yaml 内容为空。")

    # 验证 API Key
    # -------------------------------------------------------------------
    # Python 基础知识点：dict.get() 链式调用
    # -------------------------------------------------------------------
    # config.get("deepseek", {}) 表示：
    #   从 config 字典中取 "deepseek" 这个 key 的值，
    #   如果不存在，返回默认值 {}（空字典）。
    #   然后链式调用 .get("api_key", "") 再从返回的字典中取 api_key。
    #
    # 这样做比 config["deepseek"]["api_key"] 安全，
    # 因为如果 "deepseek" 不存在，config["deepseek"] 会直接报 KeyError。
    api_key = config.get("deepseek", {}).get("api_key", "")
    if not api_key or api_key.startswith("在这里填写"):
        raise RuntimeError("DeepSeek API Key 未填写，请先修改 config.yaml。")
    return config


def create_client(config: dict):
    """
    创建 OpenAI 兼容的 API 客户端实例。

    参数：
        config: load_config() 返回的配置字典

    返回：
        openai.OpenAI 客户端实例，已配置好 API Key、base_url、timeout

    -------------------------------------------------------------------
    Python 基础知识点：函数内部导入（延迟导入）
    -------------------------------------------------------------------
    这里把 openai 的导入放在函数内部，而不是文件开头。
    好处：如果只调用 load_config 而不调用 create_client，
    就不需要安装 openai 库。这种「延迟导入」可以减少不必要的依赖。
    import 有缓存机制，即使多次调用也不会重复加载，开销很小。
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("缺少 openai 依赖，请先执行 pip install -r requirements.txt。") from exc

    ds_config = config["deepseek"]
    return OpenAI(
        api_key=ds_config["api_key"],
        # base_url：API 服务器地址。DeepSeek 的 API 地址，也可以换成其他兼容服务
        base_url=ds_config.get("base_url", "https://api.deepseek.com"),
        # timeout：HTTP 请求超时时间（秒），超过这个时间还没返回就报错
        timeout=ds_config.get("timeout", 60),
    )


# ===========================================================================
# 流式聊天补全（主函数）
# ===========================================================================

# ---------------------------------------------------------------------------
# Python 基础知识点：生成器函数 (Generator) 与 yield
# ---------------------------------------------------------------------------
# 这是一个「生成器函数」，特点是使用 yield 而不是 return。
#
# return 和 yield 的区别：
#   return：函数直接结束，返回一个值，调用一次就没了
#   yield：函数「暂停」并产出一个值，下次迭代时从暂停点继续执行
#
# 生成器的优势：
# 1. 流式输出：不需要等全部生成完，可以边生成边返回
# 2. 内存友好：不需要一次性把所有结果加载到内存里
# 3. 调用方用 for 循环获取：for chunk in chat_completion(...):
#
# 在这个函数中，每次 yield 产出 LLM 流式响应中的一小段文本。
# 调用方（chess_agent.py）用 for 循环每次拿到一段，逐段拼接。

def chat_completion(
    client,
    config: dict,
    system_prompt: str,
    user_prompt: str,
):
    """
    流式调用 DeepSeek API 进行对话生成。

    如果流式响应没有产生任何文本（某些模型可能返回空流），
    会自动回退到非流式 API 调用作为兜底方案。

    参数：
        client: OpenAI 兼容客户端
        config: 配置字典
        system_prompt: 系统提示词（定义 AI 角色）
        user_prompt: 用户提示词（包含棋盘信息和用户问题）

    生成（yield）：
        每次产出 LLM 生成的一小段文本（字符串）

    -------------------------------------------------------------------
    Python 基础知识点：dict.get() 提供默认值
    -------------------------------------------------------------------
    ds_config.get("model_name", "deepseek-v4-flash")
    如果配置中有 model_name 就用它，没有就用默认值。
    """
    ds_config = config["deepseek"]

    # 调用 OpenAI 兼容的 Chat Completions API
    # messages 列表结构：[{role, content}, ...]
    #   - system 消息：设定 AI 的行为规则
    #   - user 消息：用户的实际问题 + 上下文信息
    response = client.chat.completions.create(
        model=ds_config.get("model_name", "deepseek-v4-flash"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=ds_config.get("temperature", 0.2),  # 温度：0-2，越低越确定，越高越有创意
        max_tokens=ds_config.get("max_tokens", 1200),    # 最大输出长度（token 数）
        stream=True,  # 启用流式模式
    )

    # emitted 标记：记录流式响应是否产出了任何有效文本
    # 某些情况下流式 API 可能返回空响应（如模型暂时不可用），
    # 此时需要回退到非流式调用
    emitted = False

    # 遍历流式响应的每个 chunk
    # response 是一个可迭代对象，每次迭代获取服务端刚生成的一小段文本
    for chunk in response:
        content = _extract_stream_chunk_text(chunk)
        if content:
            emitted = True
            yield content  # 把文本块「产出」给调用方

    # 流式回调没有产出任何文本 → 用非流式 API 兜底
    if not emitted:
        fallback_text = _chat_completion_non_stream(
            client=client,
            config=config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if fallback_text:
            yield fallback_text


# ===========================================================================
# 非流式 API 兜底调用
# ===========================================================================
# 某些 LLM 服务在流式模式下可能返回空响应（已知的 API 行为）。
# 非流式调用作为兜底：stream=False，等完整回答生成后一次性返回。

def _chat_completion_non_stream(
    client,
    config: dict,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    用非流式模式调用 API 作为兜底。

    与流式调用的唯一区别是 stream=False，
    API 会等完整回答生成后一次性返回。
    """
    ds_config = config["deepseek"]
    response = client.chat.completions.create(
        model=ds_config.get("model_name", "deepseek-v4-flash"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=ds_config.get("temperature", 0.2),
        max_tokens=ds_config.get("max_tokens", 1200),
        stream=False,  # 非流式模式
    )
    if not response.choices:
        return ""
    message = response.choices[0].message
    # getattr(obj, "content", None) 安全获取属性，不存在时返回 None
    return _normalize_message_content(getattr(message, "content", None))


# ===========================================================================
# 文本提取与规范化工具函数
# ===========================================================================

def _extract_stream_chunk_text(chunk) -> str:
    """
    从流式响应的一个 chunk 中提取文本内容。

    流式响应中的 chunk 结构：
        chunk.choices[0].delta.content         ← 普通文本
        chunk.choices[0].delta.reasoning_content ← 推理内容（部分模型如 DeepSeek-R1 有）

    本函数优先取 content，没有的话取 reasoning_content。

    -------------------------------------------------------------------
    Python 基础知识点：getattr() 安全获取属性
    -------------------------------------------------------------------
    getattr(obj, "attr_name", default_value)
    尝试取 obj.attr_name，如果属性不存在则返回 default_value。
    比直接 obj.attr_name 安全，不会因为属性缺失而报 AttributeError。
    """
    # 检查 chunk 是否有 choices 属性
    if not getattr(chunk, "choices", None):
        return ""

    delta = chunk.choices[0].delta

    # 优先取普通文本内容
    content = _normalize_message_content(getattr(delta, "content", None))
    if content:
        return content

    # 其次取推理内容（DeepSeek-R1 等推理模型的 thinking 输出）
    return _normalize_message_content(getattr(delta, "reasoning_content", None))


def _normalize_message_content(content) -> str:
    """
    将各种格式的消息内容统一转为纯文本字符串。

    不同 LLM API 返回的内容格式可能不同：
    - 直接是字符串：直接返回
    - 是列表：每个元素可能是字符串、字典（含 text/content 键）或对象
    - 其他类型：转为字符串

    -------------------------------------------------------------------
    Python 基础知识点：isinstance() 类型检查
    -------------------------------------------------------------------
    isinstance(obj, str) 检查 obj 是否为 str 类型。
    在 Python 中通常用 isinstance 而不是 type(obj) == str，
    因为 isinstance 支持继承检查（子类也会返回 True）。
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    # 列表格式的内容（部分 API 返回数组形式的消息）
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            # 字典格式：取 "text" 或 "content" 键
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if text:
                    parts.append(str(text))
                continue
            # 对象格式：取 .text 或 .content 属性
            text = getattr(item, "text", None) or getattr(item, "content", None)
            if text:
                parts.append(str(text))
        return "".join(parts)  # 拼接成完整字符串
    # 其他类型直接转字符串
    return str(content)
