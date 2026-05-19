"""Pikafish 引擎封装。"""

from __future__ import annotations

import subprocess
from pathlib import Path

from src.board import ChineseChessBoard


class PikafishEngine:
    """通过 UCI 协议驱动 Pikafish。"""

    LEVEL_CONFIG = {
        "beginner": {"movetime": 80, "depth": 4, "hash": 32},
        "medium": {"movetime": 300, "depth": 8, "hash": 64},
        "master": {"movetime": 1200, "depth": 14, "hash": 128},
    }

    def __init__(
        self,
        level: str = "medium",
        engine_path: str | None = None,
    ) -> None:
        if level not in self.LEVEL_CONFIG:
            raise ValueError("不支持的难度等级。")

        self.level = level
        project_root = Path(__file__).resolve().parent.parent
        default_engine_path = project_root / "third_party" / "Pikafish" / "src" / "pikafish"
        self.engine_path = Path(engine_path) if engine_path is not None else default_engine_path
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        """启动 Pikafish 进程并完成 UCI 握手。"""
        if self.process is not None:
            return
        if not self.engine_path.exists():
            raise FileNotFoundError(
                "没有找到 Pikafish 可执行文件，请先在 third_party/Pikafish/src 中完成编译。"
            )

        self.process = subprocess.Popen(
            [str(self.engine_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(self.engine_path.parent),
        )
        self._send_command("uci")
        self._read_until("uciok")
        self._apply_level_options()
        self._send_command("isready")
        self._read_until("readyok")

    def stop(self) -> None:
        """关闭 Pikafish 进程。"""
        if self.process is None:
            return
        try:
            self._send_command("quit")
        except Exception:
            pass
        if self.process.poll() is None:
            self.process.terminate()
        self.process = None

    def new_game(self) -> None:
        """通知引擎开始新对局。"""
        self.start()
        self._send_command("ucinewgame")
        self._send_command("isready")
        self._read_until("readyok")

    def set_level(self, level: str) -> None:
        """切换机器人难度。"""
        if level not in self.LEVEL_CONFIG:
            raise ValueError("不支持的难度等级。")
        self.level = level
        if self.process is not None:
            self._apply_level_options()
            self._send_command("isready")
            self._read_until("readyok")

    def get_best_move(self, board: ChineseChessBoard) -> str | None:
        """根据当前棋盘返回最佳走法。"""
        self.start()
        config = self.LEVEL_CONFIG[self.level]
        self._send_command(f"position fen {board.to_fen()}")
        self._send_command(f"go depth {config['depth']} movetime {config['movetime']}")

        while True:
            line = self._read_line()
            if line.startswith("bestmove "):
                bestmove = line.split()[1]
                if bestmove == "(none)":
                    return None
                return bestmove

    def _apply_level_options(self) -> None:
        config = self.LEVEL_CONFIG[self.level]
        self._send_command("setoption name Threads value 1")
        self._send_command(f"setoption name Hash value {config['hash']}")

    def _send_command(self, command: str) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("Pikafish 进程未启动。")
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def _read_line(self) -> str:
        if self.process is None or self.process.stdout is None:
            raise RuntimeError("Pikafish 进程未启动。")
        line = self.process.stdout.readline()
        if line == "":
            raise RuntimeError("Pikafish 进程异常退出。")
        return line.strip()

    def _read_until(self, expected_prefix: str) -> str:
        while True:
            line = self._read_line()
            if line.startswith(expected_prefix):
                return line
