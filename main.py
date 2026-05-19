"""中国象棋 Web 应用入口。"""

from __future__ import annotations

import atexit
import threading
import webbrowser
from dataclasses import dataclass, field

from flask import Flask, jsonify, render_template, request

import chess_agent
from board import ChineseChessBoard
from pikafish_engine import PikafishEngine


def create_app() -> Flask:
    app = Flask(__name__)
    session = GameSession()

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/state")
    def get_state():
        return jsonify(session.serialize_state())

    @app.get("/api/legal-moves")
    def get_legal_moves():
        row = int(request.args["row"])
        col = int(request.args["col"])
        moves = session.get_valid_moves(row, col)
        return jsonify({"moves": [{"row": move[0], "col": move[1]} for move in moves]})

    @app.post("/api/move")
    def post_move():
        payload = request.get_json(force=True)
        from_row = int(payload["from_row"])
        from_col = int(payload["from_col"])
        to_row = int(payload["to_row"])
        to_col = int(payload["to_col"])
        result = session.apply_player_move(from_row, from_col, to_row, to_col)
        return jsonify(result)

    @app.post("/api/reset")
    def post_reset():
        return jsonify(session.reset())

    @app.post("/api/level")
    def post_level():
        payload = request.get_json(force=True)
        result = session.set_level(payload["level"])
        return jsonify(result)

    @app.post("/api/chat")
    def post_chat():
        payload = request.get_json(force=True)
        result = session.ask_agent(payload["message"])
        return jsonify(result)

    atexit.register(session.close)
    return app


@dataclass
class GameSession:
    """维护单局游戏状态。"""

    board: ChineseChessBoard = field(default_factory=ChineseChessBoard)
    bot_engine: PikafishEngine = field(default_factory=lambda: PikafishEngine(level="medium"))
    analysis_engine: PikafishEngine = field(default_factory=lambda: PikafishEngine(level="master"))
    move_history: list[str] = field(default_factory=list)
    level: str = "medium"
    lock: threading.Lock = field(default_factory=threading.Lock)

    def serialize_state(self) -> dict:
        with self.lock:
            board_rows: list[list[str | None]] = []
            for row in range(self.board.ROWS):
                board_rows.append([self.board.get_piece(row, col) for col in range(self.board.COLS)])
            return {
                "board": board_rows,
                "piece_names": self.board.PIECE_NAMES,
                "current_player": self.board.current_player,
                "winner": self.board.winner,
                "move_history": list(self.move_history),
                "level": self.level,
                "status_text": self._status_text(),
            }

    def get_valid_moves(self, row: int, col: int) -> list[tuple[int, int]]:
        with self.lock:
            if self.board.winner is not None or self.board.current_player != "r":
                return []
            return self.board.get_valid_moves(row, col)

    def apply_player_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> dict:
        with self.lock:
            if self.board.winner is not None:
                return {"ok": False, "error": "对局已经结束。"}
            if self.board.current_player != "r":
                return {"ok": False, "error": "当前不是红方回合。"}

            player_piece = self.board.get_piece(from_row, from_col)
            if player_piece is None:
                return {"ok": False, "error": "起点没有棋子。"}

            player_uci = self.board.move_to_uci(from_row, from_col, to_row, to_col)
            try:
                self.board.move_piece(from_row, from_col, to_row, to_col)
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}

            self.move_history.append(player_uci)
            events = [
                {
                    "side": "player",
                    "piece": player_piece,
                    "from": [from_row, from_col],
                    "to": [to_row, to_col],
                }
            ]

            if self.board.winner is None and self.board.has_any_valid_move(self.board.current_player):
                bestmove = self.bot_engine.get_best_move(self.board)
                if bestmove is not None:
                    (bot_from_row, bot_from_col), (bot_to_row, bot_to_col) = self.board.uci_to_move(bestmove)
                    bot_piece = self.board.get_piece(bot_from_row, bot_from_col)
                    self.board.move_piece(bot_from_row, bot_from_col, bot_to_row, bot_to_col)
                    self.move_history.append(bestmove)
                    events.append(
                        {
                            "side": "bot",
                            "piece": bot_piece,
                            "from": [bot_from_row, bot_from_col],
                            "to": [bot_to_row, bot_to_col],
                        }
                    )

            return {
                "ok": True,
                "events": events,
                "state": self.serialize_state_unlocked(),
            }

    def reset(self) -> dict:
        with self.lock:
            self.board = ChineseChessBoard()
            self.move_history = []
            self.bot_engine.new_game()
            self.analysis_engine.new_game()
            return {"ok": True, "state": self.serialize_state_unlocked()}

    def set_level(self, level: str) -> dict:
        level = level.lower()
        with self.lock:
            self.level = level
            self.bot_engine.set_level(level)
            return {"ok": True, "state": self.serialize_state_unlocked()}

    def ask_agent(self, message: str) -> dict:
        board_snapshot = self.board.clone()
        move_history = list(self.move_history)
        result = chess_agent.ask_xiangqi_agent(
            board=board_snapshot,
            user_question=message,
            move_history=move_history,
            analysis_engine=self.analysis_engine,
        )
        return {
            "ok": True,
            "message": result["response"],
            "engine_analysis": result["engine_analysis"],
        }

    def serialize_state_unlocked(self) -> dict:
        board_rows: list[list[str | None]] = []
        for row in range(self.board.ROWS):
            board_rows.append([self.board.get_piece(row, col) for col in range(self.board.COLS)])
        return {
            "board": board_rows,
            "piece_names": self.board.PIECE_NAMES,
            "current_player": self.board.current_player,
            "winner": self.board.winner,
            "move_history": list(self.move_history),
            "level": self.level,
            "status_text": self._status_text(),
        }

    def _status_text(self) -> str:
        if self.board.winner == "r":
            return "对局结束，红方获胜。"
        if self.board.winner == "b":
            return "对局结束，黑方获胜。"
        if self.board.current_player == "r":
            return "轮到红方行棋。"
        return "轮到黑方行棋。"

    def close(self) -> None:
        self.bot_engine.stop()
        self.analysis_engine.stop()


def open_browser() -> None:
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    app = create_app()
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
