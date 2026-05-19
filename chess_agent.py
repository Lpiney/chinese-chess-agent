"""把棋局、引擎分析和用户问题组装后交给聊天模型。"""

from __future__ import annotations

import board_serializer
import deepseek_client
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
你是一位逻辑清楚、解释严谨、表达自然的中国象棋老师。

你会收到：
1. 用户问题
2. 当前中国象棋棋盘信息
3. Pikafish 给出的最优走法和搜索结果

规则：
1. 必须把 Pikafish 的 best move 视为当前最可信的推荐走法。
2. 先直接回答用户问题，再解释推荐走法。
3. 解释要讲清楚"这步为什么好"，包括进攻、防守、先手、子力配合、将帅安全中的 relevant 部分。
4. 如果用户问题很随意，比如"下一步呢？""帮我看看"，也要给出完整分析。
5. 不要编造棋步；推荐走法必须与给出的 best move 一致。
6. 用中文回答，逻辑清楚，条理分段，避免空话。
7. 不要输出 Markdown 标记，不要使用 ###、**、`- ` 这类格式符号。
8. 直接输出干净的自然语言段落与简单编号。
9. 回答格式尽量稳定：
   - 先给"推荐走法"
   - 再给"原因分析"
   - 最后给"你接下来可以关注什么"
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
    stream_callback=None,              # 流式输出回调函数（可选，用于前端实时显示）
) -> dict:
    """
    让 AI 老师分析当前局面并回答用户问题。

    这是本模块的「主入口函数」，调用方（main.py 中的 GameSession）只需
    传参数进来，函数内部完成所有组装和 API 调用工作。

    流程：
    1. 加载 DeepSeek 配置（API Key 等）
    2. 创建 OpenAI 兼容客户端
    3. 用 Pikafish 引擎分析当前局面（获取最优走法、评分、搜索深度）
    4. 将棋盘序列化为 LLM 可读的文本格式
    5. 组装系统提示词 + 用户提示词
    6. 调用 DeepSeek API 流式生成回答
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
    config = deepseek_client.load_config()          # 从 config.yaml 读取配置
    client = deepseek_client.create_client(config)  # 创建 OpenAI 兼容客户端

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

    # 步骤 6：流式调用 DeepSeek API
    # -------------------------------------------------------------------
    # Python 基础知识点：生成器 (Generator) 和 for 循环消费
    # -------------------------------------------------------------------
    # deepseek_client.chat_completion() 是一个「生成器函数」，
    # 用 yield 每次产出一个小文本块（chunk），不是一次性返回全部。
    #
    # for chunk in generator:  每迭代一次就获取下一个 yield 的值。
    # 好处：内存友好（不需要一次性存储整个回答），且能实现流式输出。
    #
    # 每次拿到 chunk 后：
    #   1. 累加到 final_text（用于最终返回完整回答）
    #   2. 如果有 stream_callback，调用它（用于前端实时更新）
    final_text = ""
    for chunk in deepseek_client.chat_completion(
        client=client,
        config=config,
        system_prompt=SYSTEM_PROMPT,
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

    # 返回完整结果
    return {
        "response": final_text,
        "engine_analysis": engine_analysis,
        "serialized_board": serialized,
    }


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
