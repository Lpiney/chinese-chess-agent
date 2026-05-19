"""
中国象棋棋盘与规则实现。

本文件是中国象棋项目的核心模块，实现了：
- 棋盘状态管理（初始布局、走子、克隆）
- 七种棋子的行棋规则（将/帅、士/仕、象/相、马、车、炮、兵/卒）
- 将军检测、将帅照面检测等象棋特殊规则
- FEN 格式导入导出、UCI 坐标转换、合法走法枚举

适合 Python 初学者学习的中文注释版。
"""

# ---------------------------------------------------------------------------
# Python 基础知识点：__future__ 导入
# ---------------------------------------------------------------------------
# from __future__ import annotations 是一个特殊的导入语句。
# Python 会逐步引入新的语言特性，为了不破坏旧代码，有些特性默认不开启，
# 需要用 __future__ 来「提前启用」。
# annotations 特性让类型注解（如 list[str]）在运行时变成字符串而不是对象，
# 可以提升性能，尤其是在循环导入的场景下很有用。
# 现在几乎所有新的 Python 项目都会在开头写这一行。
from __future__ import annotations

# ---------------------------------------------------------------------------
# Python 基础知识点：标准库导入 - copy 模块
# ---------------------------------------------------------------------------
# deepcopy 是「深拷贝」，它会递归地复制一个对象的所有嵌套内容，
# 生成一个完全独立的新对象。
# 与「浅拷贝」的区别：浅拷贝只复制最外层，内部嵌套的列表/字典还会共享。
# 在棋盘操作中，我们需要用深拷贝来保存/恢复棋盘状态，确保修改不影响原对象。
from copy import deepcopy


class ChineseChessBoard:
    """
    中国象棋棋盘。

    这个类封装了：
    - 10行 x 9列 的二维棋盘 (用 list[list[str | None]] 表示)
    - 当前轮到哪一方走 (current_player: "r" 红方 / "b" 黑方)
    - 是否分出胜负 (winner)

    棋子编码规则：两字符字符串，如 "rR"、"bC"
    - 第一个字符表示阵营："r" = 红方 (red)，"b" = 黑方 (black)
    - 第二个字符表示兵种：
        G = 将/帅 (General)
        A = 士/仕 (Advisor)
        E = 象/相 (Elephant)
        H = 马 (Horse)
        R = 车 (Rook / 传统称"车"读 ju)
        C = 炮 (Cannon)
        S = 兵/卒 (Soldier)
    """

    # -----------------------------------------------------------------------
    # Python 基础知识点：类属性 vs 实例属性
    # -----------------------------------------------------------------------
    # 下面这两个字典 ROWS、COLS、PIECE_NAMES、FEN_PIECES 是「类属性」。
    # 类属性属于类本身，所有这个类的实例共享同一份数据。
    # 访问方式：ChineseChessBoard.ROWS 或 self.ROWS（在实例方法内）
    # 区别于 __init__ 中通过 self.xxx 定义的「实例属性」，
    # 实例属性每个对象各自独立一份。
    # 类属性适合存放「所有棋盘都一样」的常量定义。

    ROWS = 10  # 棋盘行数（0-9，共10行）
    COLS = 9   # 棋盘列数（0-8，共9列）

    # 棋子编码 → 中文显示名称的映射表
    # Python 基础知识点：dict（字典）
    # Python 字典是「键-值对」集合，用 {} 表示。
    # 常用操作：
    #   d["key"]       → 获取值（键不存在会报错 KeyError）
    #   d.get("key")   → 获取值（键不存在返回 None，更安全）
    #   "key" in d     → 判断键是否存在
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

    # 棋子编码 → FEN 单字符的映射表
    # FEN (Forsyth-Edwards Notation) 是国际象棋的标准文字表示法，
    # 这里做了适配用于中国象棋。
    # FEN 约定：大写字母 = 红方，小写字母 = 黑方
    # R=车 N=马 B=象 A=仕 K=帅 C=炮 P=兵
    FEN_PIECES = {
        "rR": "R", "rH": "N", "rE": "B", "rA": "A",
        "rG": "K", "rC": "C", "rS": "P",
        "bR": "r", "bH": "n", "bE": "b", "bA": "a",
        "bG": "k", "bC": "c", "bS": "p",
    }

    # -----------------------------------------------------------------------
    # Python 基础知识点：构造函数 __init__
    # -----------------------------------------------------------------------
    # __init__ 是 Python 类的「初始化方法」（也叫构造函数）。
    # 当你写 board = ChineseChessBoard() 时，Python 自动调用它。
    # 参数 self 代表「当前这个实例本身」，是 Python 方法的约定俗成。
    # 所有实例方法都必须有 self 作为第一个参数（调用时不用传，Python 自动补）。
    # -> None 是「类型注解」（type hint），表示这个方法不返回值。
    # 类型注解不会影响程序运行，但能让 IDE 给出更好的代码提示。

    def __init__(self) -> None:
        # self.board 是一个「二维列表」（list of lists）。
        # 外层列表有 ROWS (=10) 个元素，每个元素是一个包含 COLS (=9) 个元素的内层列表。
        # 每个格子要么是棋子编码（如 "rR"），要么是 None（空格子）。
        # Python 基础知识点：
        #   None 是 Python 的「空值」常量，表示「什么都没有」。
        self.board = self._create_initial_board()

        # current_player 表示当前轮到谁走棋
        # "r" = 红方 (red)，"b" = 黑方 (black)
        # 中国象棋规则：红方先走
        self.current_player = "r"

        # winner 表示获胜方
        # None = 对弈进行中，"r" = 红方胜，"b" = 黑方胜
        self.winner = None

    # -------------------------------------------------------------------
    # Python 基础知识点：列表推导式 (List Comprehension)
    # -------------------------------------------------------------------
    # 下面的代码使用了「列表推导式」来创建二维棋盘。
    # 格式：[表达式 for 变量 in 可迭代对象]
    #
    # 例子：
    #   [x*2 for x in range(3)]         → [0, 2, 4]
    #   [[0 for _ in range(3)] for _ in range(2)] → [[0,0,0], [0,0,0]]
    #
    # 这里 _ 是一个约定：当一个变量的值你不需要使用时，用 _ 代替名字，
    # 告诉读代码的人「这个变量我不关心它的值，只是用来控制循环次数」。

    def _create_initial_board(self) -> list[list[str | None]]:
        """
        创建中国象棋的初始棋盘布局。

        返回一个 10x9 的二维列表，按中国象棋起始位置摆放棋子。

        Python 基础知识点：list[list[str | None]] 是类型注解。
        表示「一个列表，里面每个元素又是一个列表，
        最内层元素要么是字符串要么是 None」。
        这个注解用的是 Python 3.10+ 的语法（无需 from typing import List）。

        中国象棋初始布局（从上往下看，第0行是黑方底线）：

        行列  0    1    2    3    4    5    6    7    8
         0   车   马   象   士   将   士   象   马   车    ← 黑方
         1    .    .    .    .    .    .    .    .    .
         2    .   炮   .    .    .    .    .   炮   .     ← 黑炮在第2行
         3   卒   .   卒   .   卒   .   卒   .   卒      ← 黑卒在第3行
         4    .    .    .    .    .    .    .    .    .   ← 楚河汉界
         5    .    .    .    .    .    .    .    .    .   ← 楚河汉界
         6   兵   .   兵   .   兵   .   兵   .   兵      ← 红兵在第6行
         7    .   炮   .    .    .    .    .   炮   .     ← 红炮在第7行
         8    .    .    .    .    .    .    .    .    .
         9   车   马   相   仕   帅   仕   相   马   车    ← 红方

        注意：这里 row=0 是棋盘顶部（黑方半场），row=9 是底部（红方半场）。
        """
        # 第一步：创建一个全是 None 的 10x9 空棋盘
        # 外层 for _ in range(self.ROWS) 循环 10 次（0~9行）
        # 内层 [None for _ in range(self.COLS)] 每行生成 9 个 None
        board = [[None for _ in range(self.COLS)] for _ in range(self.ROWS)]

        # 第二步：摆放黑方底线棋子（第 0 行）
        # list[0] 可以直接赋值为一个新列表
        # 黑方从列0到列8依次：车 马 象 士 将 士 象 马 车
        board[0] = ["bR", "bH", "bE", "bA", "bG", "bA", "bE", "bH", "bR"]

        # 第三步：摆黑方炮（第 2 行，列 1 和列 7）
        board[2][1] = "bC"  # list[row][col] 先选行，再选列
        board[2][7] = "bC"

        # 第四步：摆黑方卒（第 3 行，列 0, 2, 4, 6, 8）
        # Python 基础知识点：range(start, stop, step)
        # range(0, self.COLS, 2) 生成 0, 2, 4, 6, 8
        for col in range(0, self.COLS, 2):
            board[3][col] = "bS"

        # 第五步：摆红方底线棋子（第 9 行，棋盘最下方）
        # 布局与黑方完全对称
        board[9] = ["rR", "rH", "rE", "rA", "rG", "rA", "rE", "rH", "rR"]

        # 第六步：摆红方炮（第 7 行）
        board[7][1] = "rC"
        board[7][7] = "rC"

        # 第七步：摆红方兵（第 6 行）
        for col in range(0, self.COLS, 2):
            board[6][col] = "rS"

        return board

    def display(self) -> str:
        """
        把棋盘渲染成可打印的文本，方便在终端中查看。

        Python 基础知识点：f-string（格式化字符串）
        f"...{变量}..." 是 Python 3.6+ 的字符串格式化方式，
        大括号内的表达式会被替换成对应的值。
        {row_index:>2} 中的 :>2 表示右对齐并占 2 个字符宽度。
        """
        lines = ["   " + " ".join(str(col) for col in range(self.COLS))]
        # enumerate 同时给出索引和值
        # 等价于 for row_index in range(len(self.board)): row = self.board[row_index]
        for row_index, row in enumerate(self.board):
            # 对于每个格子，如果有棋子就拿中文名，否则显示 "・"
            cells = [self.PIECE_NAMES.get(piece, "・") for piece in row]
            lines.append(f"{row_index:>2} " + " ".join(cells))
        return "\n".join(lines)  # 用换行符把所有行拼接成一个字符串

    # -------------------------------------------------------------------
    # 基本操作：读棋子、克隆棋盘
    # -------------------------------------------------------------------

    def get_piece(self, row: int, col: int) -> str | None:
        """
        读取棋盘上某个位置的棋子。

        参数：
            row: 行号 (0-9)
            col: 列号 (0-8)

        返回：
            棋子编码字符串（如 "rR"），如果格子为空则返回 None
        """
        # 先检查坐标是否合法（防御性编程：在出错的地方抛出清晰的错误信息）
        self._validate_coordinates(row, col)
        return self.board[row][col]

    def clone(self) -> "ChineseChessBoard":
        """
        创建一个当前棋盘的「深拷贝」（完全独立的新副本）。

        用途：分析走法时需要模拟走棋但不影响实际棋盘，
        克隆一个副本后在副本上试走。

        返回类型 "ChineseChessBoard" 用引号括起来是因为
        类在定义时还没完成，Python 此时不认识这个名字，
        但有了 from __future__ import annotations 后它会被当作字符串处理。

        Python 基础知识点：deepcopy vs copy
        - 浅拷贝 (copy.copy)：只复制最外层对象，里面的子对象还是共享的
        - 深拷贝 (copy.deepcopy)：递归复制所有嵌套层次，全新独立
        棋盘是二维列表（列表里套列表），必须用深拷贝。
        """
        new_board = ChineseChessBoard()
        new_board.board = deepcopy(self.board)
        new_board.current_player = self.current_player
        new_board.winner = self.winner
        return new_board

    # -------------------------------------------------------------------
    # 合法走法查询
    # -------------------------------------------------------------------

    def get_valid_moves(
        self,
        row: int,
        col: int,
        color: str | None = None,
    ) -> list[tuple[int, int]]:
        """
        获取某个棋子当前所有的合法目标位置。

        参数：
            row: 棋子所在行
            col: 棋子所在列
            color: 可选，指定走棋方。默认 None 表示用 self.current_player。

        返回：
            [(目标行, 目标列), ...] 的列表，每个元组是一个可以走到的位置。

        Python 基础知识点：tuple（元组）
        元组是不可变的序列，用 () 表示，如 (3, 5)。
        与 list 的区别：list 可变（可以 append/remove），tuple 不可变。
        这里用 tuple 表示坐标对很适合，因为坐标不需要修改。

        Python 基础知识点：默认参数值
        color: str | None = None 表示 color 参数可以不传，
        不传时默认值是 None。
        为什么默认值用 None 而不是 "r"？
        因为我们需要区分「用户没传」和「用户传了"r"」两种情况。
        """
        # 参数校验
        self._validate_coordinates(row, col)
        piece = self.board[row][col]

        # 如果调用方没传 color，用当前走棋方
        active_color = self.current_player if color is None else color

        # 几种不合法的情况直接返回空列表：
        #   - 该位置没有棋子
        #   - 棋子不属于当前走棋方（piece[0] 是第一个字符，即阵营）
        #   - 游戏已结束
        if piece is None or piece[0] != active_color or self.winner is not None:
            return []

        valid_moves: list[tuple[int, int]] = []

        # 遍历棋盘上所有 90 个位置，逐一尝试，看哪些走法合法
        # Python 基础知识点：嵌套 for 循环
        for to_row in range(self.ROWS):
            for to_col in range(self.COLS):
                # -----------------------------------------------------------------
                # Python 基础知识点：try/except/else/finally 异常处理
                # -----------------------------------------------------------------
                # try      - 尝试执行可能出错的代码
                # except   - 如果 try 中发生了指定异常，执行这里的代码
                # else     - 如果 try 中没有发生异常，执行这里的代码
                # finally  - 无论是否发生异常，都会执行这里的代码
                #
                # 这里的思路：
                # 1. 保存当前棋盘状态（snapshot）
                # 2. 尝试在棋盘上执行这个走法
                # 3. 如果成功（没抛异常），说明是合法走法，加入列表
                # 4. 无论成功与否，恢复原始棋盘状态
                #
                # 这是一种常见的「尝试-回滚」模式，避免直接修改原棋盘。

                # 保存状态
                snapshot = deepcopy(self.board)
                current_player = self.current_player
                winner = self.winner
                try:
                    # 临时把自己切换为指定走棋方
                    self.current_player = active_color
                    # 尝试走棋，不合法会抛出 ValueError
                    self.move_piece(row, col, to_row, to_col)
                except ValueError:
                    # 走法不合法，跳过
                    continue
                else:
                    # 合法！把这个目标位置加入结果
                    valid_moves.append((to_row, to_col))
                finally:
                    # 无论合法与否，恢复棋盘到走棋前的状态
                    self.board = snapshot
                    self.current_player = current_player
                    self.winner = winner

        return valid_moves

    def get_all_valid_moves(
        self,
        color: str | None = None,
    ) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """
        获取某方的所有合法走法。

        返回：
            [((起始行, 起始列), (目标行, 目标列)), ...]
            每个元素是一个「从哪到哪」的走法对。
        """
        active_color = self.current_player if color is None else color
        all_moves: list[tuple[tuple[int, int], tuple[int, int]]] = []

        for row in range(self.ROWS):
            for col in range(self.COLS):
                piece = self.board[row][col]
                # 跳过空格子和对方的棋子
                if piece is None or piece[0] != active_color:
                    continue
                # 找到这个棋子所有可走的目标位置
                for target in self.get_valid_moves(row, col, active_color):
                    all_moves.append(((row, col), target))
        return all_moves

    def has_any_valid_move(self, color: str | None = None) -> bool:
        """判断某一方是否还有可走的棋步（用于检测将死/困毙）。"""
        # Python 基础知识点：
        # len() 返回列表/字符串/字典等可迭代对象的长度
        return len(self.get_all_valid_moves(color)) > 0

    # -------------------------------------------------------------------
    # FEN（棋盘标准表示法）和 UCI（通用象棋接口）坐标转换
    # -------------------------------------------------------------------

    def to_fen(self) -> str:
        """
        将当前棋盘状态导出为 FEN 格式字符串。

        FEN (Forsyth-Edwards Notation) 格式示例（初始局面）：
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

        FEN 由 6 个空格分隔的字段组成：
        1. 棋子布局：每行用 / 分隔，连续空格用数字表示
        2. 当前走棋方：w(白/红) 或 b(黑)
        3. 王车易位权限（中国象棋不用，写 -）
        4. 过路兵位置（中国象棋不用，写 -）
        5. 半回合计数器
        6. 全回合编号
        """
        fen_rows: list[str] = []
        for row in range(self.ROWS):
            empty_count = 0
            fen_row = ""
            for col in range(self.COLS):
                piece = self.board[row][col]
                if piece is None:
                    # 空格子，累计计数
                    empty_count += 1
                    continue
                # 遇到棋子，先输出之前累计的空格数
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                # 输出棋子对应的 FEN 字母
                fen_row += self.FEN_PIECES[piece]
            # 行末的空格也要输出
            if empty_count > 0:
                fen_row += str(empty_count)
            fen_rows.append(fen_row)

        # 中国象棋中红方对应 FEN 的 "w"（白）
        side_to_move = "w" if self.current_player == "r" else "b"
        # 用 / 连接各行、空格连接各字段
        return "/".join(fen_rows) + f" {side_to_move} - - 0 1"

    def move_to_uci(
        self,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> str:
        """
        将棋盘坐标转为 UCI 格式的走法字符串。

        UCI (Universal Chess Interface) 是引擎通信标准。
        坐标映射：列 0-8 → a-i，行 0-9 → 9-0（从上往下数）。
        例如：红方炮从 (7,1) 移到 (7,4) → "b5b8"

        Python 基础知识点：chr() 和 ord()
        - ord('a') 返回字母 'a' 的 ASCII 码（97）
        - chr(97) 返回 ASCII 码对应的字母 'a'
        这里用它们来做字母与数字之间的转换。
        """
        return f"{self._coord_to_uci_square(from_row, from_col)}{self._coord_to_uci_square(to_row, to_col)}"

    def uci_to_move(self, uci_move: str) -> tuple[tuple[int, int], tuple[int, int]]:
        """
        将 UCI 走法字符串转为棋盘坐标。

        例如："b5b8" → ((7,1), (7,4))

        Python 基础知识点：字符串切片
        uci_move[:2] 取前两个字符，uci_move[2:] 取后两个字符。
        字符串的索引从 0 开始，左闭右开。
        """
        if len(uci_move) != 4:
            raise ValueError("UCI 走法格式不正确。")
        return self._uci_square_to_coord(uci_move[:2]), self._uci_square_to_coord(uci_move[2:])

    def _coord_to_uci_square(self, row: int, col: int) -> str:
        """单个坐标转 UCI 格子名。例如 (9, 0) → "a0"。"""
        self._validate_coordinates(row, col)
        # 列: 0→'a', 1→'b', ..., 8→'i'
        # 行: 9→'0', 8→'1', ..., 0→'9'（注意：UCI 行号与棋盘行号是反向的）
        return f"{chr(ord('a') + col)}{9 - row}"

    def _uci_square_to_coord(self, square: str) -> tuple[int, int]:
        """UCI 格子名转单个坐标。例如 "a0" → (9, 0)。"""
        if len(square) != 2:
            raise ValueError("棋盘坐标格式不正确。")
        file_char, rank_char = square  # Python 字符串解包：两个字符分别赋值
        col = ord(file_char) - ord("a")
        row = 9 - int(rank_char)  # 字符数字转整数：int('0') = 0, int('9') = 9
        self._validate_coordinates(row, col)
        return row, col

    # -------------------------------------------------------------------
    # 核心走子逻辑
    # -------------------------------------------------------------------

    def move_piece(self, from_row: int, from_col: int, to_row: int, to_col: int) -> None:
        """
        执行一步走棋。这是整个棋盘模块最核心的方法。

        走棋步骤（按顺序检查）：
        1. 验证坐标合法
        2. 验证起点有棋子
        3. 验证棋子是当前走棋方的
        4. 验证走法符合该棋种的规则
        5. 验证不会吃掉己方棋子
        6. 执行走棋（临时）
        7. 检查走完后将帅是否照面 → 不合法则回滚
        8. 检查走完后己方是否被将军 → 不合法则回滚
        9. 如果吃掉了对方将帅 → 获胜
        10. 否则切换走棋方

        每一步验证不通过都会抛出 ValueError，附带中文错误信息。
        """
        # 1. 验证坐标
        self._validate_coordinates(from_row, from_col)
        self._validate_coordinates(to_row, to_col)

        # 2-3. 起点验证
        piece = self.board[from_row][from_col]
        if piece is None:
            raise ValueError("起点位置没有棋子。")
        if piece[0] != self.current_player:
            raise ValueError("当前不能移动对方棋子。")

        # 4. 棋种规则验证
        if not self._is_valid_piece_move(piece, from_row, from_col, to_row, to_col):
            raise ValueError("该走法不符合棋子规则。")

        # 5. 不能吃己方棋子
        target = self.board[to_row][to_col]
        if target is not None and target[0] == piece[0]:
            raise ValueError("不能吃掉己方棋子。")

        # 6. 先临时执行走棋（后面可能回滚）
        # Python 基础知识点：赋值操作是原子的
        # 先把棋盘当前状态保存为快照
        snapshot = deepcopy(self.board)
        self.board[to_row][to_col] = piece   # 目标位置放棋子
        self.board[from_row][from_col] = None  # 原位置清空

        # 7. 将帅照面检查
        if self._generals_face_each_other():
            self.board = snapshot  # 回滚
            raise ValueError("非法走子：双方将帅不能照面。")

        # 8. 将军检查（走棋后自己的将帅不能被将军）
        if self.is_in_check(piece[0]):
            self.board = snapshot  # 回滚
            raise ValueError("非法走子：不能让己方将帅被将军。")

        # 9-10. 走棋结果判定
        if target is not None and target[1] == "G":
            # 吃掉了对方将帅 → 游戏结束，走棋方获胜
            self.winner = piece[0]
        else:
            # 正常切换走棋方
            # Python 基础知识点：三元表达式
            # X if 条件 else Y  等价于其他语言的 条件 ? X : Y
            self.current_player = "b" if self.current_player == "r" else "r"

    # -------------------------------------------------------------------
    # 将军检测
    # -------------------------------------------------------------------

    def is_in_check(self, color: str) -> bool:
        """
        判断 color 这一方的将帅是否处于被将军状态。

        将军的定义：己方将帅处于对方某一棋子的攻击范围内。

        返回 True 表示被将军，False 表示安全。

        Python 基础知识点：方法拆解
        这个方法体现了「化整为零」的编程思想：
        1. 先找到己方将帅位置 (_find_general)
        2. 遍历对方所有棋子
        3. 判断每个棋子是否能攻击到将帅所在位置 (_can_attack)
        每个子任务都由独立的方法完成，主逻辑清晰易读。
        """
        # 找到己方将帅的位置
        general_position = self._find_general(color)
        if general_position is None:
            # 将帅不在棋盘上（理论上不该发生，但防一下）
            return True

        general_row, general_col = general_position
        # 确定对手颜色
        enemy_color = "b" if color == "r" else "r"

        # 遍历整个棋盘，看对手有没有棋子能攻击到将帅
        for row in range(self.ROWS):
            for col in range(self.COLS):
                piece = self.board[row][col]
                if piece is None or piece[0] != enemy_color:
                    continue
                if self._can_attack(piece, row, col, general_row, general_col):
                    return True
        return False

    def _find_general(self, color: str) -> tuple[int, int] | None:
        """
        在棋盘上找到某一方将帅的位置。

        返回 (行, 列) 元组，如果找不到返回 None。
        """
        for row in range(self.ROWS):
            for col in range(self.COLS):
                # 将帅的编码：颜色 + "G"，例如 "rG"（红帅）、"bG"（黑将）
                if self.board[row][col] == f"{color}G":
                    return row, col
        return None

    # -------------------------------------------------------------------
    # 坐标校验
    # -------------------------------------------------------------------

    def _validate_coordinates(self, row: int, col: int) -> None:
        """
        验证坐标是否在棋盘范围内。

        Python 基础知识点：逻辑运算符 and 与链式比较
        0 <= row < self.ROWS 是 Python 特有的链式比较写法，
        等价于 0 <= row and row < self.ROWS。
        这种写法更接近数学表达方式，也更简洁。
        """
        if not (0 <= row < self.ROWS and 0 <= col < self.COLS):
            raise ValueError("坐标超出棋盘范围。")

    # ===================================================================
    # 以下为各棋种的走子规则验证方法
    #
    # 每个方法返回 bool：True = 走法符合规则，False = 不符合
    # 所有方法都不修改棋盘状态（纯计算/查询）
    # ===================================================================

    def _is_valid_piece_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        """
        根据棋子类型分派到对应的验证方法。

        Python 基础知识点：字符串索引
        piece 格式为 "颜色+兵种"，如 "rR"、"bC"。
        piece[0] 取第一个字符（颜色），piece[1] 取第二个字符（兵种）。

        Python 基础知识点：if/elif 多分支判断
        elif 是 else if 的缩写。程序从上往下依次判断条件，
        第一个为 True 的分支被执行，后面的都被跳过。
        最后的 else: return False 是「兜底」逻辑。
        """
        # 不能原地不动
        if from_row == to_row and from_col == to_col:
            return False

        piece_type = piece[1]  # 取第二个字符，即兵种代码
        if piece_type == "R":    # 车
            return self._validate_rook_move(from_row, from_col, to_row, to_col)
        if piece_type == "H":    # 马
            return self._validate_horse_move(from_row, from_col, to_row, to_col)
        if piece_type == "E":    # 象/相
            return self._validate_elephant_move(piece, from_row, from_col, to_row, to_col)
        if piece_type == "A":    # 士/仕
            return self._validate_advisor_move(piece, to_row, to_col, from_row, from_col)
        if piece_type == "G":    # 将/帅
            return self._validate_general_move(piece, from_row, from_col, to_row, to_col)
        if piece_type == "C":    # 炮
            return self._validate_cannon_move(from_row, from_col, to_row, to_col)
        if piece_type == "S":    # 兵/卒
            return self._validate_soldier_move(piece, from_row, from_col, to_row, to_col)
        return False

    def _can_attack(self, piece: str, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """
        判断棋子是否能「攻击」到某个位置。

        与 _is_valid_piece_move 的区别：
        - _is_valid_piece_move 是完整规则（包括不能移动到自己控制的格子上等）
        - _can_attack 只关心「这个棋子能不能打到那个位置」
        - 对于炮 (Cannon)：攻击时必须翻一座炮架（吃子），所以目标必须是棋子
        """
        target = self.board[to_row][to_col]
        if piece[1] == "C":
            # 炮的特殊处理：炮「攻击」= 吃子，所以目标格必须有棋子
            if target is None:
                return False
            return self._validate_cannon_move(from_row, from_col, to_row, to_col)
        # 其他棋子：攻击规则 = 走子规则
        return self._is_valid_piece_move(piece, from_row, from_col, to_row, to_col)

    # -------------------------------------------------------------------
    # 车 (Rook) 的规则
    # -------------------------------------------------------------------

    def _validate_rook_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """
        验证车的走法。

        车的规则：
        - 直线走（同行或同列）
        - 路径上不能有其他棋子阻挡（不能翻山）

        Python 基础知识点：逻辑运算符
        - != 表示「不等于」
        - and 表示「并且」（两个条件都满足）
        - or 表示「或者」（任一条件满足）
        """
        # 必须走直线（要么同行、要么同列）
        if from_row != to_row and from_col != to_col:
            return False
        # 路径上棋子数量必须为 0（无阻挡）
        return self._count_pieces_between(from_row, from_col, to_row, to_col) == 0

    # -------------------------------------------------------------------
    # 马 (Horse) 的规则
    # -------------------------------------------------------------------

    def _validate_horse_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """
        验证马的走法。

        马的规则（「日」字形）：
        - 移动 (2,1) 或 (1,2)，即「跳日字」
        - 需要检查「蹩脚」（绊马脚）：移动方向的第一步位置不能有棋子

        蹩脚原理图示（以纵向跳为例）：
        马在 (0,0)，要跳到 (2,1)
        第一步走纵向 (1,0)，这个位置就是「蹩脚点」
        如果 (1,0) 有棋子，马就不能跳到 (2,1)

        Python 基础知识点：abs() - 绝对值函数
        abs(-3) = 3, abs(3) = 3
        这里用 abs(row_diff) 来获取行差和列差的绝对值。

        Python 基础知识点：集合 set
        set 是无序不重复元素的集合，用 {} 表示。
        用 in 判断元素是否在集合中：3 in {1, 2, 3} → True
        集合查找速度比列表快（O(1) vs O(n)）。
        """
        row_diff = to_row - from_row  # 行变化量
        col_diff = to_col - from_col  # 列变化量

        # 马必须走「日」字：(2行+1列) 或 (1行+2列)
        # {(2,1), (1,2)} 是一个包含两个元组的集合
        if (abs(row_diff), abs(col_diff)) not in {(2, 1), (1, 2)}:
            return False

        # 确定蹩脚点的位置
        if abs(row_diff) == 2:
            # 纵向跳：蹩脚点在纵向的一半位置
            # row_diff // 2 是整数除法：-2//2 = -1, 2//2 = 1
            block_row = from_row + row_diff // 2
            block_col = from_col  # 列不变
        else:
            # 横向跳：蹩脚点在横向的一半位置
            block_row = from_row  # 行不变
            block_col = from_col + col_diff // 2

        # 蹩脚点必须为空
        return self.board[block_row][block_col] is None

    # -------------------------------------------------------------------
    # 象/相 (Elephant) 的规则
    # -------------------------------------------------------------------

    def _validate_elephant_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        """
        验证象/相的走法。

        规则：
        - 走「田」字形：行和列都移动 2 格
        - 需要「塞眼」检查：对角线的中心点必须为空
        - 不能过河：红相只能在 5-9 行（己方半场），黑象只能在 0-4 行

        田字图示：
            象在 (9,0)，要跳到 (7,2)
            眼的位置在 (8,1)（起点和终点的行列平均数）
        """
        # 必须走「田」字（4 格对角线）
        if abs(to_row - from_row) != 2 or abs(to_col - from_col) != 2:
            return False

        # === Python 基础知识点：整数除法 // ===
        # 普通除法 / 返回浮点数：5 / 2 = 2.5
        # 整数除法 // 返回整数：5 // 2 = 2（向下取整）
        # 这里用 // 计算中心点坐标正好合适：
        #   (9+7)//2 = 8, (0+2)//2 = 1 → 眼在 (8,1)

        # 计算塞眼位置（起点和终点的中心）
        eye_row = (from_row + to_row) // 2
        eye_col = (from_col + to_col) // 2
        if self.board[eye_row][eye_col] is not None:
            return False  # 被塞眼了，不能走

        # 检查是否过河
        # 红相（rE）不能到第 0-4 行（对方半场）
        # 黑象（bE）不能到第 5-9 行（对方半场）
        if piece[0] == "r" and to_row < 5:
            return False
        if piece[0] == "b" and to_row > 4:
            return False
        return True

    # -------------------------------------------------------------------
    # 士/仕 (Advisor) 的规则
    # -------------------------------------------------------------------

    def _validate_advisor_move(
        self,
        piece: str,
        to_row: int,
        to_col: int,
        from_row: int,
        from_col: int,
    ) -> bool:
        """
        验证士/仕的走法。

        规则：
        - 走斜线：行和列各移动 1 格
        - 必须在九宫格内

        九宫格范围：
            红方：行 7-9，列 3-5
            黑方：行 0-2，列 3-5
        """
        # 必须斜走一格
        if abs(to_row - from_row) != 1 or abs(to_col - from_col) != 1:
            return False
        # 目标格必须在九宫格内
        return self._is_in_palace(piece[0], to_row, to_col)

    # -------------------------------------------------------------------
    # 将/帅 (General) 的规则
    # -------------------------------------------------------------------

    def _validate_general_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        """
        验证将/帅的走法。

        规则：
        - 走直线一格（上下左右，不能斜走）
        - 必须在九宫格内

        注意：将帅照面检查在 move_piece 中统一处理，这里只验证基本步法。
        """
        # 曼哈顿距离（行差 + 列差）必须为 1，即只能走一格
        if abs(to_row - from_row) + abs(to_col - from_col) != 1:
            return False
        # 目标格必须在九宫格内
        return self._is_in_palace(piece[0], to_row, to_col)

    # -------------------------------------------------------------------
    # 炮 (Cannon) 的规则
    # -------------------------------------------------------------------

    def _validate_cannon_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """
        验证炮的走法。

        炮的规则（最复杂的棋种）：
        - 移动（不吃子时）：走直线，路径上无阻挡（和车一样）
        - 吃子时：走直线，且起点和目标之间必须有恰好 1 个棋子作为「炮架」

        这就是中国象棋「炮打翻山」的含义。
        """
        # 必须走直线
        if from_row != to_row and from_col != to_col:
            return False

        # 计算路径中间的棋子数量
        between = self._count_pieces_between(from_row, from_col, to_row, to_col)
        target = self.board[to_row][to_col]

        if target is None:
            # 不吃子：路径必须无阻挡（和车一样）
            return between == 0
        # 吃子：必须有且仅有一个炮架
        return between == 1

    # -------------------------------------------------------------------
    # 兵/卒 (Soldier) 的规则
    # -------------------------------------------------------------------

    def _validate_soldier_move(
        self,
        piece: str,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
    ) -> bool:
        """
        验证兵/卒的走法。

        规则：
        - 未过河：只能向前走一格（不能横走、不能后退）
        - 已过河：可以向前或横走一格（仍然不能后退）
        - 红兵向上走（行号减小），黑卒向下走（行号增大）

        Python 基础知识点：条件赋值
        crossed_river = from_row <= 4 是一个布尔表达式，
        它的结果是 True 或 False。
        Python 中 True == 1, False == 0（但一般不要依赖这个特性）。
        """
        row_diff = to_row - from_row
        col_diff = abs(to_col - from_col)

        # 红方和黑方的「前进」方向不同
        if piece[0] == "r":
            forward = -1  # 红兵向上走，行号减小
            crossed_river = from_row <= 4  # 红方过河意味着进入 0-4 行
        else:
            forward = 1   # 黑卒向下走，行号增大
            crossed_river = from_row >= 5  # 黑方过河意味着进入 5-9 行

        # 情况1：向前走一格（未过河和已过河都可以）
        if row_diff == forward and col_diff == 0:
            return True
        # 情况2：已过河后横走一格
        if crossed_river and row_diff == 0 and col_diff == 1:
            return True
        return False

    # -------------------------------------------------------------------
    # 辅助判断方法
    # -------------------------------------------------------------------

    def _is_in_palace(self, color: str, row: int, col: int) -> bool:
        """
        判断某个位置是否在九宫格内。

        九宫格是棋盘上两个 3x3 的区域，只有将帅和士仕能在里面活动。

        红方九宫：行 7-9，列 3-5  （棋盘底部中央）
        黑方九宫：行 0-2，列 3-5  （棋盘顶部中央）
        """
        if color == "r":
            return 7 <= row <= 9 and 3 <= col <= 5
        return 0 <= row <= 2 and 3 <= col <= 5

    def _count_pieces_between(self, from_row: int, from_col: int, to_row: int, to_col: int) -> int:
        """
        计算直线上两个位置之间有多少棋子（不包含起点和终点）。

        用于车和炮的阻挡判断。

        Python 基础知识点：range 步长参数
        range(from_col + step, to_col, step) 中第三个参数 step 是步长。
        如果 to_col > from_col，step=1 表示递增遍历。
        如果 to_col < from_col，step=-1 表示递减遍历。

        Python 基础知识点：is not None
        与 != None 在大多数情况下等价，但 is not None 更安全更快，
        因为 is 比较的是对象身份（内存地址），不能被重载。
        """
        count = 0
        if from_row == to_row:
            # 同一行上的移动：横向遍历列
            step = 1 if to_col > from_col else -1  # 确定遍历方向
            for col in range(from_col + step, to_col, step):
                if self.board[from_row][col] is not None:
                    count += 1
        elif from_col == to_col:
            # 同一列上的移动：纵向遍历行
            step = 1 if to_row > from_row else -1
            for row in range(from_row + step, to_row, step):
                if self.board[row][from_col] is not None:
                    count += 1
        else:
            return -1  # 不是直线，返回 -1 表示无意义
        return count

    def _generals_face_each_other(self) -> bool:
        """
        检查双方将帅是否直接照面（同列且之间无遮挡）。

        中国象棋有一个特殊规则：双方将帅不能在同一列且之间没有任何棋子。
        如果发生这种情况，视为非法走法，因为相当于将帅直接对面。

        检查方法：
        1. 找到红帅和黑将的位置
        2. 如果它们在同一列
        3. 且它们之间没有任何棋子
        4. 则返回 True（表示不合法）
        """
        red_general = self._find_general("r")
        black_general = self._find_general("b")

        # 如果任一将帅不在棋盘上，不算照面（这种情况不会在实际对弈中出现）
        if red_general is None or black_general is None:
            return False

        # 不在同一列，不可能照面
        if red_general[1] != black_general[1]:
            return False

        # 在同一列了，检查之间是否有棋子
        col = red_general[1]
        # 取两个将帅行号中的较小值和较大值，检查中间是否有棋子
        start = min(red_general[0], black_general[0]) + 1  # +1 跳过将帅本身
        end = max(red_general[0], black_general[0])

        for row in range(start, end):
            if self.board[row][col] is not None:
                return False  # 中间有棋子挡住，不算照面

        # 之间无棋子 → 照面了，不合法
        return True
