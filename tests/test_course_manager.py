"""course_manager.py 的单元测试。"""

import unittest

import course_manager
from main import GameSession


class CourseManagerTestCase(unittest.TestCase):
    """验证课程读取和提示词拼装。"""

    def test_load_all_courses_returns_eight_courses(self) -> None:
        courses = course_manager.load_all_courses()
        self.assertEqual(len(courses), 8)

    def test_get_course_finds_lesson(self) -> None:
        course = course_manager.get_course("lesson-01")
        self.assertIsNotNone(course)
        self.assertEqual(course["title"], "第1课 对面笑杀法（白脸将）")
        self.assertEqual(len(course["sections"]), 2)
        self.assertEqual(course["sections"][0]["title"], "课程讲解")
        self.assertEqual(course["sections"][1]["title"], "课后作业")

    def test_build_course_system_prompt_contains_course_context(self) -> None:
        course = course_manager.get_course("lesson-02")
        prompt = course_manager.build_course_system_prompt(course)
        self.assertIn("重炮与闷宫杀", prompt)
        self.assertIn("中国象棋课程教学", prompt)
        self.assertNotIn("主攻炮", prompt)

    def test_start_course_uses_first_available_fen_board(self) -> None:
        session = GameSession()
        result = session.start_course("lesson-01", 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["course_state"]["section_index"], 0)
        self.assertEqual(result["course_state"]["section_count"], 2)
        # lesson-01 的第 0 节没有 fen，应回退到后续最近一个带 fen 的课程局面
        self.assertEqual(session.board.to_fen(), "3k5/9/4R4/9/9/9/9/9/9/4K4 w - - 0 1")
        session.close()

    def test_course_mode_auto_replies_after_player_move(self) -> None:
        session = GameSession()
        session.start_course("lesson-03", 0)
        before = len(session.move_history)
        result = session.apply_player_move(2, 3, 0, 4)
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(len(result["events"]), 2)
        self.assertGreater(len(session.move_history), before + 0)
        session.close()


if __name__ == "__main__":
    unittest.main()
