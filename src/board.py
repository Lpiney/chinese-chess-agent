"""中国象棋棋盘与基础走子规则实现。"""

from __future__ import annotations

from copy import deepcopy


class ChineseChessBoard:
    """最小可运行的中国象棋棋盘。"""

    ROWS = 10
    COLS = 9

    PIECE_NAMES = {
        "rG": "帅",
        "rA": "仕",
        "rE": "相",
        "rH": "马",
        "rR": "车",
        "rC": "炮",
        "rS": "兵",
        "bG": "将",
        "bA": "士",
        "bE": "象",
        "bH": "马",
        "bR": "车",
        "bC": "炮",
        "bS": "卒",
    }

    FEN_PIECES = {
        "rR": "R",
        "rH": "N",
        "rE": "B",
        "rA": "A",
        "rG": "K",
        "rC": "C",
        "rS": "P",
        "bR": "r",
        "bH": "n",
        "bE": "b",
        "bA": "a",
        "bG": "k",
        "bC": "c",
        "bS": "p",
    }

    def __init__(self) -> None:
        self.board = self._create_initial_board()
        self.current_player = "r"
        self.winner = None

    def _create_initial_board(self) -> list[list[str | None]]:
        """创建标准开局棋盘。"""
        board = [[None for _ in range(self.COLS)] for _ in range(self.ROWS)]

        board[0] = ["bR", "bH", "bE", "bA", "bG", "bA", "bE", "bH", "bR"]
        board[2][1] = "bC"
        board[2][7] = "bC"
        for col in range(0, self.COLS, 2):
            board[3][col] = "bS"

        board[9] = ["rR", "rH", "rE", "rA", "rG", "rA", "rE", "rH", "rR"]
        board[7][1] = "rC"
        board[7][7] = "rC"
        for col in range(0, self.COLS, 2):
            board[6][col] = "rS"

        return board

    def display(self) -> str:
        """返回适合终端显示的棋盘文本。"""
        lines = ["   " + " ".join(str(col) for col in range(self.COLS))]
        for row_index, row in enumerate(self.board):
            cells = []
            for piece in row:
                cells.append(self.PIECE_NAMES.get(piece, "・"))
            lines.append(f"{row_index:>2} " + " ".join(cells))
        return "\n".join(lines)

    def get_piece(self, row: int, col: int) -> str | None:
        """返回指定坐标上的棋子。"""
        self._validate_coordinates(row, col)
        return self.board[row][col]

    def clone(self) -> "ChineseChessBoard":
        """返回当前棋盘的一个深拷贝。"""
        new_board = ChineseChessBoard()
        new_board.board = deepcopy(self.board)
        new_board.current_player = self.current_player
        new_board.winner = self.winner
        return new_board

    def get_valid_moves(
        self,
        row: int,
        col: int,
        color: str | None = None,
    ) -> list[tuple[int, int]]:
        """返回某个棋子当前所有合法落点。"""
        self._validate_coordinates(row, col)
        piece = self.board[row][col]
        active_color = self.current_player if color is None else color
        if piece is None or piece[0] != active_color or self.winner is not None:
            return []

        valid_moves: list[tuple[int, int]] = []
        for to_row in range(self.ROWS):
            for to_col in range(self.COLS):
                snapshot = deepcopy(self.board)
                current_player = self.current_player
                winner = self.winner
                try:
                    self.current_player = active_color
                    self.move_piece(row, col, to_row, to_col)
                except ValueError:
                    continue
                else:
                    valid_moves.append((to_row, to_col))
                finally:
                    self.board = snapshot
                    self.current_player = current_player
                    self.winner = winner

        return valid_moves

    def get_all_valid_moves(
        self,
        color: str | None = None,
    ) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """返回某一方当前所有合法走法。"""
        active_color = self.current_player if color is None else color
        all_moves: list[tuple[tuple[int, int], tuple[int, int]]] = []

        for row in range(self.ROWS):
            for col in range(self.COLS):
                piece = self.board[row][col]
                if piece is None or piece[0] != active_color:
                    continue
                for target in self.get_valid_moves(row, col, active_color):
                    all_moves.append(((row, col), target))
        return all_moves

    def has_any_valid_move(self, color: str | None = None) -> bool:
        """判断某一方是否至少还有一步合法走法。"""
        return len(self.get_all_valid_moves(color)) > 0

    def to_fen(self) -> str:
        """将当前棋盘转换为 Pikafish 使用的 FEN。"""
        fen_rows: list[str] = []

        for row in range(self.ROWS):
            empty_count = 0
            fen_row = ""
            for col in range(self.COLS):
                piece = self.board[row][col]
                if piece is None:
                    empty_count += 1
                    continue
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                fen_row += self.FEN_PIECES[piece]
            if empty_count > 0:
                fen_row += str(empty_count)
            fen_rows.append(fen_row)

        side_to_move = "w" if self.current_player == "r" else "b"
        return "/".join(fen_rows) + f" {side_to_move} - - 0 1"

    def move_to_uci(
        self,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> str:
        """将内部坐标转换为 Pikafish UCI 走法。"""
        return f"{self._coord_to_uci_square(from_row, from_col)}{self._coord_to_uci_square(to_row, to_col)}"

    def uci_to_move(self, uci_move: str) -> tuple[tuple[int, int], tuple[int, int]]:
        """将 Pikafish UCI 走法转换为内部坐标。"""
        if len(uci_move) != 4:
            raise ValueError("UCI 走法格式不正确。")
        from_square = uci_move[:2]
        to_square = uci_move[2:]
        return self._uci_square_to_coord(from_square), self._uci_square_to_coord(to_square)

    def _coord_to_uci_square(self, row: int, col: int) -> str:
        self._validate_coordinates(row, col)
        file_char = chr(ord("a") + col)
        rank_char = str(9 - row)
        return f"{file_char}{rank_char}"

    def _uci_square_to_coord(self, square: str) -> tuple[int, int]:
        if len(square) != 2:
            raise ValueError("棋盘坐标格式不正确。")
        file_char, rank_char = square
        col = ord(file_char) - ord("a")
        row = 9 - int(rank_char)
        self._validate_coordinates(row, col)
        return row, col

    def move_piece(self, from_row: int, from_col: int, to_row: int, to_col: int) -> None:
        """执行一步合法走子。"""
        self._validate_coordinates(from_row, from_col)
        self._validate_coordinates(to_row, to_col)

        piece = self.board[from_row][from_col]
        if piece is None:
            raise ValueError("起点位置没有棋子。")
        if piece[0] != self.current_player:
            raise ValueError("当前不能移动对方棋子。")
        if not self._is_valid_piece_move(piece, from_row, from_col, to_row, to_col):
            raise ValueError("该走法不符合棋子规则。")

        target = self.board[to_row][to_col]
        if target is not None and target[0] == piece[0]:
            raise ValueError("不能吃掉己方棋子。")

        snapshot = deepcopy(self.board)
        self.board[to_row][to_col] = piece
        self.board[from_row][from_col] = None

        if self._generals_face_each_other():
            self.board = snapshot
            raise ValueError("非法走子：双方将帅不能照面。")

        if self.is_in_check(piece[0]):
            self.board = snapshot
            raise ValueError("非法走子：不能让己方将帅被将军。")

        if target is not None and target[1] == "G":
            self.winner = piece[0]
        else:
            self.current_player = "b" if self.current_player == "r" else "r"

    def is_in_check(self, color: str) -> bool:
        """判断某一方将帅是否被攻击。"""
        general_position = self._find_general(color)
        if general_position is None:
            return True

        general_row, general_col = general_position
        enemy_color = "b" if color == "r" else "r"

        for row in range(self.ROWS):
            for col in range(self.COLS):
                piece = self.board[row][col]
                if piece is None or piece[0] != enemy_color:
                    continue
                if self._can_attack(piece, row, col, general_row, general_col):
                    return True
        return False

    def _find_general(self, color: str) -> tuple[int, int] | None:
        for row in range(self.ROWS):
            for col in range(self.COLS):
                if self.board[row][col] == f"{color}G":
                    return row, col
        return None

    def _validate_coordinates(self, row: int, col: int) -> None:
        if not (0 <= row < self.ROWS and 0 <= col < self.COLS):
            raise ValueError("坐标超出棋盘范围。")

    def _is_valid_piece_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        if from_row == to_row and from_col == to_col:
            return False

        if piece[1] == "R":
            return self._validate_rook_move(from_row, from_col, to_row, to_col)
        if piece[1] == "H":
            return self._validate_horse_move(from_row, from_col, to_row, to_col)
        if piece[1] == "E":
            return self._validate_elephant_move(piece, from_row, from_col, to_row, to_col)
        if piece[1] == "A":
            return self._validate_advisor_move(piece, to_row, to_col, from_row, from_col)
        if piece[1] == "G":
            return self._validate_general_move(piece, from_row, from_col, to_row, to_col)
        if piece[1] == "C":
            return self._validate_cannon_move(from_row, from_col, to_row, to_col)
        if piece[1] == "S":
            return self._validate_soldier_move(piece, from_row, from_col, to_row, to_col)
        return False

    def _can_attack(self, piece: str, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """判断某个棋子是否能攻击目标位置。"""
        target = self.board[to_row][to_col]

        if piece[1] == "C":
            if target is None:
                return False
            return self._validate_cannon_move(from_row, from_col, to_row, to_col)

        return self._is_valid_piece_move(piece, from_row, from_col, to_row, to_col)

    def _validate_rook_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        if from_row != to_row and from_col != to_col:
            return False
        return self._count_pieces_between(from_row, from_col, to_row, to_col) == 0

    def _validate_horse_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        row_diff = to_row - from_row
        col_diff = to_col - from_col

        if (abs(row_diff), abs(col_diff)) not in {(2, 1), (1, 2)}:
            return False

        if abs(row_diff) == 2:
            block_row = from_row + row_diff // 2
            block_col = from_col
        else:
            block_row = from_row
            block_col = from_col + col_diff // 2

        return self.board[block_row][block_col] is None

    def _validate_elephant_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        if abs(to_row - from_row) != 2 or abs(to_col - from_col) != 2:
            return False

        eye_row = (from_row + to_row) // 2
        eye_col = (from_col + to_col) // 2
        if self.board[eye_row][eye_col] is not None:
            return False

        if piece[0] == "r" and to_row < 5:
            return False
        if piece[0] == "b" and to_row > 4:
            return False
        return True

    def _validate_advisor_move(
        self,
        piece: str,
        to_row: int,
        to_col: int,
        from_row: int,
        from_col: int,
    ) -> bool:
        if abs(to_row - from_row) != 1 or abs(to_col - from_col) != 1:
            return False
        return self._is_in_palace(piece[0], to_row, to_col)

    def _validate_general_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        row_diff = abs(to_row - from_row)
        col_diff = abs(to_col - from_col)
        if row_diff + col_diff != 1:
            return False
        return self._is_in_palace(piece[0], to_row, to_col)

    def _validate_cannon_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        if from_row != to_row and from_col != to_col:
            return False

        between = self._count_pieces_between(from_row, from_col, to_row, to_col)
        target = self.board[to_row][to_col]

        if target is None:
            return between == 0
        return between == 1

    def _validate_soldier_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        row_diff = to_row - from_row
        col_diff = abs(to_col - from_col)

        if piece[0] == "r":
            forward = -1
            crossed_river = from_row <= 4
        else:
            forward = 1
            crossed_river = from_row >= 5

        if row_diff == forward and col_diff == 0:
            return True
        if crossed_river and row_diff == 0 and col_diff == 1:
            return True
        return False

    def _is_in_palace(self, color: str, row: int, col: int) -> bool:
        if color == "r":
            return 7 <= row <= 9 and 3 <= col <= 5
        return 0 <= row <= 2 and 3 <= col <= 5

    def _count_pieces_between(self, from_row: int, from_col: int, to_row: int, to_col: int) -> int:
        count = 0

        if from_row == to_row:
            step = 1 if to_col > from_col else -1
            for col in range(from_col + step, to_col, step):
                if self.board[from_row][col] is not None:
                    count += 1
        elif from_col == to_col:
            step = 1 if to_row > from_row else -1
            for row in range(from_row + step, to_row, step):
                if self.board[row][from_col] is not None:
                    count += 1
        else:
            return -1

        return count

    def _generals_face_each_other(self) -> bool:
        red_general = self._find_general("r")
        black_general = self._find_general("b")

        if red_general is None or black_general is None:
            return False
        if red_general[1] != black_general[1]:
            return False

        col = red_general[1]
        start = min(red_general[0], black_general[0]) + 1
        end = max(red_general[0], black_general[0])
        for row in range(start, end):
            if self.board[row][col] is not None:
                return False
        return True
