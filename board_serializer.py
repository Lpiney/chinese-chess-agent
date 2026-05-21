"""
棋盘状态序列化 —— 将程序内部数据结构转为大语言模型可读的文本。

本模块承担「翻译官」角色：
- 将二维数组 + 棋子编码 → 带中文描述的可视化文本
- 将引擎分析结果 → 人类可读的描述
- 组装最终发给 LLM 的完整提示词

为什么要序列化？
大语言模型只能理解文本（自然语言），它无法直接读取 Python 对象。
所以我们需要把棋盘状态「翻译」成它看得懂的格式。
"""

from __future__ import annotations

from board import ChineseChessBoard


# ---------------------------------------------------------------------------
# Python 基础知识点：函数默认参数值
# ---------------------------------------------------------------------------
# move_history: list[str] | None = None 中，
# | None 表示这个参数可以接受 None 值。
# 默认值是 None 而不是 []，
# 因为 Python 的默认参数值只在函数定义时计算一次。
# 如果用 []，每次调用都会共享同一个列表对象，
# 这在多线程或多处调用时会导致意外的数据污染。

def serialize_board(
    board: ChineseChessBoard,
    move_history: list[str] | None = None,
    engine_analysis: dict | None = None,
) -> dict:
    """
    将棋盘状态转换为 LLM 可读的字典格式。

    参数：
        board: 棋盘对象
        move_history: 走棋历史（UCI 格式列表），可选
        engine_analysis: 引擎分析结果字典，可选

    返回的字典包含以下字段：
    - fen: FEN 格式棋盘字符串
    - side_to_move: 中文的当前走棋方（"红方"/"黑方"）
    - visual_board: 棋盘可视化文本（行列标注的棋子布局）
    - piece_list: 棋子清单（每行一个棋子的位置和阵营描述）
    - move_history: 走棋历史
    - legal_moves: 当前合法走法列表（UCI 格式）
    - engine_analysis: 引擎分析结果（透传）

    -------------------------------------------------------------------
    Python 基础知识点：or 运算符的短路求值
    -------------------------------------------------------------------
    move_history = move_history or []
    这个写法的意思是：如果 move_history 是 None（或其他空值），就用 [] 代替。
    这是 Python 中常见的写法，利用了 or 的「短路」特性：
    如果左边是真值，直接返回左边；否则返回右边。
    """
    move_history = move_history or []                 # None → 空列表
    engine_analysis = engine_analysis or {}           # None → 空字典

    visual_rows: list[str] = []   # 存储每一行的文本表示
    piece_lines: list[str] = []   # 存储每个棋子的描述行

    # 遍历棋盘 10 行 x 9 列
    for row in range(board.ROWS):
        display_cells: list[str] = []
        for col in range(board.COLS):
            piece = board.get_piece(row, col)
            # 有棋子就用中文名，没棋子就用 "・"（全角中点，视觉上对齐更好看）
            display_cells.append(board.PIECE_NAMES.get(piece, "・"))
            if piece is not None:
                # 构建棋子描述：阵营 + 中文名 + 坐标
                camp = "红方" if piece[0] == "r" else "黑方"
                square = board.coord_to_uci_square(row, col)
                piece_lines.append(f"- {camp}{board.PIECE_NAMES[piece]} 在 {square}")
        # 每行格式："行号: 棋子1 棋子2 ..."
        visual_rows.append(f"{row}: " + " ".join(display_cells))

    # 当前走棋方的中文描述
    side_to_move = "红方" if board.current_player == "r" else "黑方"

    # 获取合法走法（最多取前 40 个，发给 LLM 的信息量适中）
    # -------------------------------------------------------------------
    # Python 基础知识点：列表切片 [:40]
    # -------------------------------------------------------------------
    # some_list[:40] 表示取列表的前 40 个元素。
    # 如果列表不足 40 个元素，也不会报错，只返回所有元素。
    # 切片语法：[start:stop:step]
    #   - start 省略 = 从开头
    #   - stop 省略 = 到末尾
    #   - step 省略 = 步长 1
    legal_moves: list[str] = []
    for source, target in board.get_all_valid_moves(board.current_player)[:40]:
        # 把坐标 (r,c) 转为 UCI 格式（如 "a3a4"）
        legal_moves.append(board.move_to_uci(source[0], source[1], target[0], target[1]))

    return {
        "fen": board.to_fen(),
        "side_to_move": side_to_move,
        "winner": board.winner,
        "position_status": _build_position_status(board),
        "coordinate_guide": _build_coordinate_guide(),
        "visual_board": "\n".join(visual_rows),
        "piece_list": "\n".join(piece_lines),
        "move_history": move_history,
        "legal_moves": legal_moves,
        "engine_analysis": engine_analysis,
    }


def build_user_prompt(serialized: dict, user_question: str) -> str:
    """
    组装最终发送给 LLM 的用户提示词。

    将序列化的棋盘数据和用户问题按照固定模板拼接，
    形成一个结构化的、信息完整的提示词。

    参数：
        serialized: serialize_board 返回的字典
        user_question: 用户原始问题

    返回：
        完整的提示词字符串
    """
    # === 解析引擎分析结果 ===
    engine = serialized["engine_analysis"]

    # 格式化评分：centipawns（厘兵）或 checkmate（杀棋步数）
    score_text = _format_engine_score(engine.get("score_type"), engine.get("score_value"))

    # PV (Principal Variation)：引擎算出的最优变例（即推荐的前几步走法）
    # 取前 6 个走法，太多反而让 LLM 信息过载
    pv_text = ", ".join(engine.get("pv", [])[:6]) if engine.get("pv") else "无"

    # 合法走法、走棋历史 —— 空列表时显示"无"而不是空白
    legal_moves_text = ", ".join(serialized["legal_moves"]) if serialized["legal_moves"] else "无"
    move_history_text = ", ".join(serialized["move_history"]) if serialized["move_history"] else "无"

    # -------------------------------------------------------------------
    # Python 基础知识点：f-string 多行文本
    # -------------------------------------------------------------------
    # f"""...""" 是格式化的多行字符串。
    # 大括号里的变量/表达式会被替换成对应的值。
    # .strip() 去掉首尾空白，避免提示词开头有多余空行。
    return f"""
用户问题：
{user_question}

当前轮到：
{serialized["side_to_move"]}

局面状态：
{serialized["position_status"]}

坐标说明：
{serialized["coordinate_guide"]}

当前棋盘 FEN：
{serialized["fen"]}

棋盘可视化：
{serialized["visual_board"]}

棋子清单：
{serialized["piece_list"]}

走子历史：
{move_history_text}

当前合法走法（UCI）：
{legal_moves_text}

Pikafish 的结论：
- best move: {engine.get("bestmove", "无")}
- score: {score_text}
- search depth: {engine.get("depth", "未知")}
- pv: {pv_text}
""".strip()


def _build_position_status(board: ChineseChessBoard) -> str:
    """把当前局面转成一句稳定状态描述。"""
    if board.winner == "r":
        return "终局：红方已获胜。"
    if board.winner == "b":
        return "终局：黑方已获胜。"
    if not board.has_any_valid_move(board.current_player):
        side = "红方" if board.current_player == "r" else "黑方"
        return f"终局：{side}当前没有任何合法走法。"
    return "对局进行中。"


def _build_coordinate_guide() -> str:
    """给模型提供清楚的 UCI 坐标映射。"""
    return (
        "棋盘采用 UCI 坐标：列从左到右为 a-i，行从下到上为 0-9。"
        "例如底线红帅初始位置是 e0；如果看到 e9，表示顶线中路那一格。"
        "回答时优先使用这套 UCI 坐标，不要混用内部 row/col 说明。"
    )


def _format_engine_score(score_type: str | None, score_value: int | None) -> str:
    """
    将引擎评分转为人类可读文本。

    棋类引擎的评分有两种类型：
    - "cp" (centipawns)：以「厘兵」为单位的局面优势评分
      正值表示红方优势，负值表示黑方优势
      例如：+100 = 红方约多一个兵的优势
    - "mate"：杀棋步数
      正值表示红方还有 N 步将杀黑方
      负值表示黑方还有 N 步将杀红方
    """
    if score_type == "cp" and score_value is not None:
        return f"{score_value} centipawns"
    if score_type == "mate" and score_value is not None:
        return f"mate {score_value}"
    return "未知"
