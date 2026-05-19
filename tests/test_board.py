"""中国象棋棋盘测试。"""

import unittest

from src.board import ChineseChessBoard


class ChineseChessBoardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.board = ChineseChessBoard()

    def test_initial_board_contains_generals(self) -> None:
        self.assertEqual(self.board.board[0][4], "bG")
        self.assertEqual(self.board.board[9][4], "rG")

    def test_red_soldier_can_move_forward(self) -> None:
        self.board.move_piece(6, 0, 5, 0)
        self.assertEqual(self.board.board[5][0], "rS")
        self.assertEqual(self.board.current_player, "b")

    def test_cannot_move_opponent_piece_on_current_turn(self) -> None:
        with self.assertRaisesRegex(ValueError, "当前不能移动对方棋子"):
            self.board.move_piece(3, 0, 4, 0)

    def test_horse_move_blocked_by_leg(self) -> None:
        self.board.board[8][1] = "rS"
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(9, 1, 7, 2)

    def test_elephant_cannot_cross_river(self) -> None:
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(9, 2, 5, 6)

    def test_cannon_must_jump_when_capturing(self) -> None:
        self.board.board[2][4] = "bS"
        self.board.board[3][4] = None
        self.board.board[4][4] = None
        self.board.board[5][4] = None
        self.board.board[6][4] = None
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(7, 1, 2, 4)

    def test_general_cannot_leave_palace(self) -> None:
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(9, 4, 9, 6)

    def test_cannot_leave_general_in_check(self) -> None:
        self.board.board = [[None for _ in range(self.board.COLS)] for _ in range(self.board.ROWS)]
        self.board.board[9][4] = "rG"
        self.board.board[8][4] = "rR"
        self.board.board[0][4] = "bR"
        self.board.current_player = "r"

        with self.assertRaisesRegex(ValueError, "不能让己方将帅被将军"):
            self.board.move_piece(8, 4, 8, 5)

    def test_generals_cannot_face_each_other(self) -> None:
        self.board.board = [[None for _ in range(self.board.COLS)] for _ in range(self.board.ROWS)]
        self.board.board[9][4] = "rG"
        self.board.board[0][4] = "bG"
        self.board.board[5][4] = "rR"
        self.board.current_player = "r"

        with self.assertRaisesRegex(ValueError, "双方将帅不能照面"):
            self.board.move_piece(5, 4, 5, 5)

    def test_get_valid_moves_for_red_soldier(self) -> None:
        moves = self.board.get_valid_moves(6, 0)
        self.assertEqual(moves, [(5, 0)])

    def test_get_valid_moves_returns_empty_for_opponent_piece(self) -> None:
        moves = self.board.get_valid_moves(3, 0)
        self.assertEqual(moves, [])

    def test_get_all_valid_moves_for_red_contains_forward_soldier(self) -> None:
        all_moves = self.board.get_all_valid_moves("r")
        self.assertIn(((6, 0), (5, 0)), all_moves)

    def test_clone_creates_independent_board(self) -> None:
        clone_board = self.board.clone()
        clone_board.move_piece(6, 0, 5, 0)
        self.assertIsNone(self.board.board[5][0])
        self.assertEqual(clone_board.board[5][0], "rS")

    def test_to_fen_for_initial_position(self) -> None:
        fen = self.board.to_fen()
        self.assertEqual(
            fen,
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        )

    def test_move_to_uci_for_red_soldier_forward(self) -> None:
        self.assertEqual(self.board.move_to_uci(6, 0, 5, 0), "a3a4")

    def test_uci_to_move_for_red_soldier_forward(self) -> None:
        self.assertEqual(self.board.uci_to_move("a3a4"), ((6, 0), (5, 0)))


if __name__ == "__main__":
    unittest.main()
