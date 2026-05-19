"""Flask 入口，负责页面、API 和单局游戏状态。"""

# ---------------------------------------------------------------------------
# Python 基础知识点：from __future__ import annotations
# ---------------------------------------------------------------------------
# 见 board.py 中的详细注释。简言之：让类型注解在运行时变成字符串，
# 避免循环导入问题，同时提升性能。新项目几乎都加这一行。
from __future__ import annotations

# ---------------------------------------------------------------------------
# Python 基础知识点：标准库导入
# ---------------------------------------------------------------------------
# atexit     - 程序退出时的清理钩子（程序退出时自动执行注册的函数）
# threading  - 多线程支持（用于加锁保护共享状态，以及延时启动浏览器）
# webbrowser - 控制系统的默认浏览器（自动打开网页）
# dataclasses - 数据类装饰器，自动生成 __init__、__repr__ 等样板方法（Python 3.7+）
import atexit
import threading
import webbrowser
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Python 基础知识点：第三方库导入 - Flask
# ---------------------------------------------------------------------------
# Flask 是一个轻量级 Python Web 框架。
# - Flask 类：创建 Web 应用实例
# - jsonify()：将 Python 字典转为 JSON 响应（自动设置 Content-Type: application/json）
# - render_template()：渲染 Jinja2 HTML 模板
# - request：代表当前 HTTP 请求，可从中读取参数和请求体
from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# 项目内部模块导入
# ---------------------------------------------------------------------------
# import chess_agent   → 导入模块（然后需要用 chess_agent.xxx() 调用）
# from board import ChineseChessBoard → 直接导入类（直接用 ChineseChessBoard()）
import chess_agent
from board import ChineseChessBoard
from pikafish_engine import PikafishEngine


# ---------------------------------------------------------------------------
# 应用工厂函数
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    """
    创建并配置 Flask 应用。

    Python 基础知识点：Flask 应用工厂模式
    不直接在模块级别创建 app = Flask(__name__)，
    而是用工厂函数 create_app() 来创建。
    好处：
    1. 便于测试（每次测试可以创建全新的应用实例）
    2. 便于配置（可以传入不同的配置参数）
    3. 避免循环导入（模块加载顺序不影响应用创建）

    路由装饰器：
    @app.get("/path")  等价于 @app.route("/path", methods=["GET"])
    @app.post("/path") 等价于 @app.route("/path", methods=["POST"])
    """
    app = Flask(__name__)  # __name__ 是当前模块名，Flask 用它定位模板和静态文件
    session = GameSession()  # 创建游戏会话（所有 API 请求共享这一局游戏状态）

    # -------------------------------------------------------------------
    # 路由 1：首页
    # -------------------------------------------------------------------
    @app.get("/")
    def index():
        """
        返回前端 HTML 页面。

        render_template("index.html") 会去项目根目录的 templates/ 文件夹
        找 index.html，用 Jinja2 模板引擎渲染后返回。
        """
        return render_template("index.html")

    # -------------------------------------------------------------------
    # 路由 2：获取游戏状态
    # -------------------------------------------------------------------
    @app.get("/api/state")
    def get_state():
        """
        返回当前游戏状态的 JSON 数据。

        前端通过轮询这个接口来更新界面显示。
        返回数据包括：棋盘布局、棋子名称映射、当前走棋方、获胜方、走棋历史等。
        """
        return jsonify(session.serialize_state())

    # -------------------------------------------------------------------
    # 路由 3：获取某棋子的合法走法
    # -------------------------------------------------------------------
    @app.get("/api/legal-moves")
    def get_legal_moves():
        """
        查询某个位置棋子的所有合法目标位置。

        前端在点击棋子时调用此接口，获取高亮显示的合法走法。

        Python 基础知识点：读取 URL 查询参数
        request.args 是一个类字典对象，包含 URL 中 ? 后面的参数。
        例如 GET /api/legal-moves?row=6&col=0
        request.args["row"] 获取到的值是字符串 "6"，需要用 int() 转为整数。
        """
        row = int(request.args["row"])
        col = int(request.args["col"])
        moves = session.get_valid_moves(row, col)
        # 列表推导式：把 [(0,1), (2,3)] 转为 [{"row":0,"col":1}, {"row":2,"col":3}]
        return jsonify({"moves": [{"row": move[0], "col": move[1]} for move in moves]})

    # -------------------------------------------------------------------
    # 路由 4：执行走棋
    # -------------------------------------------------------------------
    @app.post("/api/move")
    def post_move():
        """
        接收前端提交的走棋操作。

        POST 请求体为 JSON 格式：
        {"from_row": 6, "from_col": 0, "to_row": 5, "to_col": 0}

        Python 基础知识点：读取 JSON 请求体
        request.get_json(force=True) 解析请求体中的 JSON 数据。
        force=True 表示即使 Content-Type 头不对也强制解析。
        """
        payload = request.get_json(force=True)
        from_row = int(payload["from_row"])
        from_col = int(payload["from_col"])
        to_row = int(payload["to_row"])
        to_col = int(payload["to_col"])
        result = session.apply_player_move(from_row, from_col, to_row, to_col)
        return jsonify(result)

    # -------------------------------------------------------------------
    # 路由 5：重置游戏
    # -------------------------------------------------------------------
    @app.post("/api/reset")
    def post_reset():
        """重新开始一局游戏。"""
        return jsonify(session.reset())

    # -------------------------------------------------------------------
    # 路由 6：设置难度
    # -------------------------------------------------------------------
    @app.post("/api/level")
    def post_level():
        """
        设置电脑难度等级。

        请求体：{"level": "beginner" | "medium" | "master"}
        """
        payload = request.get_json(force=True)
        result = session.set_level(payload["level"])
        return jsonify(result)

    # -------------------------------------------------------------------
    # 路由 7：AI 聊天
    # -------------------------------------------------------------------
    @app.post("/api/chat")
    def post_chat():
        """
        用户向 AI 老师提问。

        请求体：{"message": "这一步为什么走炮？"}
        返回：AI 老师的分析和建议。

        Python 基础知识点：try/except 异常处理
        try 块中的代码如果出错会跳到 except 块，防止整个服务崩溃。
        返回 HTTP 503 (Service Unavailable) 状态码表示服务暂时不可用。
        """
        payload = request.get_json(force=True)
        try:
            result = session.ask_agent(payload["message"])
        except Exception as exc:
            # 聊天服务出错时返回友好提示，HTTP 503 表示服务暂时不可用
            return jsonify({"ok": False, "error": f"聊天服务当前不可用：{exc}"}), 503
        return jsonify(result)

    # -------------------------------------------------------------------
    # 程序退出时的清理
    # -------------------------------------------------------------------
    # atexit.register(func) 的作用：当 Python 进程退出时（无论正常还是异常），
    # 自动调用 func。这里注册 session.close 来关闭 Pikafish 引擎子进程。
    # 如果不这样做，Pikafish 子进程可能变成「僵尸进程」继续占用资源。
    atexit.register(session.close)

    return app


# ===========================================================================
# GameSession 数据类 —— 维护单局游戏的所有状态
# ===========================================================================

# ---------------------------------------------------------------------------
# Python 基础知识点：@dataclass 装饰器
# ---------------------------------------------------------------------------
# 在 Python 3.7 之前，一个数据容器类需要手写很多样板代码：
#   class GameSession:
#       def __init__(self, board=None, ...):
#           self.board = board
#           ...
#       def __repr__(self): return f"GameSession(...)"
#       def __eq__(self, other): return self.board == other.board ...
#
# @dataclass 自动帮你生成 __init__、__repr__、__eq__ 这些方法，
# 你只需要声明字段和类型就行，大大减少样板代码。
#
# field(default_factory=...) 的用法：
# 如果字段的默认值是「可变对象」（list、dict、自定义类实例），
# 不能写 field(default=[])——因为 Python 只会计算一次默认值，
# 所有实例会共享同一个列表！必须用 default_factory 指定一个工厂函数。

@dataclass
class GameSession:
    """
    维护单局游戏的所有状态。

    字段说明：
    - board：棋盘对象（10x9 的棋子二维数组）
    - bot_engine：电脑走棋引擎（根据难度等级决定思考时间）
    - analysis_engine：AI 分析引擎（用于 AI 老师分析局面，走得更深更准）
    - move_history：走棋历史列表（UCI 格式，如 ["a3a4", "b7b6"]）
    - level：当前难度等级（"beginner" / "medium" / "master"）
    - lock：线程锁（Flask 是多线程的，需要保护共享状态）
    """

    # 棋盘：每个新游戏创建一个全新的 ChineseChessBoard 实例
    board: ChineseChessBoard = field(default_factory=ChineseChessBoard)

    # bot_engine：电脑走棋引擎
    # lambda: PikafishEngine(level="medium") 是一个匿名函数（也叫 lambda 函数），
    # 每次创建 GameSession 实例时都会执行它，返回一个新的引擎对象
    bot_engine: PikafishEngine = field(default_factory=lambda: PikafishEngine(level="medium"))

    # analysis_engine：AI 分析引擎，用更高配置以获取更准确的分析
    analysis_engine: PikafishEngine = field(default_factory=lambda: PikafishEngine(level="master"))

    # move_history 是列表（可变对象），必须用 default_factory=list 而不是 default=[]
    move_history: list[str] = field(default_factory=list)

    # 当前难度等级
    level: str = "medium"

    # -------------------------------------------------------------------
    # Python 基础知识点：线程锁 (threading.Lock)
    # -------------------------------------------------------------------
    # 为什么需要锁？
    # Flask 默认是多线程模式，多个 HTTP 请求可能同时到达。
    # 如果两个请求同时修改棋盘状态，就会产生「数据竞争」——状态被破坏。
    #
    # Lock 的工作原理：
    #   with self.lock:
    #       操作共享数据...    ← 同一时刻只有一个线程能进入
    #
    # with 语句进去时自动获取锁（如果别人持有就等待），出来时自动释放。
    # 即使 with 块内抛出异常，锁也会安全释放。
    lock: threading.Lock = field(default_factory=threading.Lock)

    # -------------------------------------------------------------------
    # 序列化方法 —— 把内部状态转成前端能用的字典
    # -------------------------------------------------------------------

    def serialize_state(self) -> dict:
        """线程安全的状态序列化，供 API 路由直接调用。"""
        with self.lock:
            return self.serialize_state_unlocked()

    def serialize_state_unlocked(self) -> dict:
        """
        内部序列化方法（不加锁，调用者必须已持有锁）。

        返回结构：
        {
            "board": [["rR", "rH", ...], [None, ...], ...],  ← 10x9 二维棋子数组
            "piece_names": {"rG": "帅", "bG": "将", ...},     ← 棋子中文名映射
            "current_player": "r",                             ← 当前走棋方
            "winner": None,                                    ← 获胜方
            "move_history": ["a3a4", ...],                     ← 走棋历史
            "level": "medium",                                 ← 当前难度
            "status_text": "轮到红方行棋。"                     ← 状态提示
        }
        """
        board_rows: list[list[str | None]] = []
        for row in range(self.board.ROWS):
            board_rows.append([self.board.get_piece(row, col) for col in range(self.board.COLS)])
        return {
            "board": board_rows,
            "piece_names": self.board.PIECE_NAMES,
            "current_player": self.board.current_player,
            "winner": self.board.winner,
            "move_history": list(self.move_history),  # list() 创建副本
            "level": self.level,
            "status_text": self._status_text(),
        }

    # -------------------------------------------------------------------
    # 游戏操作方法
    # -------------------------------------------------------------------

    def get_valid_moves(self, row: int, col: int) -> list[tuple[int, int]]:
        """
        获取某个棋子当前可以走到的所有位置。

        只有红方回合且游戏未结束时才返回结果（前端只在玩家回合查询）。
        """
        with self.lock:
            if self.board.winner is not None or self.board.current_player != "r":
                return []
            return self.board.get_valid_moves(row, col)

    def apply_player_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> dict:
        """
        处理玩家的走棋请求。

        流程：
        1. 检查游戏状态（未结束、是红方回合、起点有棋子）
        2. 执行玩家走棋
        3. 如果游戏没结束，电脑自动应一步
        4. 返回走棋事件和最新游戏状态

        返回的 events 列表用于前端做动画：
        [
            {"side": "player", "piece": "rR", "from": [6,0], "to": [5,0]},
            {"side": "bot",    "piece": "bC", "from": [2,1], "to": [2,4]},
        ]

        Python 基础知识点：try/except ValueError as exc
        如果走法不合法，board.move_piece 会抛出 ValueError 异常。
        用 except 捕获它，提取错误消息（str(exc)），返回给前端显示。
        """
        with self.lock:
            # === 前置检查 ===
            if self.board.winner is not None:
                return {"ok": False, "error": "对局已经结束。"}
            if self.board.current_player != "r":
                return {"ok": False, "error": "当前不是红方回合。"}

            player_piece = self.board.get_piece(from_row, from_col)
            if player_piece is None:
                return {"ok": False, "error": "起点没有棋子。"}

            # === 玩家走棋 ===
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

            # === 电脑自动应棋 ===
            # 条件：游戏没结束 且 黑方（电脑）还有合法棋步可走
            if self.board.winner is None and self.board.has_any_valid_move(self.board.current_player):
                bestmove = self.bot_engine.get_best_move(self.board)
                if bestmove is not None:
                    # Python 基础知识点：元组解包
                    # (a,b),(c,d) = ((1,2),(3,4)) 一次性给四个变量赋值
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
        """重置游戏到初始状态。"""
        with self.lock:
            self.board = ChineseChessBoard()  # 创建全新棋盘
            self.move_history = []            # 清空走棋历史
            self.bot_engine.new_game()        # 通知引擎新游戏开始
            self.analysis_engine.new_game()
            return {"ok": True, "state": self.serialize_state_unlocked()}

    def set_level(self, level: str) -> dict:
        """
        设置电脑难度。

        Python 基础知识点：str.lower()
        将字符串转为小写，确保 "Medium"/"MEDIUM"/"medium" 都能正常处理。
        """
        level = level.lower()
        with self.lock:
            self.level = level
            self.bot_engine.set_level(level)
            return {"ok": True, "state": self.serialize_state_unlocked()}

    def ask_agent(self, message: str) -> dict:
        """
        让 AI 老师回答用户问题。

        流程：
        1. 快照当前棋盘（克隆副本 + 复制走棋历史）
        2. 调用 chess_agent.ask_xiangqi_agent() 获取 AI 分析
        3. 返回 AI 回答和引擎分析结果

        Python 基础知识点：为何要 clone() 和 list() 副本？
        Python 中 list 是「可变对象」，如果直接传递引用，
        AI 分析过程中棋盘状态可能被其他请求修改，导致分析结果不一致。
        所以这里先用 clone() 和 list() 创建独立副本。
        """
        board_snapshot = self.board.clone()
        move_history = list(self.move_history)  # 创建独立副本
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

    # -------------------------------------------------------------------
    # 状态文字生成
    # -------------------------------------------------------------------

    def _status_text(self) -> str:
        """根据当前游戏状态生成中文提示文字。"""
        if self.board.winner == "r":
            return "对局结束，红方获胜。"
        if self.board.winner == "b":
            return "对局结束，黑方获胜。"
        if self.board.current_player == "r":
            return "轮到红方行棋。"
        return "轮到黑方行棋。"

    # -------------------------------------------------------------------
    # 清理
    # -------------------------------------------------------------------

    def close(self) -> None:
        """关闭引擎子进程，释放系统资源。"""
        self.bot_engine.stop()
        self.analysis_engine.stop()


# ===========================================================================
# 辅助函数
# ===========================================================================

def open_browser() -> None:
    """
    用系统默认浏览器打开游戏页面。

    webbrowser.open(url) 是 Python 标准库提供的方法，
    会自动检测操作系统并使用合适的浏览器打开 URL。
    """
    webbrowser.open("http://127.0.0.1:5000")


# ===========================================================================
# 程序入口 —— 脚本从这里开始运行
# ===========================================================================

# ---------------------------------------------------------------------------
# Python 基础知识点：if __name__ == "__main__" 的作用
# ---------------------------------------------------------------------------
# 当一个 .py 文件被直接运行时（如 python main.py），Python 会把
# 特殊变量 __name__ 设为 "__main__"。
# 当这个文件被其他模块 import 时，__name__ 则是模块名（"main"）。
#
# 这个 if 的作用：「只在直接运行时执行，被 import 时跳过」。
# 为什么要这样？试想如果 chess_agent.py 中 import main，
# 没有这个 if 的话，一 import 就会启动 Web 服务器——这显然不对。
#
# 这是一个非常重要的 Python 惯用法，几乎每个可运行的 .py 文件都有。

if __name__ == "__main__":
    # 1. 创建 Flask 应用
    app = create_app()

    # 2. 延迟 1 秒后自动打开浏览器
    # threading.Timer(interval, function) 在新线程中等待 interval 秒后执行 function
    # 延迟是为了确保 Flask 服务器已经启动好
    threading.Timer(1.0, open_browser).start()

    # 3. 启动 Flask 开发服务器
    # host="127.0.0.1"  → 只监听本机，外部无法访问（安全）
    # port=5000         → 监听 5000 端口
    # debug=False       → 关闭调试模式（生产环境下应关闭）
    # threaded=True     → 启用多线程模式（默认就是 True，这里显式标注）
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
