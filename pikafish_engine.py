"""Pikafish 引擎封装，通过 UCI 命令拿到最优走法和评分。"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from board import ChineseChessBoard


class PikafishEngine:
    """
    Pikafish 中国象棋引擎的 Python 封装。

    通过子进程启动 Pikafish 可执行文件，使用 UCI 协议进行通信。
    支持多线程安全调用（内部有锁保护）。

    使用示例：
        engine = PikafishEngine(level="medium")
        engine.start()                        # 启动引擎
        best_move = engine.get_best_move(board)  # 获取最优走法
        engine.stop()                         # 停止引擎
    """

    # 难度等级配置表
    # movetime: 最大思考时间（毫秒）—— 时间越长，走棋质量越高
    # depth:    最大搜索深度（半回合数）—— 深度越深，看得越远
    # hash:     哈希表大小（MB）—— 越大越能记住已搜索过的局面，减少重复计算
    LEVEL_CONFIG = {
        "beginner": {"movetime": 120,  "depth": 5,  "hash": 32},
        "medium":   {"movetime": 400,  "depth": 9,  "hash": 64},
        "master":   {"movetime": 1400, "depth": 14, "hash": 128},
    }

    def __init__(self, level: str = "medium", engine_path: str | None = None) -> None:
        """
        初始化引擎实例（此时还没有启动子进程，需要调用 start() 才会启动）。

        参数：
            level: 难度等级 —— "beginner" | "medium" | "master"
            engine_path: Pikafish 可执行文件路径，默认在 third_party 目录下

        -------------------------------------------------------------------
        Python 基础知识点：self.xxx 的初始化
        -------------------------------------------------------------------
        在 __init__ 中给 self 添加的属性都是「实例属性」，
        每个 PikafishEngine 实例都有自己独立的一份。
        """
        # 校验难度等级
        if level not in self.LEVEL_CONFIG:
            raise ValueError("不支持的难度等级。")
        self.level = level

        # 引擎可执行文件的路径
        # -----------------------------------------------------------------
        # Python 基础知识点：Path 对象 / 运算符
        # -----------------------------------------------------------------
        # Path("/a/b") / "c" / "d" 等价于 "/a/b/c/d"
        # Path 重载了 / 运算符，让路径拼接更加直观和平台无关。
        # Windows 上会自动用 \ 分隔。
        project_root = Path(__file__).resolve().parent
        default_path = project_root / "third_party" / "Pikafish" / "src" / "pikafish"
        self.engine_path = Path(engine_path) if engine_path is not None else default_path

        # 子进程对象引用，启动前为 None
        # -------------------------------------------------------------------
        # Python 基础知识点：Union 类型（| None）
        # -------------------------------------------------------------------
        # subprocess.Popen[str] | None 表示这个变量要么是一个 Popen 对象，
        # 要么是 None。方括号里的 [str] 表示进程的输入/输出以字符串模式工作。
        self.process: subprocess.Popen[str] | None = None

        # 线程锁 —— 保护对子进程的并发访问
        # 如果两个线程同时向 stdin 写命令，输出会乱套
        self._lock = threading.Lock()

    # -------------------------------------------------------------------
    # 引擎生命周期管理
    # -------------------------------------------------------------------

    def start(self) -> None:
        """
        启动 Pikafish 引擎子进程并完成初始化。

        -------------------------------------------------------------------
        Python 基础知识点：subprocess.Popen 参数详解
        -------------------------------------------------------------------
        stdin=subprocess.PIPE   → 创建一个管道，用于向子进程写数据
        stdout=subprocess.PIPE  → 创建一个管道，用于从子进程读数据
        stderr=subprocess.STDOUT → 将标准错误合并到标准输出（2>&1）
        text=True               → 以文本模式（字符串）而不是二进制模式（字节）通信
        bufsize=1               → 行缓冲模式（每写一行立即发送）
        cwd=...                 → 设置子进程的工作目录

        启动后的初始化序列（UCI 协议标准流程）：
        1. 发送 "uci"         → 让引擎进入 UCI 模式
        2. 等待 "uciok"       → 确认引擎支持 UCI 协议
        3. 设置引擎参数        → 多线程数、哈希表大小
        4. 发送 "isready"     → 询问就绪状态
        5. 等待 "readyok"     → 确认引擎就绪可以接收指令
        """
        with self._lock:
            # 幂等性：如果已经启动了，直接返回
            if self.process is not None:
                return

            # 检查可执行文件是否存在
            if not self.engine_path.exists():
                raise FileNotFoundError("没有找到 Pikafish 可执行文件，请先运行 scripts/setup_pikafish.sh。")

            # 启动子进程
            self.process = subprocess.Popen(
                [str(self.engine_path)],  # 命令和参数列表（转为字符串）
                stdin=subprocess.PIPE,    # 标准输入 → 管道
                stdout=subprocess.PIPE,   # 标准输出 → 管道
                stderr=subprocess.STDOUT, # 标准错误合并到标准输出
                text=True,                # 文本模式
                bufsize=1,               # 行缓冲
                cwd=str(self.engine_path.parent),  # 工作目录 = 可执行文件所在目录
            )

            # UCI 初始化序列
            self._send_command("uci")          # 步骤 1
            self._read_until("uciok")          # 步骤 2
            self._apply_level_options()        # 步骤 3
            self._send_command("isready")      # 步骤 4
            self._read_until("readyok")        # 步骤 5

    def stop(self) -> None:
        """
        停止 Pikafish 引擎子进程。

        先尝试优雅地发送 quit 命令让引擎自己退出，
        如果不行再强制终止进程。
        """
        with self._lock:
            if self.process is None:
                return  # 已经停止了
            try:
                self._send_command("quit")  # 优雅退出
            except Exception:
                pass  # 如果管道已断，忽略错误

            # poll() 返回 None 表示进程还在运行，返回整数表示已退出
            if self.process.poll() is None:
                self.process.terminate()  # 强制终止（发送 SIGTERM）
                # 注意：这里没有调用 wait()，可能会有短暂的僵尸状态，
                # 但 Python 的垃圾回收最终会清理
            self.process = None

    def new_game(self) -> None:
        """
        通知引擎新游戏开始。

        "ucinewgame" 命令会清空引擎内部的搜索缓存和历史信息，
        让引擎以全新的状态开始分析。
        """
        self.start()  # 如果还没启动，先启动

        with self._lock:
            self._send_command("ucinewgame")  # 清空内部状态
            self._send_command("isready")     # 确认就绪
            self._read_until("readyok")

    def set_level(self, level: str) -> None:
        """
        动态切换难度等级。

        如果引擎正在运行，会立即应用新的配置参数。
        """
        if level not in self.LEVEL_CONFIG:
            raise ValueError("不支持的难度等级。")
        self.level = level

        # 引擎还没启动就不需要发送参数
        if self.process is None:
            return

        with self._lock:
            self._apply_level_options()
            self._send_command("isready")
            self._read_until("readyok")

    # -------------------------------------------------------------------
    # 局面分析与走棋
    # -------------------------------------------------------------------

    def get_best_move(self, board: ChineseChessBoard) -> str | None:
        """
        获取当前局面下的最优走法。

        返回值：UCI 格式的走法字符串（如 "h2e2"），或者 None（没有合法走法）。

        这是 analyze_position 的简化版，只返回 bestmove 而不包含评分等详细信息。
        用于电脑自动走棋场景。
        """
        return self.analyze_position(board)["bestmove"]

    def analyze_position(self, board: ChineseChessBoard) -> dict:
        """
        分析当前局面，返回包含最优走法和详细评分的字典。

        这是本模块最核心的方法。调用后引擎会开始搜索，
        并实时输出 info 行（包含搜索深度、评分、变例等信息），
        直到找到最优走法后输出 bestmove 行。

        UCI 搜索流程：
        1. position fen <FEN>   → 告诉引擎当前棋盘状态
        2. go depth N movetime M → 开始搜索（限制深度和时间）
        3. 读取 info ... 行      → 引擎持续输出搜索信息
        4. 读取 bestmove ... 行  → 引擎给出最终结论

        返回字典结构：
        {
            "bestmove": "h2e2",       # 最优走法（UCI 格式），"(none)" 转为 None
            "score_type": "cp",       # 评分类型："cp"=厘兵，"mate"=杀棋步数
            "score_value": 35,        # 评分值
            "depth": 9,               # 搜索深度
            "pv": ["h2e2", "b7b6"]    # 最优变例（前几步走法序列）
        }
        """
        # 确保引擎已启动
        self.start()

        # 获取当前难度配置（搜索深度、思考时间）
        config = self.LEVEL_CONFIG[self.level]

        with self._lock:
            # 步骤 1：设置棋盘位置
            self._send_command(f"position fen {board.to_fen()}")

            # 步骤 2：开始搜索
            # go depth 9 movetime 400 表示：最多搜索 9 层，最多思考 400 毫秒
            self._send_command(f"go depth {config['depth']} movetime {config['movetime']}")

            # last_info 存储最后一次收到的 info 行解析结果
            # 引擎在搜索过程中会不断输出 info 行，每行包含越来越深/越来越准的信息，
            # 我们只保留最后一次的信息（最深最准）
            last_info = {
                "score_type": None,
                "score_value": None,
                "depth": None,
                "pv": [],
            }

            # 步骤 3-4：循环读取引擎输出，直到收到 bestmove 行
            while True:
                line = self._read_line()  # 读一行输出

                if line.startswith("info "):
                    # info 行示例：info depth 9 score cp 35 pv h2e2 b7b6 ...
                    parsed = self._parse_info_line(line)
                    if parsed is not None:
                        # 用新的非 None 值更新 last_info
                        # Python 基础知识点：dict.update()
                        # update 会合并两个字典，新的值覆盖旧的，
                        # 如果新字典某个 key 的值是 None，不会覆盖
                        last_info.update(parsed)

                elif line.startswith("bestmove "):
                    # bestmove 行示例：bestmove h2e2 ponder b7b6
                    parts = line.split()
                    bestmove = parts[1]  # "h2e2" 或 "(none)"
                    return {
                        "bestmove": None if bestmove == "(none)" else bestmove,
                        "score_type": last_info["score_type"],
                        "score_value": last_info["score_value"],
                        "depth": last_info["depth"],
                        "pv": last_info["pv"],
                    }

    # -------------------------------------------------------------------
    # UCI info 行解析
    # -------------------------------------------------------------------

    def _parse_info_line(self, line: str) -> dict | None:
        """
        解析 UCI info 行，提取搜索信息。

        info 行格式示例：
            info depth 9 score cp 35 pv h2e2 b7b6 h0g2 ...

        各部分含义：
            depth 9    → 当前搜索到了第 9 层
            score cp 35 → 评分：35 厘兵（约 0.35 个兵的优势）
            score mate 3 → 评分：3 步内将杀
            pv h2e2 b7b6 → 最优变例：前几步的走法序列

        返回解析后的字典，解析失败返回 None。

        -------------------------------------------------------------------
        Python 基础知识点：list.index() 和 list 切片
        -------------------------------------------------------------------
        parts.index("depth") 在列表中查找元素 "depth"，返回它的索引位置。
        parts[depth_index + 1] 取 depth 后面的第一个元素，即深度的数值。

        parts[pv_index + 1 :] 切片：从 PV 标记之后一个位置开始，
        一直到列表末尾的所有元素。
        """
        parts = line.split()  # 以空格分割成单词列表

        # info 行必须包含 depth 和 score 字段，否则不处理
        if "depth" not in parts or "score" not in parts:
            return None

        parsed = {"score_type": None, "score_value": None, "depth": None, "pv": []}

        # 提取搜索深度
        try:
            depth_index = parts.index("depth")
            parsed["depth"] = int(parts[depth_index + 1])
        except Exception:
            parsed["depth"] = None  # 解析失败也不影响，用 None 标记

        # 提取评分
        try:
            score_index = parts.index("score")
            parsed["score_type"] = parts[score_index + 1]    # "cp" 或 "mate"
            parsed["score_value"] = int(parts[score_index + 2])  # 数值
        except Exception:
            parsed["score_type"] = None
            parsed["score_value"] = None

        # 提取最优变例（PV = Principal Variation）
        if "pv" in parts:
            pv_index = parts.index("pv")
            parsed["pv"] = parts[pv_index + 1 :]  # 从 pv 标记之后到末尾

        return parsed

    # -------------------------------------------------------------------
    # 底层通信方法
    # -------------------------------------------------------------------

    def _apply_level_options(self) -> None:
        """
        根据当前难度等级设置引擎参数。

        setoption 命令格式：setoption name <参数名> value <值>
        Threads=1        → 单线程（对于 Web 应用足够了，多线程反而浪费）
        Hash=64          → 哈希表 64MB（用于缓存已搜索过的局面）
        """
        config = self.LEVEL_CONFIG[self.level]
        self._send_command("setoption name Threads value 1")
        self._send_command(f"setoption name Hash value {config['hash']}")

    def _send_command(self, command: str) -> None:
        """
        向引擎子进程发送一条 UCI 命令。

        写入命令字符串 + 换行符到子进程的 stdin，
        然后立即 flush 确保数据被发送出去（bufsize=1 的行缓冲通常会自动 flush，
        但显式 flush 更安全）。

        -------------------------------------------------------------------
        Python 基础知识点：stdin.write() 和 stdin.flush()
        -------------------------------------------------------------------
        write(command + "\n") → 把字符串写入管道的写缓冲区
        flush()               → 强制清空缓冲区，立即发送数据
        如果不用 flush，数据可能等缓冲区满才发送，造成命令延迟。
        """
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("Pikafish 进程未启动。")
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def _read_line(self) -> str:
        """
        从引擎子进程的标准输出读取一行文本。

        -------------------------------------------------------------------
        Python 基础知识点：readline() 的返回值
        -------------------------------------------------------------------
        - 正常情况：返回一行字符串（包含末尾换行符，.strip() 去掉了）
        - 进程退出/管道关闭：返回空字符串 ""
        - 这里把空字符串视为引擎异常退出，抛出异常
        """
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("Pikafish 进程未启动。")
        line = self.process.stdout.readline()
        if line == "":
            raise RuntimeError("Pikafish 进程异常退出。")
        return line.strip()  # 去掉末尾的换行符和多余空白

    def _read_until(self, expected_prefix: str) -> str:
        """
        循环读取引擎输出，直到遇到以指定前缀开头的行。

        这是 UCI 通信中的常见模式：发完命令后等待特定响应。
        例如：发送 "isready" 后等待 "readyok"。

        -------------------------------------------------------------------
        Python 基础知识点：while True 无限循环
        -------------------------------------------------------------------
        while True 会一直循环直到内部某个条件触发 return 或 break。
        在子进程通信中很常用（你不知道什么时候会收到期望的响应）。
        """
        while True:
            line = self._read_line()
            if line.startswith(expected_prefix):
                return line
