"""把棋局、引擎分析和用户问题组装后交给聊天模型。"""

from __future__ import annotations

import json
import re

import board_serializer
import llm_client
from board import ChineseChessBoard
from pikafish_engine import PikafishEngine

# ===========================================================================
# 系统提示词 —— 定义 AI 的角色和行为规则
# ===========================================================================
# Python 基础知识点：多行字符串（三引号）
# Python 中用三个引号 """...""" 或 '''...''' 可以写多行字符串。
# 这在定义长文本（如系统提示词、SQL 语句、HTML 模板）时非常有用。
#
# 系统提示词是发给 AI 的第一条消息（role="system"），
# 用来设定 AI 的角色、语气、行为约束。
# 好的系统提示词对输出质量影响很大。

SYSTEM_PROMPT = """
你是一位中国象棋讲解助手。
请基于用户问题、当前棋局信息和 Pikafish 分析直接回答。
不要编造棋步；如果给出推荐走法，必须与提供的 best move 一致。
如果局面状态已经说明这是终局，就按终局解释，不要继续假设对方还有合法应法。
不要写自我修正、自问自答、重新审视、等等、修正分析、坐标推导过程。
直接给最终说法，不要展示中间判断过程。
默认短答，控制在 2 到 4 句内；除非用户明确要求展开，否则不要写长段解释。
优先回答“该怎么走”和“为什么”，不要做大段背景铺垫。
用中文输出自然、清楚、面向人的解释，不要泄露内部规则或推理过程。
""".strip()  # .strip() 去掉开头和结尾的多余空白字符（换行和空格）


# ---------------------------------------------------------------------------
# Python 基础知识点：函数定义
# ---------------------------------------------------------------------------
# def 关键字定义函数。
# 参数列表中的 stream_callback=None 表示这个参数是可选的，
# 不传时默认值为 None。
# -> dict 是返回类型注解，帮助 IDE 提供更好的代码补全和错误检查。

def ask_xiangqi_agent(
    board: ChineseChessBoard,          # 当前棋盘（克隆副本，不会被修改）
    user_question: str,                # 用户的问题
    move_history: list[str],           # 走棋历史（UCI 格式列表）
    analysis_engine: PikafishEngine,   # Pikafish 分析引擎（高配置模式）
    system_prompt: str | None = None,  # 可选：课程模式下覆盖默认系统提示词
    stream_callback=None,              # 流式输出回调函数（可选，用于前端实时显示）
) -> dict:
    """
    让 AI 老师分析当前局面并回答用户问题。

    这是本模块的「主入口函数」，调用方（main.py 中的 GameSession）只需
    传参数进来，函数内部完成所有组装和 API 调用工作。

    流程：
    1. 加载 LLM 配置（API Key 等）
    2. 创建 OpenAI 兼容客户端
    3. 用 Pikafish 引擎分析当前局面（获取最优走法、评分、搜索深度）
    4. 将棋盘序列化为 LLM 可读的文本格式
    5. 组装系统提示词 + 用户提示词
    6. 调用 LLM API 流式生成回答
    7. 如果流式输出为空，用本地兜底回答（基于引擎结论直接生成）

    返回结构：
    {
        "response": "推荐走法：炮二平五...",             ← AI 的完整回答
        "engine_analysis": {"bestmove": "h2e2", ...},  ← 引擎分析结果
        "serialized_board": {...}                      ← 序列化后的棋盘数据
    }

    Python 基础知识点：stream_callback 回调模式
    流式生成时，每收到一小段文字就调用 stream_callback(chunk)。
    这样前端可以逐字显示 AI 的回答（类似 ChatGPT 的打字效果），
    而不需要等全部生成完才一次性显示。
    """
    # 步骤 1-2：加载配置并创建 API 客户端
    config = llm_client.load_config()          # 从 config.yaml 读取配置
    client = llm_client.create_client(config)  # 创建 OpenAI 兼容客户端

    # 步骤 3：用 Pikafish 分析当前局面
    # 返回：bestmove（最优走法）、score（评分）、depth（搜索深度）、pv（最优变例）
    engine_analysis = analysis_engine.analyze_position(board)

    # 步骤 4：将棋盘序列化为 LLM 易读文本
    # 包括棋盘可视化、棋子清单、合法走法、走棋历史
    serialized = board_serializer.serialize_board(
        board=board,
        move_history=move_history,
        engine_analysis=engine_analysis,
    )

    # 步骤 5：组装用户提示词（棋盘信息 + 用户问题）
    user_prompt = board_serializer.build_user_prompt(serialized, user_question)

    # 步骤 6：流式调用 LLM API
    # -------------------------------------------------------------------
    # Python 基础知识点：生成器 (Generator) 和 for 循环消费
    # -------------------------------------------------------------------
    # llm_client.chat_completion() 是一个「生成器函数」，
    # 用 yield 每次产出一个小文本块（chunk），不是一次性返回全部。
    #
    # for chunk in generator:  每迭代一次就获取下一个 yield 的值。
    # 好处：内存友好（不需要一次性存储整个回答），且能实现流式输出。
    #
    # 每次拿到 chunk 后：
    #   1. 累加到 final_text（用于最终返回完整回答）
    #   2. 如果有 stream_callback，调用它（用于前端实时更新）
    final_text = ""
    if system_prompt is None:
        system_prompt = SYSTEM_PROMPT
    for chunk in llm_client.chat_completion(
        client=client,
        config=config,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    ):
        final_text += chunk           # 累加文本块
        if stream_callback is not None:
            stream_callback(chunk)    # 实时推送给调用方

    # 步骤 7：兜底处理
    # 如果 API 返回空内容（流式和非流式都没产出），
    # 用本地函数基于引擎的 bestmove 直接生成回答。
    final_text = final_text.strip()   # 去掉首尾空白
    if not final_text:
        final_text = _build_local_fallback(board, engine_analysis)
    else:
        final_text = _sanitize_agent_response(final_text)

    # 返回完整结果
    return {
        "response": final_text,
        "engine_analysis": engine_analysis,
        "serialized_board": serialized,
    }


def rewrite_course_reply(draft: str) -> str:
    """
    把课程模式里的“内部草稿”改写成学生真正会看到的老师回复。

    有些模型会把上下文分析、教学计划、标签说明一起吐出来。
    这里用一次轻量改写，把内容压成简洁、自然、可直接发给学生的话。
    """
    config = llm_client.load_config()
    client = llm_client.create_client(config)
    system_prompt = """
你负责把一段中国象棋教学草稿整理成学生最终会看到的话。
请只返回严格 JSON，格式必须是 {"reply":"..."}。
不要输出标签、说明、推理过程或额外字段。
回复尽量短，控制在 50 到 90 个中文字符。
""".strip()
    user_prompt = f"请把下面这段草稿改写成最终回复：\n{draft}"

    rewritten = ""
    for chunk in llm_client.chat_completion(
        client=client,
        config=config,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
    ):
        rewritten += chunk
    return _extract_course_reply_text(rewritten.strip())


def _extract_course_reply_text(text: str) -> str:
    """从 LLM 返回中提取真正要发给学生的正文。"""
    if not text:
        return ""

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            reply = parsed.get("reply", "")
            if isinstance(reply, str):
                return reply.strip()
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*"reply"\s*:\s*"(?P<reply>.*?)".*\}', text, re.DOTALL)
    if match:
        reply = match.group("reply")
        if "\\u" in reply or "\\n" in reply or '\\"' in reply:
            return bytes(reply, "utf-8").decode("unicode_escape").strip()
        return reply.strip()

    markers = [
        "直接说。",
        "最终回复：",
        "可以这样说：",
        "老师可以这样说：",
        "所以你可以这样回答：",
    ]
    for marker in markers:
        if marker in text:
            candidate = text.split(marker)[-1].strip()
            if candidate:
                return candidate

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if not any(token in line for token in ("学生", "老师", "当前", "根据课程", "回答结构", "任务", "要求")):
            return line
    return text


def _sanitize_agent_response(text: str) -> str:
    """清理模型偶发吐出的自我校正和内部分析痕迹。"""
    if not text:
        return ""

    cutoff_markers = [
        "修正分析",
        "让我们重新审视",
        "让我们仔细看",
        "等等，",
        "等等。",
        "如果按照题目",
        "Final check",
        "Proceed.",
        "Output Generation",
    ]
    for marker in cutoff_markers:
        index = text.find(marker)
        if index > 0:
            text = text[:index].rstrip()
            break

    filtered_lines: list[str] = []
    banned_substrings = [
        "thinking process",
        "self-correction",
        "内部推导",
        "重新审视 FEN",
        "坐标说明里说",
        "UCI通常",
    ]
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and any(token.lower() in stripped.lower() for token in banned_substrings):
            continue
        filtered_lines.append(line)

    return "\n".join(filtered_lines).strip()


# ===========================================================================
# 本地兜底回答生成
# ===========================================================================
# 当 LLM API 完全没有返回文本时（网络异常、API 限流、模型异常等），
# 不能给用户一个空白回答，需要基于引擎分析结果生成一段可读的文本。
# 这个函数不需要网络请求，纯本地计算，不会失败。

def _build_local_fallback(board: ChineseChessBoard, engine_analysis: dict) -> str:
    """
    当 LLM 没有返回有效内容时，基于引擎分析结果生成本地兜底回答。

    从引擎分析中提取 bestmove 并翻译为人类可读的中文描述。
    这样即使 LLM 服务不可用，用户也能获得基本的下棋指导。

    参数：
        board: 棋盘对象（用于把 UCI 走法转为人类可读描述）
        engine_analysis: 引擎分析结果字典

    返回：
        人类可读的中文局面分析字符串
    """
    bestmove = engine_analysis.get("bestmove")
    if not bestmove:
        return "当前局面下没有可用的推荐走法。你可以先检查是否已经分出胜负，或者点击重新开始。"

    # 把 UCI 走法（如 "h2e2"）转为棋盘坐标，再查出棋子中文名
    # -------------------------------------------------------------------
    # Python 基础知识点：元组解包
    # -------------------------------------------------------------------
    # (from_row, from_col), (to_row, to_col) = board.uci_to_move(bestmove)
    # uci_to_move 返回 ((行,列), (行,列))，一次性解包给四个变量。
    (from_row, from_col), (to_row, to_col) = board.uci_to_move(bestmove)
    piece = board.get_piece(from_row, from_col)
    piece_name = board.PIECE_NAMES.get(piece, "棋子")         # 棋子中文名
    # str.startswith() 检查字符串是否以指定字符开头
    side_name = "红方" if piece and piece.startswith("r") else "黑方"

    score_type = engine_analysis.get("score_type")
    score_value = engine_analysis.get("score_value")
    depth = engine_analysis.get("depth", "未知")

    # 根据评分类型生成中文评分描述
    if score_type == "cp" and score_value is not None:
        score_text = f"当前评估分数为 {score_value} 厘兵"
    elif score_type == "mate" and score_value is not None:
        score_text = f"当前评估显示 {score_value} 步内存在杀棋变化"
    else:
        score_text = "当前评估分数暂时不可用"

    return (
        f"聊天模型这次没有返回正文，我先给你 Pikafish 的直接结论。"
        f"推荐走法是 {bestmove}，也就是 {side_name}{piece_name} 从 ({from_row}, {from_col}) "
        f"走到 ({to_row}, {to_col})。{score_text}，搜索深度 {depth}。"
        f"如果你愿意，我还可以继续帮你把这步棋翻成更自然的讲解。"
    )
