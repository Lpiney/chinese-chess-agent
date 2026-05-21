"""课程数据加载与课程上下文拼装。"""

from __future__ import annotations

import json
from pathlib import Path


COURSES_DIR = Path(__file__).resolve().parent / "courses"


def load_all_courses() -> list[dict]:
    """读取 courses 目录下的全部课程 JSON。"""
    courses: list[dict] = []
    if not COURSES_DIR.exists():
        return courses

    for path in sorted(COURSES_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as file:
            raw_course = json.load(file)
        courses.append(_normalize_course(raw_course))
    return courses


def get_course(course_id: str) -> dict | None:
    """按课程 id 查找课程。"""
    for course in load_all_courses():
        if course.get("id") == course_id:
            return course
    return None


def build_course_system_prompt(course: dict) -> str:
    """构造最小化课程系统提示，避免过度限制模型表达。"""
    title = (course.get("title") or "").strip()
    description = (course.get("description") or "").strip()
    parts = [
        "你正在进行中国象棋课程教学。",
        "请结合当前课题与局面回答，但不要复述内部背景说明。",
        "如果给出推荐走法，必须与提供的 best move 一致。",
        "如果当前局面已经是终局，就直接按终局讲解，不要继续假设还能往下走。",
        "默认短答，每次只推进一个点，尽量控制在 2 到 4 句内。",
    ]
    if title:
        parts.append(f"当前课程主题：{title}")
    if description:
        parts.append(f"课程简介：{description}")
    return "\n".join(parts)


def _normalize_course(course: dict) -> dict:
    """把原始多节课程压缩成“课程讲解 + 课后作业”两步。"""
    sections = list(course.get("sections") or [])
    if not sections:
        return course

    lesson_parts: list[str] = []
    lesson_fen: str | None = None
    lesson_hints: list[str] = []
    homework_section: dict | None = None

    for section in sections:
        section_type = section.get("type")
        content = (section.get("content") or "").strip()
        title = (section.get("title") or "").strip()
        fen = section.get("fen")

        if section_type == "exercise" and homework_section is None:
            homework_section = section
            continue

        if section_type != "exercise":
            if title and content:
                lesson_parts.append(f"{title}：{content}")
            elif content:
                lesson_parts.append(content)
            if lesson_fen is None and fen:
                lesson_fen = fen
            for hint in section.get("hints") or []:
                if hint not in lesson_hints:
                    lesson_hints.append(hint)

    if homework_section is None:
        homework_section = next((section for section in sections if section.get("fen")), sections[-1])

    homework_content = (homework_section.get("content") or "").strip()
    homework_hints = list(homework_section.get("hints") or [])
    homework_fen = homework_section.get("fen") or lesson_fen

    normalized_sections = [
        {
            "type": "lesson",
            "title": "课程讲解",
            "content": "\n\n".join(part for part in lesson_parts if part) or course.get("description", ""),
            "fen": lesson_fen or homework_fen,
            "hints": lesson_hints[:2],
        },
        {
            "type": "homework",
            "title": "课后作业",
            "content": homework_content or "请根据本课内容完成一次实战练习，走完后让老师点评。",
            "fen": homework_fen or lesson_fen,
            "hints": homework_hints[:2],
        },
    ]

    normalized = dict(course)
    normalized["sections"] = normalized_sections
    return normalized
