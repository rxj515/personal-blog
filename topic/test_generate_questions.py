import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_questions


class JudgmentAnswerPlanTests(unittest.TestCase):

    def test_false_answers_are_at_least_half_of_judgment_questions(self):
        question_types = ["判断题"] * 5 + ["单选题", "多选题"]

        plan = generate_questions.create_judgment_answer_plan(question_types)

        self.assertEqual(len(plan), 5)
        self.assertGreaterEqual(list(plan.values()).count("B"), 3)
        self.assertEqual(set(plan), {0, 1, 2, 3, 4})
        self.assertEqual(set(plan.values()), {"A", "B"})

    def test_answer_constraints_cover_single_and_multiple_choice_variants(self):
        question_types = ["单选题"] * 4 + ["多选题"] * 4

        plan = generate_questions.create_answer_constraint_plan(question_types)

        self.assertEqual(
            {plan[index]["required_answer"] for index in range(4)},
            {"A", "B", "C", "D"},
        )
        self.assertEqual(
            {plan[index]["required_correct_count"] for index in range(4, 8)},
            {2, 3, 4, 5},
        )

    def test_prompt_requires_assigned_judgment_answer(self):
        prompt = generate_questions.build_prompt(
            "第一条",
            "法规原文",
            "判断题",
            required_answer="B",
        )

        self.assertIn("本题答案必须是：B（错误）", prompt)


if __name__ == "__main__":
    unittest.main()
