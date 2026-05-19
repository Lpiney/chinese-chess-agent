"""Pikafish 引擎封装。"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from board import ChineseChessBoard


class PikafishEngine:
    """通过 UCI 协议驱动 Pikafish。"""

    LEVEL_CONFIG = {
        "beginner": {"movetime": 120, "depth": 5, "hash": 32},
        "medium": {"movetime": 400, "depth": 9, "hash": 64},
        "master": {"movetime": 1400, "depth": 14, "hash": 128},
    }

    def __init__(self, level: str = "medium", engine_path: str | None = None) -> None:
        if level not in self.LEVEL_CONFIG:
            raise ValueError("不支持的难度等级。")
        self.level = level
        project_root = Path(__file__).resolve().parent
        default_path = project_root / "third_party" / "Pikafish" / "src" / "pikafish"
        self.engine_path = Path(engine_path) if engine_path is not None else default_path
        self.process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self.process is not None:
                return
            if not self.engine_path.exists():
                raise FileNotFoundError("没有找到 Pikafish 可执行文件，请先运行 scripts/setup_pikafish.sh。")

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
        with self._lock:
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
        self.start()
        with self._lock:
            self._send_command("ucinewgame")
            self._send_command("isready")
            self._read_until("readyok")

    def set_level(self, level: str) -> None:
        if level not in self.LEVEL_CONFIG:
            raise ValueError("不支持的难度等级。")
        self.level = level
        if self.process is None:
            return
        with self._lock:
            self._apply_level_options()
            self._send_command("isready")
            self._read_until("readyok")

    def get_best_move(self, board: ChineseChessBoard) -> str | None:
        return self.analyze_position(board)["bestmove"]

    def analyze_position(self, board: ChineseChessBoard) -> dict:
        self.start()
        config = self.LEVEL_CONFIG[self.level]
        with self._lock:
            self._send_command(f"position fen {board.to_fen()}")
            self._send_command(f"go depth {config['depth']} movetime {config['movetime']}")

            last_info = {
                "score_type": None,
                "score_value": None,
                "depth": None,
                "pv": [],
            }

            while True:
                line = self._read_line()
                if line.startswith("info "):
                    parsed = self._parse_info_line(line)
                    if parsed is not None:
                        last_info.update(parsed)
                elif line.startswith("bestmove "):
                    parts = line.split()
                    bestmove = parts[1]
                    return {
                        "bestmove": None if bestmove == "(none)" else bestmove,
                        "score_type": last_info["score_type"],
                        "score_value": last_info["score_value"],
                        "depth": last_info["depth"],
                        "pv": last_info["pv"],
                    }

    def _parse_info_line(self, line: str) -> dict | None:
        parts = line.split()
        if "depth" not in parts or "score" not in parts:
            return None

        parsed = {"score_type": None, "score_value": None, "depth": None, "pv": []}
        try:
            depth_index = parts.index("depth")
            parsed["depth"] = int(parts[depth_index + 1])
        except Exception:
            parsed["depth"] = None

        try:
            score_index = parts.index("score")
            parsed["score_type"] = parts[score_index + 1]
            parsed["score_value"] = int(parts[score_index + 2])
        except Exception:
            parsed["score_type"] = None
            parsed["score_value"] = None

        if "pv" in parts:
            pv_index = parts.index("pv")
            parsed["pv"] = parts[pv_index + 1 :]
        return parsed

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
