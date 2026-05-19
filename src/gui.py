"""中国象棋桌面图形界面。"""

from __future__ import annotations

import tkinter as tk
import threading
from tkinter import messagebox
from tkinter import ttk

from src.board import ChineseChessBoard
from src.pikafish_engine import PikafishEngine


class ChineseChessGUI:
    """基于 tkinter 的中国象棋桌面界面。"""

    CELL_SIZE = 64
    MARGIN = 48
    PIECE_RADIUS = 24
    BOARD_COLOR = "#ead7a4"
    LINE_COLOR = "#5c3b1e"
    RED_COLOR = "#b8342f"
    BLACK_COLOR = "#222222"
    SELECT_COLOR = "#f5b301"
    MOVE_HINT_COLOR = "#2f9e44"
    CAPTURE_HINT_COLOR = "#d6336c"
    LAST_MOVE_COLOR = "#74c0fc"
    BOT_COLOR = "b"
    ANIMATION_FRAMES = 10
    ANIMATION_INTERVAL_MS = 22
    LEVEL_NAMES = ["Beginner", "Medium", "Master"]
    LEVEL_NAME_TO_KEY = {"Beginner": "beginner", "Medium": "medium", "Master": "master"}

    def __init__(self) -> None:
        self.board = ChineseChessBoard()
        self.engine = PikafishEngine(level="medium")
        self.root = tk.Tk()
        self.root.title("中国象棋对战")
        self.root.resizable(False, False)

        self.selected_position: tuple[int, int] | None = None
        self.valid_moves: list[tuple[int, int]] = []
        self.last_move: tuple[tuple[int, int], tuple[int, int]] | None = None
        self.is_animating = False
        self.animation_state: dict[str, object] | None = None
        self.is_bot_thinking = False

        self.status_var = tk.StringVar()
        self.status_var.set("红方先行。请选择一个红方棋子开始对局。")
        self.level_var = tk.StringVar(value="Medium")

        width = self.MARGIN * 2 + self.CELL_SIZE * (self.board.COLS - 1)
        height = self.MARGIN * 2 + self.CELL_SIZE * (self.board.ROWS - 1)

        control_frame = tk.Frame(self.root)
        control_frame.pack(fill="x", padx=12, pady=(12, 0))

        tk.Label(control_frame, text="机器人难度:", font=("PingFang SC", 11)).pack(side="left")
        self.level_box = ttk.Combobox(
            control_frame,
            textvariable=self.level_var,
            values=self.LEVEL_NAMES,
            state="readonly",
            width=12,
        )
        self.level_box.pack(side="left", padx=(8, 12))
        self.level_box.bind("<<ComboboxSelected>>", self._on_level_changed)

        self.restart_button = tk.Button(
            control_frame,
            text="重新开始",
            command=self._restart_game,
            font=("PingFang SC", 11),
        )
        self.restart_button.pack(side="right")

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=self.BOARD_COLOR,
            highlightthickness=0,
        )
        self.canvas.pack(padx=12, pady=(12, 8))
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("PingFang SC", 13),
            anchor="w",
            justify="left",
        )
        self.status_label.pack(fill="x", padx=12, pady=(0, 6))

        self.hint_label = tk.Label(
            self.root,
            text="操作方式：先点击己方棋子，再点击绿色提示位置完成走子。",
            font=("PingFang SC", 11),
            anchor="w",
            fg="#555555",
        )
        self.hint_label.pack(fill="x", padx=12, pady=(0, 12))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._draw()

    def run(self) -> None:
        """启动图形界面。"""
        self.root.mainloop()

    def _draw(self) -> None:
        self.canvas.delete("all")
        self._draw_board()
        self._draw_hints()
        self._draw_pieces()

    def _draw_board(self) -> None:
        left = self.MARGIN
        top = self.MARGIN
        right = self.MARGIN + self.CELL_SIZE * (self.board.COLS - 1)
        bottom = self.MARGIN + self.CELL_SIZE * (self.board.ROWS - 1)

        for col in range(self.board.COLS):
            x = left + col * self.CELL_SIZE
            if col == 0 or col == self.board.COLS - 1:
                self.canvas.create_line(x, top, x, bottom, fill=self.LINE_COLOR, width=2)
            else:
                river_top = top + self.CELL_SIZE * 4
                river_bottom = top + self.CELL_SIZE * 5
                self.canvas.create_line(x, top, x, river_top, fill=self.LINE_COLOR, width=2)
                self.canvas.create_line(x, river_bottom, x, bottom, fill=self.LINE_COLOR, width=2)

        for row in range(self.board.ROWS):
            y = top + row * self.CELL_SIZE
            self.canvas.create_line(left, y, right, y, fill=self.LINE_COLOR, width=2)

        self._draw_palace(left, top)
        self._draw_palace(left, top + self.CELL_SIZE * 7)

        self.canvas.create_text(
            left + self.CELL_SIZE * 1.5,
            top + self.CELL_SIZE * 4.5,
            text="楚 河",
            fill="#7a4a22",
            font=("KaiTi", 24, "bold"),
        )
        self.canvas.create_text(
            left + self.CELL_SIZE * 5.5,
            top + self.CELL_SIZE * 4.5,
            text="汉 界",
            fill="#7a4a22",
            font=("KaiTi", 24, "bold"),
        )

    def _draw_palace(self, left: int, top: int) -> None:
        palace_left = left + self.CELL_SIZE * 3
        palace_top = top
        palace_right = left + self.CELL_SIZE * 5
        palace_bottom = top + self.CELL_SIZE * 2
        self.canvas.create_line(palace_left, palace_top, palace_right, palace_bottom, fill=self.LINE_COLOR, width=2)
        self.canvas.create_line(palace_right, palace_top, palace_left, palace_bottom, fill=self.LINE_COLOR, width=2)

    def _draw_hints(self) -> None:
        if self.last_move is not None:
            for row, col in self.last_move:
                x, y = self._grid_to_pixel(row, col)
                self.canvas.create_rectangle(
                    x - 14,
                    y - 14,
                    x + 14,
                    y + 14,
                    outline=self.LAST_MOVE_COLOR,
                    width=2,
                )

        if self.selected_position is not None:
            row, col = self.selected_position
            x, y = self._grid_to_pixel(row, col)
            self.canvas.create_oval(
                x - self.PIECE_RADIUS - 4,
                y - self.PIECE_RADIUS - 4,
                x + self.PIECE_RADIUS + 4,
                y + self.PIECE_RADIUS + 4,
                outline=self.SELECT_COLOR,
                width=3,
            )

        for row, col in self.valid_moves:
            x, y = self._grid_to_pixel(row, col)
            target = self.board.get_piece(row, col)
            if target is None:
                self.canvas.create_oval(
                    x - 8,
                    y - 8,
                    x + 8,
                    y + 8,
                    fill=self.MOVE_HINT_COLOR,
                    outline="",
                )
            else:
                self.canvas.create_oval(
                    x - self.PIECE_RADIUS - 3,
                    y - self.PIECE_RADIUS - 3,
                    x + self.PIECE_RADIUS + 3,
                    y + self.PIECE_RADIUS + 3,
                    outline=self.CAPTURE_HINT_COLOR,
                    width=3,
                )

    def _draw_pieces(self) -> None:
        for row in range(self.board.ROWS):
            for col in range(self.board.COLS):
                piece = self.board.get_piece(row, col)
                if piece is None:
                    continue

                if self.animation_state is not None:
                    animation_to = self.animation_state["to"]
                    if (row, col) == animation_to:
                        continue

                x, y = self._grid_to_pixel(row, col)
                self._draw_piece_at(piece, x, y)

        if self.animation_state is not None:
            piece = self.animation_state["piece"]
            x = self.animation_state["x"]
            y = self.animation_state["y"]
            self._draw_piece_at(piece, x, y)

    def _draw_piece_at(self, piece: str, x: float, y: float) -> None:
        text = self.board.PIECE_NAMES[piece]
        text_color = self.RED_COLOR if piece[0] == "r" else self.BLACK_COLOR

        self.canvas.create_oval(
            x - self.PIECE_RADIUS,
            y - self.PIECE_RADIUS,
            x + self.PIECE_RADIUS,
            y + self.PIECE_RADIUS,
            fill="#f9f1dc",
            outline="#8d6b3f",
            width=2,
        )
        self.canvas.create_text(
            x,
            y,
            text=text,
            fill=text_color,
            font=("KaiTi", 22, "bold"),
        )

    def _on_canvas_click(self, event: tk.Event) -> None:
        position = self._pixel_to_grid(event.x, event.y)
        if position is None or self.board.winner is not None or self.is_animating or self.is_bot_thinking:
            return
        if self.board.current_player == self.BOT_COLOR:
            self.status_var.set("当前是机器人回合，请稍候。")
            return

        row, col = position
        piece = self.board.get_piece(row, col)

        if self.selected_position is None:
            self._select_piece(row, col)
            return

        if piece is not None and piece[0] == self.board.current_player:
            self._select_piece(row, col)
            return

        from_row, from_col = self.selected_position
        if (row, col) not in self.valid_moves:
            self.status_var.set("该位置不是当前棋子的合法落点，请重新选择。")
            return

        self._perform_move(from_row, from_col, row, col, mover="player")

    def _select_piece(self, row: int, col: int) -> None:
        piece = self.board.get_piece(row, col)
        if piece is None:
            self.status_var.set("该位置没有棋子，请点击己方棋子。")
            self.selected_position = None
            self.valid_moves = []
            self._draw()
            return

        if piece[0] != self.board.current_player:
            current_player = "红方" if self.board.current_player == "r" else "黑方"
            self.status_var.set(f"当前轮到{current_player}，不能选择对方棋子。")
            return

        valid_moves = self.board.get_valid_moves(row, col)
        self.selected_position = (row, col)
        self.valid_moves = valid_moves

        piece_name = self.board.PIECE_NAMES[piece]
        if valid_moves:
            self.status_var.set(f"已选中{piece_name}。绿色圆点和红色边框表示可以移动到的位置。")
        else:
            self.status_var.set(f"已选中{piece_name}，但当前没有合法走法。")
        self._draw()

    def _perform_move(
        self,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
        mover: str,
    ) -> None:
        piece = self.board.get_piece(from_row, from_col)
        if piece is None:
            return

        try:
            self.board.move_piece(from_row, from_col, to_row, to_col)
        except ValueError as exc:
            self.status_var.set(f"走子失败：{exc}")
            self.selected_position = None
            self.valid_moves = []
            self._draw()
            return

        self.selected_position = None
        self.valid_moves = []
        self.last_move = ((from_row, from_col), (to_row, to_col))

        if self.board.winner is not None:
            winner = "红方" if self.board.winner == "r" else "黑方"
            end_text = f"对局结束，{winner}获胜。"
            self._start_animation(
                piece,
                (from_row, from_col),
                (to_row, to_col),
                on_complete=lambda: self._finish_game(end_text),
            )
            return

        if not self.board.has_any_valid_move(self.board.current_player):
            winner = "红方" if self.board.current_player == "b" else "黑方"
            if self.board.is_in_check(self.board.current_player):
                end_text = f"对局结束，{winner}获胜。"
            else:
                end_text = "对局结束，双方无子可走，判和。"
            self._start_animation(
                piece,
                (from_row, from_col),
                (to_row, to_col),
                on_complete=lambda: self._finish_game(end_text),
            )
            return

        if mover == "player":
            self.status_var.set("你已落子，机器人正在思考。")
            self._start_animation(
                piece,
                (from_row, from_col),
                (to_row, to_col),
                on_complete=self._schedule_bot_move,
            )
        else:
            self._start_animation(
                piece,
                (from_row, from_col),
                (to_row, to_col),
                on_complete=self._after_bot_move,
            )

    def _schedule_bot_move(self) -> None:
        self._draw()
        self.root.after(120, self._start_bot_thinking)

    def _start_bot_thinking(self) -> None:
        self.is_bot_thinking = True
        self.status_var.set(f"黑方机器人(Pikafish, {self.level_var.get()})正在思考。")
        board_snapshot = self.board.clone()
        worker = threading.Thread(
            target=self._bot_worker,
            args=(board_snapshot,),
            daemon=True,
        )
        worker.start()

    def _bot_worker(self, board_snapshot: ChineseChessBoard) -> None:
        try:
            bestmove = self.engine.get_best_move(board_snapshot)
            self.root.after(0, lambda: self._apply_bot_move(bestmove))
        except Exception as exc:
            self.root.after(0, lambda: self._handle_engine_error(str(exc)))

    def _apply_bot_move(self, bestmove: str | None) -> None:
        self.is_bot_thinking = False
        if self.board.winner is not None:
            return

        if bestmove is None:
            if self.board.is_in_check(self.BOT_COLOR):
                self._finish_game("对局结束，红方获胜。")
            else:
                self._finish_game("对局结束，双方无子可走，判和。")
            return

        (from_row, from_col), (to_row, to_col) = self.board.uci_to_move(bestmove)
        self._perform_move(from_row, from_col, to_row, to_col, mover="bot")

    def _after_bot_move(self) -> None:
        if self.board.winner is not None:
            return
        self.status_var.set("轮到红方。请选择一个棋子继续对局。")
        self._draw()

    def _start_animation(
        self,
        piece: str,
        start: tuple[int, int],
        end: tuple[int, int],
        on_complete: callable,
    ) -> None:
        start_x, start_y = self._grid_to_pixel(*start)
        end_x, end_y = self._grid_to_pixel(*end)
        self.is_animating = True
        self.animation_state = {
            "piece": piece,
            "from": start,
            "to": end,
            "x": start_x,
            "y": start_y,
            "end_x": end_x,
            "end_y": end_y,
            "on_complete": on_complete,
        }
        self._animate_step(0)

    def _animate_step(self, frame: int) -> None:
        if self.animation_state is None:
            return

        progress = frame / self.ANIMATION_FRAMES
        eased = 1 - (1 - progress) * (1 - progress)
        start_row, start_col = self.animation_state["from"]
        start_x, start_y = self._grid_to_pixel(start_row, start_col)
        end_x = self.animation_state["end_x"]
        end_y = self.animation_state["end_y"]
        self.animation_state["x"] = start_x + (end_x - start_x) * eased
        self.animation_state["y"] = start_y + (end_y - start_y) * eased
        self._draw()

        if frame >= self.ANIMATION_FRAMES:
            callback = self.animation_state["on_complete"]
            self.animation_state = None
            self.is_animating = False
            self._draw()
            callback()
            return

        self.root.after(self.ANIMATION_INTERVAL_MS, lambda: self._animate_step(frame + 1))

    def _finish_game(self, message: str) -> None:
        if "红方获胜" in message:
            self.board.winner = "r"
        elif "黑方获胜" in message:
            self.board.winner = "b"
        self.status_var.set(message)
        self._draw()
        messagebox.showinfo("对局结束", message)

    def _on_level_changed(self, _event: tk.Event | None = None) -> None:
        level_key = self.LEVEL_NAME_TO_KEY[self.level_var.get()]
        self.engine.set_level(level_key)
        self.status_var.set(f"机器人难度已切换为 {self.level_var.get()}。")

    def _restart_game(self) -> None:
        if self.is_animating or self.is_bot_thinking:
            return
        self.board = ChineseChessBoard()
        self.engine.new_game()
        self.selected_position = None
        self.valid_moves = []
        self.last_move = None
        self.animation_state = None
        self.status_var.set("已重新开始。红方先行，请先走子。")
        self._draw()

    def _handle_engine_error(self, error_message: str) -> None:
        self.is_bot_thinking = False
        self.status_var.set("Pikafish 启动或思考失败，请检查引擎是否已经成功编译。")
        messagebox.showerror("Pikafish 错误", error_message)

    def _on_close(self) -> None:
        self.engine.stop()
        self.root.destroy()

    def _grid_to_pixel(self, row: int, col: int) -> tuple[int, int]:
        x = self.MARGIN + col * self.CELL_SIZE
        y = self.MARGIN + row * self.CELL_SIZE
        return x, y

    def _pixel_to_grid(self, x: int, y: int) -> tuple[int, int] | None:
        col = round((x - self.MARGIN) / self.CELL_SIZE)
        row = round((y - self.MARGIN) / self.CELL_SIZE)

        if not (0 <= row < self.board.ROWS and 0 <= col < self.board.COLS):
            return None

        center_x, center_y = self._grid_to_pixel(row, col)
        if abs(x - center_x) > self.CELL_SIZE * 0.45 or abs(y - center_y) > self.CELL_SIZE * 0.45:
            return None
        return row, col


def main() -> None:
    """桌面图形界面入口。"""
    gui = ChineseChessGUI()
    gui.run()
