"""中国象棋 LLM Agent。"""

from __future__ import annotations

import board_serializer
import deepseek_client
from board import ChineseChessBoard
from pikafish_engine import PikafishEngine


SYSTEM_PROMPT = """
你是一位逻辑清楚、解释严谨、表达自然的中国象棋老师。

你会收到：
1. 用户问题
2. 当前中国象棋棋盘信息
3. Pikafish 给出的最优走法和搜索结果

规则：
1. 必须把 Pikafish 的 best move 视为当前最可信的推荐走法。
2. 先直接回答用户问题，再解释推荐走法。
3. 解释要讲清楚“这步为什么好”，包括进攻、防守、先手、子力配合、将帅安全中的 relevant 部分。
4. 如果用户问题很随意，比如“下一步呢？”“帮我看看”，也要给出完整分析。
5. 不要编造棋步；推荐走法必须与给出的 best move 一致。
6. 用中文回答，逻辑清楚，条理分段，避免空话。
7. 不要输出 Markdown 标记，不要使用 ###、**、`- ` 这类格式符号。
8. 直接输出干净的自然语言段落与简单编号。
9. 回答格式尽量稳定：
   - 先给“推荐走法”
   - 再给“原因分析”
   - 最后给“你接下来可以关注什么”
""".strip()


def ask_xiangqi_agent(
    board: ChineseChessBoard,
    user_question: str,
    move_history: list[str],
    analysis_engine: PikafishEngine,
    stream_callback=None,
) -> dict:
    config = deepseek_client.load_config()
    client = deepseek_client.create_client(config)

    engine_analysis = analysis_engine.analyze_position(board)
    serialized = board_serializer.serialize_board(
        board=board,
        move_history=move_history,
        engine_analysis=engine_analysis,
    )
    user_prompt = board_serializer.build_user_prompt(serialized, user_question)

    final_text = ""
    for chunk in deepseek_client.chat_completion(
        client=client,
        config=config,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    ):
        final_text += chunk
        if stream_callback is not None:
            stream_callback(chunk)

    return {
        "response": final_text,
        "engine_analysis": engine_analysis,
        "serialized_board": serialized,
    }
