"""board.py 的单元测试。"""

import unittest

import board_serializer
from board import ChineseChessBoard


# ---------------------------------------------------------------------------
# Python 基础知识点：继承
# ---------------------------------------------------------------------------
# class ChineseChessBoardTestCase(unittest.TestCase):
# 这表示 ChineseChessBoardTestCase 继承了 unittest.TestCase 类。
# 继承意味着子类自动拥有父类的所有方法和属性。
# 在这里，继承 TestCase 让我们获得了 setUp、assertEqual 等测试框架方法。

class ChineseChessBoardTestCase(unittest.TestCase):
    """
    中国象棋棋盘规则测试集。

    每个 test_ 开头的方法都是一个独立测试用例，
    框架会自动发现并运行它们。
    """

    # -------------------------------------------------------------------
    # Python 基础知识点：setUp 方法
    # -------------------------------------------------------------------
    # setUp() 会在每个测试方法执行**之前**被自动调用。
    # 用于准备每个测试所需的共同环境（在这里是创建一个新棋盘）。
    # 对应的还有 tearDown()，在每个测试方法执行**之后**调用（清理环境）。
    #
    # 每个测试方法都会获得一个全新的 self.board 实例，
    # 这样做可以保证测试之间互相独立（一个测试的修改不影响另一个测试）。
    def setUp(self) -> None:
        """每个测试方法执行前创建全新的棋盘。"""
        self.board = ChineseChessBoard()

    # ===================================================================
    # 棋盘初始状态测试
    # ===================================================================

    def test_initial_board_contains_generals(self) -> None:
        """
        测试1：初始棋盘上双方将帅各在其位。

        黑将在 (0,4)，红帅在 (9,4)。
        这是最基本的完整性测试——没有将帅的棋盘是不完整的。
        """
        self.assertEqual(self.board.board[0][4], "bG")  # 黑将在第0行第4列
        self.assertEqual(self.board.board[9][4], "rG")  # 红帅在第9行第4列

    # ===================================================================
    # 兵/卒走法测试
    # ===================================================================

    def test_red_soldier_can_move_forward(self) -> None:
        """
        测试2：红兵可以向前走一格。

        红兵从 (6,0) 走到 (5,0)（向棋盘上方走就是向前）。
        走完后：
        - 目标位置应该有红兵
        - 走棋方应该切换到黑方
        """
        self.board.move_piece(6, 0, 5, 0)           # 执行走棋
        self.assertEqual(self.board.board[5][0], "rS")  # 目标格有红兵
        self.assertEqual(self.board.current_player, "b")  # 轮到黑方

    def test_cannot_move_opponent_piece_on_current_turn(self) -> None:
        """
        测试3：红方回合不能移动黑方棋子。

        尝试移动黑卒 (3,0) → (4,0)，应该抛出 ValueError。
        assertRaisesRegex 验证：
        1. 抛出了 ValueError
        2. 异常消息中包含"当前不能移动对方棋子"
        """
        with self.assertRaisesRegex(ValueError, "当前不能移动对方棋子"):
            self.board.move_piece(3, 0, 4, 0)  # 黑卒在红方回合不能动

    # ===================================================================
    # 马走法测试
    # ===================================================================

    def test_horse_move_blocked_by_leg(self) -> None:
        """
        测试4：蹩马脚 —— 马被阻挡时不能跳。

        马的走法是「日」字形，但如果在日字的长边方向有棋子阻挡，
        马就不能跳。这个阻挡点叫「蹩脚」（绊马脚）。

        这里在 (8,1) 放一个红兵来蹩红方右马的脚，
        红马在 (9,1)，目标 (7,2)：
        - 纵向跳：蹩脚点 = (8,1)，这里放了兵，所以马不能跳
        """
        self.board.board[8][1] = "rS"  # 在蹩脚位置放一个兵
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(9, 1, 7, 2)

    # ===================================================================
    # 象/相走法测试
    # ===================================================================

    def test_elephant_cannot_cross_river(self) -> None:
        """
        测试5：红相不能过河。

        相（象）是防守型棋子，不能越过楚河汉界进入对方半场。
        红相在 (9,2)，要跳到 (5,6)，但 (5,6) 已经在黑方半场（0-4行），
        所以不合法。
        """
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(9, 2, 5, 6)

    # ===================================================================
    # 炮走法测试
    # ===================================================================

    def test_cannon_must_jump_when_capturing(self) -> None:
        """
        测试6：炮必须翻山才能吃子。

        炮的规则是：移动时和车一样（直走无阻挡），
        但吃子时必须有恰好一个炮架。

        这里构造了一个局面：
        - 红炮在 (7,1)，黑卒在 (2,4)
        - 中间路径上的其他棋子被清空
        - 炮和黑卒之间没有炮架 → 不能吃

        需要至少有一个炮架才能吃掉黑卒。
        """
        # 构造局面：在 (2,4) 放一个黑卒，清空路径上的棋子
        self.board.board[2][4] = "bS"
        self.board.board[3][4] = None
        self.board.board[4][4] = None
        self.board.board[5][4] = None
        self.board.board[6][4] = None
        # 现在炮到黑卒之间没有炮架，不能吃子
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(7, 1, 2, 4)

    # ===================================================================
    # 将/帅走法测试
    # ===================================================================

    def test_general_cannot_leave_palace(self) -> None:
        """
        测试7：将帅不能离开九宫格。

        红帅在 (9,4)，九宫格列范围是 3-5。
        试图走到 (9,6)（列 6 超出九宫格），应该不合法。
        """
        with self.assertRaisesRegex(ValueError, "该走法不符合棋子规则"):
            self.board.move_piece(9, 4, 9, 6)

    # ===================================================================
    # 将军规则测试
    # ===================================================================

    def test_cannot_leave_general_in_check(self) -> None:
        """
        测试8：不能走出让己方将帅被将军的走法。

        构造局面：
        - 红帅 (9,4)，红车 (8,4)
        - 黑车 (0,4) 控制着第 4 列
        - 如果红车离开第 4 列，红帅就直接暴露在黑车攻击下 → 不合法

        这是象棋的基本规则：走完后自己的将帅不能被将军。
        """
        # 清空棋盘，构造简化的将军测试局面
        self.board.board = [[None for _ in range(self.board.COLS)] for _ in range(self.board.ROWS)]
        self.board.board[9][4] = "rG"  # 红帅
        self.board.board[8][4] = "rR"  # 红车（挡住黑车的攻击线）
        self.board.board[0][4] = "bR"  # 黑车（控制第 4 列）
        self.board.current_player = "r"

        # 红车如果离开第 4 列，红帅就被黑车将军
        with self.assertRaisesRegex(ValueError, "不能让己方将帅被将军"):
            self.board.move_piece(8, 4, 8, 5)

    def test_generals_cannot_face_each_other(self) -> None:
        """
        测试9：双方将帅不能照面。

        中国象棋的特殊规则：双方将帅不能在同一列且之间没有任何棋子遮挡。
        这相当于两军统帅不能直接对面。

        构造局面：
        - 红帅 (9,4)，黑将 (0,4) —— 同在第 4 列
        - 红车 (5,4) 在它们之间，遮住了
        - 如果红车横向移开（离开第 4 列），帅和将之间就无遮拦 → 不合法
        """
        self.board.board = [[None for _ in range(self.board.COLS)] for _ in range(self.board.ROWS)]
        self.board.board[9][4] = "rG"  # 红帅
        self.board.board[0][4] = "bG"  # 黑将（同列）
        self.board.board[5][4] = "rR"  # 红车在中间挡着
        self.board.current_player = "r"

        # 红车离开第 4 列 → 将帅照面 → 不合法
        with self.assertRaisesRegex(ValueError, "双方将帅不能照面"):
            self.board.move_piece(5, 4, 5, 5)

    # ===================================================================
    # get_valid_moves 测试
    # ===================================================================

    def test_get_valid_moves_for_red_soldier(self) -> None:
        """
        测试10：红兵初始位置只有一个合法走法。

        红兵在 (6,0)（初始位置），只能向前走一格到 (5,0)。
        不能后退、不能横走（还没过河）。
        """
        moves = self.board.get_valid_moves(6, 0)
        self.assertEqual(moves, [(5, 0)])

    def test_get_valid_moves_returns_empty_for_opponent_piece(self) -> None:
        """
        测试11：查询对方棋子的合法走法返回空列表。

        黑卒在 (3,0)，红方回合查询它的走法应该返回 []，
        因为当前是红方回合，不能操作黑方棋子。
        """
        moves = self.board.get_valid_moves(3, 0)
        self.assertEqual(moves, [])

    def test_get_all_valid_moves_for_red_contains_forward_soldier(self) -> None:
        """
        测试12：红方所有合法走法中包含兵向前走。

        get_all_valid_moves("r") 返回红方所有棋子的所有合法走法。
        这里验证其中包含红兵 (6,0) → (5,0) 这个走法。
        """
        all_moves = self.board.get_all_valid_moves("r")
        self.assertIn(((6, 0), (5, 0)), all_moves)

    def test_checkmate_position_sets_winner_without_capturing_general(self) -> None:
        """
        测试12-1：形成将死时，即使没有吃掉将，也要立刻判胜。

        这是课程里“对面笑”示范局面的核心行为：
        红车平到 d 线后，黑方无合法应法，应直接判红方获胜。
        """
        board = ChineseChessBoard.from_fen("3k5/9/4R4/9/9/9/9/9/9/4K4 w - - 0 1")
        board.move_piece(2, 4, 2, 3)
        self.assertEqual(board.winner, "r")
        self.assertEqual(board.get_all_valid_moves("b"), [])

    # ===================================================================
    # 克隆测试
    # ===================================================================

    def test_clone_creates_independent_board(self) -> None:
        """
        测试13：克隆出的棋盘与原棋盘相互独立。

        这个测试验证 deepcopy 确实创建了完全独立的副本：
        1. 克隆一个棋盘
        2. 在副本上走棋
        3. 验证原棋盘不受影响
        4. 验证副本的修改生效

        -------------------------------------------------------------------
        Python 基础知识点：is None vs == None
        -------------------------------------------------------------------
        self.assertIsNone(x) 是 self.assertTrue(x is None) 的简写。
        用 is None 比 == None 更安全更快（is 比较身份不能被重载）。
        """
        clone_board = self.board.clone()
        clone_board.move_piece(6, 0, 5, 0)            # 在副本上走棋

        # 原棋盘的 (5,0) 应该还是空的
        self.assertIsNone(self.board.board[5][0])
        # 副本的 (5,0) 应该有红兵
        self.assertEqual(clone_board.board[5][0], "rS")

    # ===================================================================
    # FEN 格式测试
    # ===================================================================

    def test_to_fen_for_initial_position(self) -> None:
        """
        测试14：初始棋盘的 FEN 格式输出正确。

        FEN 是国际通用的棋盘文字表示法。
        这里验证初始布局的 FEN 字符串精确匹配。
        """
        fen = self.board.to_fen()
        self.assertEqual(
            fen,
            "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
        )

    def test_from_fen_round_trip(self) -> None:
        """to_fen 和 from_fen 应该能互相还原。"""
        self.board.move_piece(6, 0, 5, 0)
        fen = self.board.to_fen()
        restored = ChineseChessBoard.from_fen(fen)
        self.assertEqual(restored.to_fen(), fen)
        self.assertEqual(restored.current_player, self.board.current_player)

    def test_from_fen_requires_both_generals(self) -> None:
        """FEN 中必须同时包含红帅和黑将。"""
        with self.assertRaisesRegex(ValueError, "恰好包含一个红帅和一个黑将"):
            ChineseChessBoard.from_fen("9/9/9/9/9/9/9/9/9/4K4 w - - 0 1")

    # ===================================================================
    # UCI 坐标转换测试
    # ===================================================================

    def test_move_to_uci_for_red_soldier_forward(self) -> None:
        """
        测试15：棋盘坐标转 UCI 格式。

        红兵 (6,0) → (5,0)
        列 0 = 'a'，行 6 = '3'（UCI 中行号从下往上数：9→0, 8→1, ...）
        期望输出 "a3a4"（等价于 a3→a4）
        """
        self.assertEqual(self.board.move_to_uci(6, 0, 5, 0), "a3a4")

    def test_uci_to_move_for_red_soldier_forward(self) -> None:
        """
        测试16：UCI 格式转棋盘坐标。

        "a3a4" 应该解析为 ((6,0), (5,0))。
        这是 move_to_uci 的逆操作。
        """
        self.assertEqual(self.board.uci_to_move("a3a4"), ((6, 0), (5, 0)))

    # ===================================================================
    # 序列化与提示词构建测试
    # ===================================================================

    def test_serialize_board_contains_bestmove(self) -> None:
        """
        测试17：序列化的字典中包含引擎最优走法。

        验证 serialize_board 正确透传了 engine_analysis 信息。
        """
        serialized = board_serializer.serialize_board(
            board=self.board,
            move_history=["a3a4"],
            engine_analysis={"bestmove": "h2e2", "depth": 9},
        )
        self.assertEqual(serialized["engine_analysis"]["bestmove"], "h2e2")
        self.assertEqual(serialized["move_history"], ["a3a4"])

    def test_build_user_prompt_contains_question_and_engine_move(self) -> None:
        """
        测试18：构建的用户提示词包含用户问题和引擎最优走法。

        验证 board_serializer.build_user_prompt 生成的提示词文本
        中确实包含了用户问题和引擎推荐走法这两个关键信息。
        """
        serialized = board_serializer.serialize_board(
            board=self.board,
            move_history=[],
            engine_analysis={
                "bestmove": "h2e2",
                "score_type": "cp",
                "score_value": 35,
                "depth": 9,
                "pv": ["h2e2"],
            },
        )
        prompt = board_serializer.build_user_prompt(serialized, "下一步走什么？")
        self.assertIn("下一步走什么", prompt)  # 用户问题必须在提示词中
        self.assertIn("h2e2", prompt)          # 引擎推荐必须在提示词中
        self.assertIn("UCI 坐标", prompt)

    def test_serialize_board_piece_list_contains_uci_square(self) -> None:
        """测试19：棋子清单里包含 UCI 坐标，方便模型和界面统一。"""
        serialized = board_serializer.serialize_board(self.board)
        self.assertIn("e0", serialized["piece_list"])


# ===========================================================================
# 运行测试的主入口
# ===========================================================================
# unittest.main() 会自动发现当前模块中所有 test_ 开头的方法并运行它们。
# 运行方式：python tests/test_board.py
if __name__ == "__main__":
    unittest.main()
