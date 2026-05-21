"""Flask 入口，负责自由对弈和课程模式。"""

from __future__ import annotations

import atexit
import json
import queue
import threading
import webbrowser
from dataclasses import dataclass, field

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

import chess_agent
import course_manager
from board import ChineseChessBoard
from pikafish_engine import PikafishEngine


def create_app() -> Flask:
    """创建 Flask 应用并注册全部页面和 API。"""
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
        result = session.apply_player_move(
            int(payload["from_row"]),
            int(payload["from_col"]),
            int(payload["to_row"]),
            int(payload["to_col"]),
        )
        return jsonify(result)

    @app.post("/api/reset")
    def post_reset():
        return jsonify(session.reset())

    @app.post("/api/level")
    def post_level():
        payload = request.get_json(force=True)
        return jsonify(session.set_level(payload["level"]))

    @app.post("/api/chat")
    def post_chat():
        payload = request.get_json(force=True)
        return Response(
            stream_with_context(session.stream_agent(payload["message"])),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/courses")
    def get_courses():
        return jsonify({"courses": session.list_courses()})

    @app.post("/api/course/start")
    def post_course_start():
        payload = request.get_json(force=True)
        course_id = payload["course_id"]
        lesson_index = int(payload.get("lesson_index", 0))
        return jsonify(session.start_course(course_id, lesson_index))

    @app.post("/api/course/chat")
    def post_course_chat():
        payload = request.get_json(force=True)
        return Response(
            stream_with_context(session.stream_course_agent(payload["message"])),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/course/next-section")
    def post_course_next_section():
        return jsonify(session.course_next_section())

    @app.get("/api/course/state")
    def get_course_state():
        return jsonify(session.serialize_course_state())

    @app.post("/api/course/stop")
    def post_course_stop():
        return jsonify(session.stop_course())

    atexit.register(session.close)
    return app


@dataclass
class GameSession:
    """维护当前棋局和课程状态。"""

    board: ChineseChessBoard = field(default_factory=ChineseChessBoard)
    bot_engine: PikafishEngine = field(default_factory=lambda: PikafishEngine(level="medium"))
    analysis_engine: PikafishEngine = field(default_factory=lambda: PikafishEngine(level="master"))
    move_history: list[str] = field(default_factory=list)
    level: str = "medium"
    lock: threading.Lock = field(default_factory=threading.Lock)
    course_mode: bool = False
    active_course_id: str | None = None
    active_section_index: int = 0
    current_course: dict | None = None
    course_history: list[dict[str, str]] = field(default_factory=list)

    def serialize_state(self) -> dict:
        with self.lock:
            return self.serialize_state_unlocked()

    def serialize_state_unlocked(self) -> dict:
        board_rows = [
            [self.board.get_piece(row, col) for col in range(self.board.COLS)]
            for row in range(self.board.ROWS)
        ]
        course_state = self.serialize_course_state_unlocked()
        return {
            "board": board_rows,
            "piece_names": self.board.PIECE_NAMES,
            "current_player": self.board.current_player,
            "winner": self.board.winner,
            "move_history": list(self.move_history),
            "level": self.level,
            "status_text": self._status_text(),
            "mode": "course" if self.course_mode else "free",
            "course_state": course_state,
        }

    def serialize_course_state(self) -> dict:
        with self.lock:
            return self.serialize_course_state_unlocked()

    def serialize_course_state_unlocked(self) -> dict:
        section = self._current_section_unlocked()
        if not self.course_mode or self.current_course is None or section is None:
            return {
                "active": False,
                "course_id": None,
                "course_title": None,
                "section_index": 0,
                "section_count": 0,
                "section_type": None,
                "section_title": None,
                "section_content": None,
                "section_hints": [],
            }

        return {
            "active": True,
            "course_id": self.active_course_id,
            "course_title": self.current_course["title"],
            "section_index": self.active_section_index,
            "section_count": len(self.current_course["sections"]),
            "section_type": section["type"],
            "section_title": section["title"],
            "section_content": section["content"],
            "section_hints": list(section.get("hints") or []),
        }

    def list_courses(self) -> list[dict]:
        """返回课程摘要，供前端下拉框使用。"""
        summaries = []
        for course in course_manager.load_all_courses():
            summaries.append(
                {
                    "id": course["id"],
                    "title": course["title"],
                    "description": course["description"],
                    "section_count": len(course.get("sections", [])),
                }
            )
        return summaries

    def get_valid_moves(self, row: int, col: int) -> list[tuple[int, int]]:
        """课程模式下允许操作当前轮到的一方；自由模式只允许红方。"""
        with self.lock:
            if self.board.winner is not None:
                return []
            if not self.course_mode and self.board.current_player != "r":
                return []
            return self.board.get_valid_moves(row, col)

    def apply_player_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> dict:
        """处理玩家一步棋。课程模式下也会自动帮对手应招。"""
        with self.lock:
            if self.board.winner is not None:
                return {"ok": False, "error": "对局已经结束。"}
            if not self.course_mode and self.board.current_player != "r":
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
            if self.course_mode:
                self._append_course_history_unlocked(
                    "system",
                    self._describe_move(player_piece, from_row, from_col, to_row, to_col, "学生"),
                )

            if (
                self.board.winner is None
                and self.board.has_any_valid_move(self.board.current_player)
            ):
                reply_engine = self.bot_engine
                if self.course_mode:
                    self.analysis_engine = self._restart_engine_if_needed(self.analysis_engine, "master")
                    reply_engine = self.analysis_engine

                bestmove = reply_engine.get_best_move(self.board)
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
                    if self.course_mode:
                        self._append_course_history_unlocked(
                            "system",
                            self._describe_move(bot_piece, bot_from_row, bot_from_col, bot_to_row, bot_to_col, "对手"),
                        )

            return {"ok": True, "events": events, "state": self.serialize_state_unlocked()}

    def reset(self) -> dict:
        """自由模式重开，课程模式则回到当前节的初始局面。"""
        with self.lock:
            if self.course_mode and self.current_course is not None:
                self._load_section_board_unlocked(self.active_section_index)
                self._refresh_engines_unlocked()
                return {
                    "ok": True,
                    "state": self.serialize_state_unlocked(),
                    "course_state": self.serialize_course_state_unlocked(),
                }

            self._reset_free_board_unlocked()
            self._refresh_engines_unlocked()
            return {"ok": True, "state": self.serialize_state_unlocked()}

    def set_level(self, level: str) -> dict:
        """设置电脑难度。"""
        level = level.lower()
        with self.lock:
            self.level = level
            self.bot_engine.set_level(level)
            return {"ok": True, "state": self.serialize_state_unlocked()}

    def ask_agent(self, message: str) -> dict:
        """自由对弈模式下的聊天。"""
        with self.lock:
            self.analysis_engine = self._restart_engine_if_needed(self.analysis_engine, "master")
            board_snapshot = self.board.clone()
            move_history = list(self.move_history)
        try:
            result = chess_agent.ask_xiangqi_agent(
                board=board_snapshot,
                user_question=message,
                move_history=move_history,
                analysis_engine=self.analysis_engine,
            )
        except Exception:
            engine_analysis = self.analysis_engine.analyze_position(board_snapshot)
            result = {
                "response": chess_agent._build_local_fallback(board_snapshot, engine_analysis),
                "engine_analysis": engine_analysis,
            }
        return {
            "ok": True,
            "message": result["response"],
            "engine_analysis": result["engine_analysis"],
            "source": "llm" if result["response"] != chess_agent._build_local_fallback(board_snapshot, result["engine_analysis"]) else "fallback",
        }

    def stream_agent(self, message: str):
        """自由对弈模式下的流式聊天。"""
        with self.lock:
            self.analysis_engine = self._restart_engine_if_needed(self.analysis_engine, "master")
            board_snapshot = self.board.clone()
            move_history = list(self.move_history)

        event_queue: queue.Queue[tuple[str, dict]] = queue.Queue()

        def worker() -> None:
            try:
                result = chess_agent.ask_xiangqi_agent(
                    board=board_snapshot,
                    user_question=message,
                    move_history=move_history,
                    analysis_engine=self.analysis_engine,
                    stream_callback=lambda chunk: event_queue.put(("chunk", {"text": chunk})),
                )
                fallback_text = chess_agent._build_local_fallback(board_snapshot, result["engine_analysis"])
                source = "llm" if result["response"] != fallback_text else "fallback"
                event_queue.put(
                    (
                        "done",
                        {
                            "ok": True,
                            "message": result["response"],
                            "engine_analysis": result["engine_analysis"],
                            "source": source,
                        },
                    )
                )
            except Exception:
                engine_analysis = self.analysis_engine.analyze_position(board_snapshot)
                fallback_text = chess_agent._build_local_fallback(board_snapshot, engine_analysis)
                event_queue.put(("chunk", {"text": fallback_text}))
                event_queue.put(
                    (
                        "done",
                        {
                            "ok": True,
                            "message": fallback_text,
                            "engine_analysis": engine_analysis,
                            "source": "fallback",
                        },
                    )
                )

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event, payload = event_queue.get()
            yield _sse_event(event, payload)
            if event == "done":
                break

    def start_course(self, course_id: str, lesson_index: int = 0) -> dict:
        """进入课程模式并切到指定节。"""
        with self.lock:
            course = course_manager.get_course(course_id)
            if course is None:
                return {"ok": False, "error": "没有找到这节课程。"}

            sections = course.get("sections", [])
            if not sections:
                return {"ok": False, "error": "课程内容为空。"}
            if not 0 <= lesson_index < len(sections):
                return {"ok": False, "error": "课节索引超出范围。"}

            self.course_mode = True
            self.active_course_id = course_id
            self.active_section_index = lesson_index
            self.current_course = course
            self.course_history = []
            self._load_section_board_unlocked(lesson_index)
            self._refresh_engines_unlocked()
            self._append_course_section_intro_unlocked()
            return {
                "ok": True,
                "state": self.serialize_state_unlocked(),
                "course_state": self.serialize_course_state_unlocked(),
                "section": self._current_section_unlocked(),
            }

    def course_next_section(self) -> dict:
        """推进到下一节，必要时加载对应 FEN。"""
        with self.lock:
            if not self.course_mode or self.current_course is None:
                return {"ok": False, "error": "当前不在课程模式。"}

            next_index = self.active_section_index + 1
            if next_index >= len(self.current_course["sections"]):
                return {"ok": False, "error": "已经是最后一节。"}

            self.active_section_index = next_index
            self.course_history = []
            self._load_section_board_unlocked(next_index)
            self._refresh_engines_unlocked()
            self._append_course_section_intro_unlocked()
            return {
                "ok": True,
                "state": self.serialize_state_unlocked(),
                "course_state": self.serialize_course_state_unlocked(),
                "section": self._current_section_unlocked(),
            }

    def stop_course(self) -> dict:
        """退出课程模式并恢复自由对弈初始局面。"""
        with self.lock:
            self.course_mode = False
            self.active_course_id = None
            self.active_section_index = 0
            self.current_course = None
            self.course_history = []
            self._reset_free_board_unlocked()
            self._refresh_engines_unlocked()
            return {
                "ok": True,
                "state": self.serialize_state_unlocked(),
                "course_state": self.serialize_course_state_unlocked(),
            }

    def ask_course_agent(self, message: str) -> dict:
        """课程模式聊天，带上最小化课程上下文。"""
        with self.lock:
            if not self.course_mode or self.current_course is None:
                return {"ok": False, "error": "当前不在课程模式。"}

            section = self._current_section_unlocked()
            if section is None:
                return {"ok": False, "error": "当前课程节不存在。"}

            self.analysis_engine = self._restart_engine_if_needed(self.analysis_engine, "master")
            board_snapshot = self.board.clone()
            move_history = list(self.move_history)
            system_prompt = self._build_active_course_prompt_unlocked(section)
            composed_question = self._compose_course_user_question_unlocked(message)
            section_snapshot = {
                "title": section["title"],
                "type": section["type"],
                "content": section["content"],
                "hints": list(section.get("hints") or []),
            }

        try:
            result = chess_agent.ask_xiangqi_agent(
                board=board_snapshot,
                user_question=composed_question,
                move_history=move_history,
                analysis_engine=self.analysis_engine,
                system_prompt=system_prompt,
            )
            source = "llm"
            if self._looks_like_meta_reply(result["response"]):
                rewritten = chess_agent.rewrite_course_reply(result["response"])
                if rewritten and not self._looks_like_meta_reply(rewritten):
                    result["response"] = rewritten
        except Exception:
            engine_analysis = self._safe_analyze(board_snapshot)
            result = {
                "response": self._build_course_fallback(
                    board_snapshot,
                    section_snapshot,
                    message,
                    engine_analysis,
                ),
                "engine_analysis": engine_analysis,
            }
            source = "fallback"
        with self.lock:
            self._append_course_history_unlocked("user", message)
            self._append_course_history_unlocked("assistant", result["response"])
        return {
            "ok": True,
            "message": result["response"],
            "engine_analysis": result["engine_analysis"],
            "course_state": self.serialize_course_state(),
            "source": source,
        }

    def stream_course_agent(self, message: str):
        """课程模式下的流式聊天。"""
        with self.lock:
            if not self.course_mode or self.current_course is None:
                yield _sse_event("done", {"ok": False, "error": "当前不在课程模式。"})
                return

            section = self._current_section_unlocked()
            if section is None:
                yield _sse_event("done", {"ok": False, "error": "当前课程节不存在。"})
                return

            self.analysis_engine = self._restart_engine_if_needed(self.analysis_engine, "master")
            board_snapshot = self.board.clone()
            move_history = list(self.move_history)
            system_prompt = self._build_active_course_prompt_unlocked(section)
            composed_question = self._compose_course_user_question_unlocked(message)
            section_snapshot = {
                "title": section["title"],
                "type": section["type"],
                "content": section["content"],
                "hints": list(section.get("hints") or []),
            }

        event_queue: queue.Queue[tuple[str, dict]] = queue.Queue()

        def worker() -> None:
            try:
                result = chess_agent.ask_xiangqi_agent(
                    board=board_snapshot,
                    user_question=composed_question,
                    move_history=move_history,
                    analysis_engine=self.analysis_engine,
                    system_prompt=system_prompt,
                    stream_callback=lambda chunk: event_queue.put(("chunk", {"text": chunk})),
                )
                source = "llm"
                if self._looks_like_meta_reply(result["response"]):
                    rewritten = chess_agent.rewrite_course_reply(result["response"])
                    if rewritten and not self._looks_like_meta_reply(rewritten):
                        result["response"] = rewritten
                        source = "rewritten"
                        event_queue.put(("replace", {"text": rewritten}))

                with self.lock:
                    self._append_course_history_unlocked("user", message)
                    self._append_course_history_unlocked("assistant", result["response"])
                    course_state = self.serialize_course_state_unlocked()

                event_queue.put(
                    (
                        "done",
                        {
                            "ok": True,
                            "message": result["response"],
                            "engine_analysis": result["engine_analysis"],
                            "course_state": course_state,
                            "source": source,
                        },
                    )
                )
            except Exception:
                engine_analysis = self._safe_analyze(board_snapshot)
                fallback_text = self._build_course_fallback(
                    board_snapshot,
                    section_snapshot,
                    message,
                    engine_analysis,
                )
                with self.lock:
                    self._append_course_history_unlocked("user", message)
                    self._append_course_history_unlocked("assistant", fallback_text)
                    course_state = self.serialize_course_state_unlocked()
                event_queue.put(("chunk", {"text": fallback_text}))
                event_queue.put(
                    (
                        "done",
                        {
                            "ok": True,
                            "message": fallback_text,
                            "engine_analysis": engine_analysis,
                            "course_state": course_state,
                            "source": "fallback",
                        },
                    )
                )

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event, payload = event_queue.get()
            yield _sse_event(event, payload)
            if event == "done":
                break

    def _build_active_course_prompt_unlocked(self, section: dict) -> str:
        """在课程通用提示后补上当前节上下文。"""
        course_prompt = course_manager.build_course_system_prompt(self.current_course)
        section_hints = section.get("hints") or []
        hints_text = "\n".join(f"- {hint}" for hint in section_hints) if section_hints else "无"
        history_lines = []
        for item in self.course_history[-6:]:
            role_name = {"user": "学生", "assistant": "老师", "system": "背景"}.get(item["role"], item["role"])
            history_lines.append(f"{role_name}：{item['content']}")
        history_text = "\n".join(history_lines) if history_lines else "无"
        section_prompt = f"""
以下内容都是教学背景，只供你理解，不要原样复述。
当前课程：{self.current_course['title']}
当前节次：第 {self.active_section_index + 1} 节 / 共 {len(self.current_course['sections'])} 节
当前节类型：{section['type']}
当前节标题：{section['title']}
当前节说明：
{section['content']}
当前节提示：
{hints_text}
最近对话摘录：
{history_text}
""".strip()
        return f"{course_prompt}\n\n{section_prompt}"

    def _current_section_unlocked(self) -> dict | None:
        if self.current_course is None:
            return None
        sections = self.current_course.get("sections", [])
        if not 0 <= self.active_section_index < len(sections):
            return None
        return sections[self.active_section_index]

    def _load_section_board_unlocked(self, section_index: int) -> None:
        """按照课程节的 FEN 切换棋盘；当前节没有 FEN 时沿后续课程节寻找最近局面。"""
        section = self.current_course["sections"][section_index]
        fen = section.get("fen")
        if not fen:
            for candidate in self.current_course["sections"][section_index + 1:]:
                fen = candidate.get("fen")
                if fen:
                    break
        self.board = ChineseChessBoard.from_fen(fen) if fen else ChineseChessBoard()
        self.move_history = []

    def _reset_free_board_unlocked(self) -> None:
        self.board = ChineseChessBoard()
        self.move_history = []

    def _refresh_engines_unlocked(self) -> None:
        """让两个引擎回到新局状态，坏掉时自动重建。"""
        self.bot_engine = self._restart_engine_if_needed(self.bot_engine, self.level)
        self.analysis_engine = self._restart_engine_if_needed(self.analysis_engine, "master")

    def _restart_engine_if_needed(self, engine: PikafishEngine, level: str) -> PikafishEngine:
        try:
            engine.new_game()
            return engine
        except Exception:
            engine.stop()
            replacement = PikafishEngine(level=level)
            replacement.new_game()
            return replacement

    def _safe_analyze(self, board: ChineseChessBoard) -> dict:
        """尽量返回引擎分析；如果实在失败，就给空分析结果。"""
        try:
            self.analysis_engine = self._restart_engine_if_needed(self.analysis_engine, "master")
            return self.analysis_engine.analyze_position(board)
        except Exception:
            return {
                "bestmove": None,
                "score_type": None,
                "score_value": None,
                "depth": None,
                "pv": [],
            }

    def _build_course_fallback(
        self,
        board: ChineseChessBoard,
        section: dict,
        user_message: str,
        engine_analysis: dict,
    ) -> str:
        """课程聊天不可用时，仍然给出像老师一样的本地引导。"""
        bestmove = engine_analysis.get("bestmove")
        hint_lines = section.get("hints") or []
        position_text = self._build_position_observation(board)
        next_question = self._build_next_question(section, board)
        unsure = self._looks_unsure(user_message)

        if unsure:
            prefix = "先不用急着会完整答案，我先帮你把第一层看法搭起来。"
        else:
            prefix = f"你刚才这句话里已经有一个对的方向：{self._extract_positive_fragment(user_message)}。"

        if bestmove:
            move_text = f"如果你想往下验证，可以重点看看走法 {bestmove} 背后的控制关系。"
        else:
            move_text = "这一步先别急着找唯一答案，先把局面的控制关系看清。"

        hint_text = "；".join(hint_lines[:2]) if hint_lines else "先看线路，再看退路。"

        if section["type"] == "demonstration":
            focus = "示范局面最重要的是先说清楚谁在控制哪条线、对方还能往哪逃。"
        elif section["type"] == "exercise":
            focus = "练习题最重要的是先提出一个候选思路，再让棋盘验证它。"
        else:
            focus = "这一节先抓核心概念，不要一次想太多。"

        return (
            f"{prefix}"
            f"{focus}"
            f"{position_text}"
            f"你这一步可以先只完成一个小目标：{hint_text}。"
            f"{move_text}"
            f"{next_question}"
        )

    def _append_course_section_intro_unlocked(self) -> None:
        """把当前节的课题说明写进课程历史，方便 LLM 接着往下教。"""
        section = self._current_section_unlocked()
        if section is None:
            return
        intro = f"{self.current_course['title']}｜{section['title']}：{section['content']}"
        self._append_course_history_unlocked("system", intro)

    def _append_course_history_unlocked(self, role: str, content: str) -> None:
        """追加一条课程对话历史，只保留最近几轮。"""
        self.course_history.append({"role": role, "content": content})
        self.course_history = self.course_history[-8:]

    def _compose_course_user_question_unlocked(self, user_message: str) -> str:
        """把学生本轮发言整理成干净的 user prompt。"""
        message = user_message.strip() or "我暂时没想法。"
        return (
            "请直接对学生说话，不要解释你的思路，不要复述背景或规则。"
            f"\n学生本轮发言：{message}"
        )

    def _looks_like_meta_reply(self, text: str) -> bool:
        """识别模型是否在复述内部提示，而不是直接教学。"""
        markers = [
            "学生说",
            "老师说",
            "最近对话",
            "当前课程",
            "当前节",
            "我会先",
            "按课程方式",
            "接下来请先检查",
            "只推进下一小步",
            "你现在在",
        ]
        stripped = text.strip()
        if stripped.startswith("我们正在讲"):
            return True
        return any(marker in stripped for marker in markers)

    def _describe_move(
        self,
        piece: str | None,
        from_row: int,
        from_col: int,
        to_row: int,
        to_col: int,
        side_name: str,
    ) -> str:
        """把一步棋转成便于教学的自然语言。"""
        piece_name = self.board.PIECE_NAMES.get(piece, "棋子") if piece else "棋子"
        return f"{side_name}把{piece_name}从({from_row},{from_col})走到({to_row},{to_col})。"

    def _looks_unsure(self, user_message: str) -> bool:
        text = user_message.strip()
        unsure_markers = ["不知道", "不懂", "不会", "没思路", "看不懂", "?", "？"]
        return not text or any(marker in text for marker in unsure_markers)

    def _extract_positive_fragment(self, user_message: str) -> str:
        text = user_message.strip().rstrip("。！？!?")
        if len(text) <= 28:
            return text
        return text[:28] + "…"

    def _build_position_observation(self, board: ChineseChessBoard) -> str:
        red_general = board._find_general("r")
        black_general = board._find_general("b")
        observations: list[str] = []

        if red_general and black_general:
            if red_general[1] == black_general[1]:
                observations.append("先看空间关系：红帅和黑将现在在同一条竖线上。")
            else:
                observations.append("先看空间关系：红帅和黑将不在同一路，所以要先找控制线。")

            black_moves = board.get_valid_moves(black_general[0], black_general[1], "b")
            observations.append(f"黑将当前能走的合法点不多，大约有 {len(black_moves)} 个。")

        attack_lines = self._find_major_attack_lines(board)
        if attack_lines:
            observations.append(attack_lines)

        return "".join(observations)

    def _find_major_attack_lines(self, board: ChineseChessBoard) -> str:
        black_general = board._find_general("b")
        if black_general is None:
            return ""

        target_row, target_col = black_general
        for row in range(board.ROWS):
            for col in range(board.COLS):
                piece = board.get_piece(row, col)
                if piece is None or not piece.startswith("r"):
                    continue
                if piece[1] == "R" and (row == target_row or col == target_col):
                    return "红车已经站在能直接压住黑将活动的主线上。"
                if piece[1] == "C" and (row == target_row or col == target_col):
                    return "红炮对着黑将的线路值得重点检查，关键看中间有没有炮架。"
                if piece[1] == "H":
                    moves = board.get_valid_moves(row, col, "r")
                    if black_general in moves:
                        return "红马已经在控制黑将附近的关键落点。"
        return ""

    def _build_next_question(self, section: dict, board: ChineseChessBoard) -> str:
        if section["type"] == "demonstration":
            black_general = board._find_general("b")
            if black_general is not None:
                black_moves = board.get_valid_moves(black_general[0], black_general[1], "b")
                if black_moves:
                    return f"下一步你只回答一个点：如果黑将想逃，它最可能先往哪一格走？"
            return "下一步你只回答一个点：这盘棋里哪条线最重要？"
        if section["type"] == "exercise":
            return "下一步你只要给我一个候选着法，哪怕不确定也可以。"
        return "下一步你只要用一句话说出这节课最关键的结构特征。"

    def _status_text(self) -> str:
        """生成底部状态文本。"""
        if self.board.winner == "r":
            return "对局结束，红方获胜。"
        if self.board.winner == "b":
            return "对局结束，黑方获胜。"
        if self.course_mode:
            course_state = self.serialize_course_state_unlocked()
            if course_state["active"]:
                return (
                    f"课程模式：{course_state['course_title']} "
                    f"第 {course_state['section_index'] + 1}/{course_state['section_count']} 节"
                )
        return "轮到红方行棋。" if self.board.current_player == "r" else "轮到黑方行棋。"

    def close(self) -> None:
        """关闭引擎进程。"""
        self.bot_engine.stop()
        self.analysis_engine.stop()


def open_browser() -> None:
    """启动后自动打开本地页面。"""
    webbrowser.open("http://127.0.0.1:5000")


def _sse_event(event: str, payload: dict) -> str:
    """构造一个 SSE 事件文本。"""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    app = create_app()
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
