"""将中国象棋棋局整理成 LLM 易读文本。"""

from __future__ import annotations

from board import ChineseChessBoard


def serialize_board(
    board: ChineseChessBoard,
    move_history: list[str] | None = None,
    engine_analysis: dict | None = None,
) -> dict:
    move_history = move_history or []
    engine_analysis = engine_analysis or {}
    visual_rows: list[str] = []
    piece_lines: list[str] = []

    for row in range(board.ROWS):
        display_cells: list[str] = []
        for col in range(board.COLS):
            piece = board.get_piece(row, col)
            display_cells.append(board.PIECE_NAMES.get(piece, "・"))
            if piece is not None:
                camp = "红方" if piece[0] == "r" else "黑方"
                piece_lines.append(f"- {camp}{board.PIECE_NAMES[piece]} 在 ({row}, {col})")
        visual_rows.append(f"{row}: " + " ".join(display_cells))

    side_to_move = "红方" if board.current_player == "r" else "黑方"
    legal_moves: list[str] = []
    for source, target in board.get_all_valid_moves(board.current_player)[:40]:
        legal_moves.append(board.move_to_uci(source[0], source[1], target[0], target[1]))

    return {
        "fen": board.to_fen(),
        "side_to_move": side_to_move,
        "visual_board": "\n".join(visual_rows),
        "piece_list": "\n".join(piece_lines),
        "move_history": move_history,
        "legal_moves": legal_moves,
        "engine_analysis": engine_analysis,
    }


def build_user_prompt(serialized: dict, user_question: str) -> str:
    engine = serialized["engine_analysis"]
    score_text = _format_engine_score(engine.get("score_type"), engine.get("score_value"))
    pv_text = ", ".join(engine.get("pv", [])[:6]) if engine.get("pv") else "无"
    legal_moves_text = ", ".join(serialized["legal_moves"]) if serialized["legal_moves"] else "无"
    move_history_text = ", ".join(serialized["move_history"]) if serialized["move_history"] else "无"

    return f"""
用户问题：
{user_question}

当前轮到：
{serialized["side_to_move"]}

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


def _format_engine_score(score_type: str | None, score_value: int | None) -> str:
    if score_type == "cp" and score_value is not None:
        return f"{score_value} centipawns"
    if score_type == "mate" and score_value is not None:
        return f"mate {score_value}"
    return "未知"
