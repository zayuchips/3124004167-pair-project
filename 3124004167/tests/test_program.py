"""单元测试：覆盖数值格式、表达式生成、约束检查、判重、判卷和命令行参数。

运行方式（在本文件所在目录的上一级执行）：
    python3 -m unittest discover -s tests -v
"""

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import checker                                              # noqa: E402
import expression as ex                                     # noqa: E402
import generator                                            # noqa: E402
import main as app                                          # noqa: E402
from fraction_utils import format_fraction, parse_fraction   # noqa: E402


def leaves(tree):
    """取出一棵表达式树的所有叶子（也就是所有操作数）。"""
    if len(tree) == 1:
        yield tree[0]
        return
    yield from leaves(tree[1])
    yield from leaves(tree[2])


class TestFractionText(unittest.TestCase):
    """用例 1-5：数值的显示与解析。"""

    def test_integer_text(self):
        self.assertEqual("7", format_fraction(Fraction(7)))
        self.assertEqual("0", format_fraction(Fraction(0)))

    def test_proper_fraction_text(self):
        self.assertEqual("3/5", format_fraction(Fraction(3, 5)))
        self.assertEqual("8/45", format_fraction(Fraction(8, 45)))

    def test_mixed_fraction_text(self):
        self.assertEqual("2'3/8", format_fraction(Fraction(19, 8)))       # 作业原文的写法
        self.assertEqual("1'17/36", format_fraction(Fraction(53, 36)))

    def test_parse_three_forms(self):
        self.assertEqual(Fraction(7), parse_fraction("7"))
        self.assertEqual(Fraction(3, 5), parse_fraction("3/5"))
        self.assertEqual(Fraction(19, 8), parse_fraction("2'3/8"))
        self.assertEqual(Fraction(19, 8), parse_fraction("2’3/8"))        # 中文排版的撇号也认

    def test_format_and_parse_are_inverse(self):
        for value in [Fraction(0), Fraction(9), Fraction(2, 3), Fraction(19, 8), Fraction(247, 105)]:
            self.assertEqual(value, parse_fraction(format_fraction(value)))


class TestEvaluate(unittest.TestCase):
    """用例 6-10：把算式文字算成结果。"""

    def test_operator_priority(self):
        self.assertEqual(Fraction(7), ex.evaluate_text("1 + 2 × 3"))
        self.assertEqual(Fraction(5), ex.evaluate_text("8 - 6 ÷ 2"))

    def test_brackets(self):
        self.assertEqual(Fraction(9), ex.evaluate_text("(1 + 2) × 3"))
        self.assertEqual(Fraction(1, 2), ex.evaluate_text("2 ÷ (1 + 3)"))

    def test_fraction_arithmetic(self):
        # 作业原文给的例子：1/6 + 1/8 = 7/24
        self.assertEqual(Fraction(7, 24), ex.evaluate_text("1/6 + 1/8"))
        self.assertEqual(Fraction(9, 4), ex.evaluate_text("2'3/8 - 1/8"))

    def test_bad_expression_raises(self):
        for text in ["1 ÷ 0", "1 + 2 ×", "(1 + 2", "1 & 2", "1/0"]:
            with self.assertRaises(ValueError, msg=text):
                ex.evaluate_text(text)

    def test_equal_sign_cuts_the_rest(self):
        self.assertEqual(Fraction(3), ex.evaluate_text("1 + 2 ="))
        self.assertEqual(Fraction(3), ex.evaluate_text("1 + 2 = 999"))     # 等号后面是答案，不看


class TestGenerate(unittest.TestCase):
    """用例 11-20：题目生成与题目要求里的三条硬性约束。"""

    @classmethod
    def setUpClass(cls):
        cls.problems = generator.make_problems(300, 10, seed=20260918)

    def test_text_matches_answer(self):
        """题面能重新算出答案文件里的值 —— 括号一个都不能丢。"""
        for text, answer in self.problems:
            self.assertEqual(parse_fraction(answer), ex.evaluate_text(text), text)

    def test_answers_are_never_negative(self):
        for text, answer in self.problems:
            self.assertGreaterEqual(parse_fraction(answer), 0, text)

    def test_no_negative_in_subtraction(self):
        for text, _ in self.problems:
            problems = [e for e in ex.constraint_errors_text(text) if "负数" in e]
            self.assertEqual([], problems, text)

    def test_division_result_is_proper_fraction(self):
        for text, _ in self.problems:
            problems = [e for e in ex.constraint_errors_text(text) if "真分数" in e]
            self.assertEqual([], problems, text)

    def test_at_most_three_operators(self):
        for text, _ in self.problems:
            self.assertLessEqual(sum(text.count(op) for op in ex.OPERATORS), 3, text)

    def test_problems_are_unique(self):
        keys = [ex.expression_key(ex.parse_tree(text)) for text, _ in self.problems]
        self.assertEqual(len(keys), len(set(keys)))

    def test_texts_are_unique(self):
        """题目文件里不能出现两行一模一样的算式。"""
        texts = [text for text, _ in self.problems]
        self.assertEqual(len(texts), len(set(texts)))

    def test_text_reproduces_the_same_tree(self):
        """印出来的题面解析回去，还应该是同一棵树（括号没多也没少）。"""
        for text, _ in self.problems:
            self.assertEqual(text, ex.to_text(ex.parse_tree(text)), text)

    def test_exchange_rule_for_deduplication(self):
        """作业原文举例：3+(2+1) 与 1+2+3 重复，3+2+1 不重复，1×2 与 2×1 重复。"""
        same = ex.expression_key(ex.parse_tree("3 + (2 + 1)"))
        self.assertEqual(same, ex.expression_key(ex.parse_tree("1 + 2 + 3")))
        self.assertNotEqual(same, ex.expression_key(ex.parse_tree("3 + 2 + 1")))
        self.assertEqual(
            ex.expression_key(ex.parse_tree("1 × 2")), ex.expression_key(ex.parse_tree("2 × 1"))
        )

    def test_bracket_keeps_division_meaningful(self):
        """6 × (1/2 ÷ 4/7)：括号不能省，否则印出来那一步的商就不是真分数了。"""
        tree = ("×", (Fraction(6),), ("÷", (Fraction(1, 2),), (Fraction(4, 7),)))
        text = ex.to_text(tree)
        self.assertEqual("6 × (1/2 ÷ 4/7)", text)
        self.assertEqual(ex.tree_value(tree), ex.evaluate_text(text))
        self.assertEqual([], ex.constraint_errors_text(text))

    def test_operand_range(self):
        for text, _ in self.problems:      # 这批题目用 -r 10 生成
            for node in leaves(ex.parse_tree(text)):
                if node.denominator == 1:
                    self.assertLess(node, 10, text)
                else:
                    self.assertLess(node.denominator, 10, text)
                    self.assertLess(node.numerator, node.denominator, text)

    def test_small_range_does_not_crash(self):
        for r in (1, 2, 3):
            problems = generator.make_problems(5, r, seed=1)
            self.assertGreater(len(problems), 0)
            for text, answer in problems:
                self.assertEqual(parse_fraction(answer), ex.evaluate_text(text), text)

    def test_impossible_count_stops_early(self):
        """-r 1 时只有 0 可用，凑不出 10000 道题，程序要收工而不是死循环。"""
        problems = generator.make_problems(10000, 1, seed=1)
        self.assertGreater(len(problems), 0)
        self.assertLess(len(problems), 10000)


class TestFilesAndGrading(unittest.TestCase):
    """用例 21-24：写题目/答案文件，以及判卷。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.exercise = os.path.join(self.tmp.name, "Exercises.txt")
        self.answer = os.path.join(self.tmp.name, "Answers.txt")
        self.grade = os.path.join(self.tmp.name, "Grade.txt")
        generator.write_problems(
            generator.make_problems(10, 10, seed=7), self.exercise, self.answer
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_format(self):
        with open(self.exercise, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        self.assertEqual(10, len(lines))
        for index, line in enumerate(lines, start=1):
            self.assertRegex(line, rf"^{index}\. .+ =$")

    def test_all_correct(self):
        correct, wrong = checker.check(self.exercise, self.answer, self.grade)
        self.assertEqual([], wrong)
        self.assertEqual(list(range(1, 11)), correct)
        with open(self.grade, encoding="utf-8") as handle:
            self.assertEqual(
                "Correct: 10 (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)\nWrong: 0 ()\n", handle.read()
            )

    def test_some_wrong(self):
        with open(self.answer, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        lines[1] = "2. 0"           # 第 2 题故意答错
        lines[3] = "4. 1/2"         # 第 4 题故意答错
        with open(self.answer, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

        correct, wrong = checker.check(self.exercise, self.answer, self.grade)
        self.assertEqual([2, 4], wrong)
        self.assertEqual([1, 3, 5, 6, 7, 8, 9, 10], correct)

    def test_grade_tolerates_spaces_and_chinese_apostrophe(self):
        """别人的题目/答案文件里空格多一点、撇号是中文的，也要能判。"""
        with open(self.exercise, "w", encoding="utf-8") as handle:
            handle.write("1. 2’3/8 + 1/8 =\n2.   1/6 + 1/8 =\n")
        with open(self.answer, "w", encoding="utf-8") as handle:
            handle.write("1. 2'1/2\n2. 7/24\n")
        correct, wrong = checker.check(self.exercise, self.answer, self.grade)
        self.assertEqual([1, 2], correct)
        self.assertEqual([], wrong)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            checker.check(os.path.join(self.tmp.name, "不存在.txt"), self.answer, self.grade)


class TestCommandLine(unittest.TestCase):
    """用例 25-30：命令行参数、退出码与一万道题的性能。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def run_main(self, argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = app.main(argv)
        return code, buffer.getvalue()

    def test_missing_r_gives_help(self):
        code, output = self.run_main(["-n", "10"])
        self.assertEqual(1, code)
        self.assertIn("错误", output)
        self.assertIn("-r", output)          # 报错同时给出帮助信息

    def test_invalid_range(self):
        code, output = self.run_main(["-n", "10", "-r", "0"])
        self.assertEqual(1, code)
        self.assertIn("错误", output)

    def test_invalid_count(self):
        self.assertEqual(1, self.run_main(["-n", "0", "-r", "10"])[0])

    def test_default_count_is_ten(self):
        code, output = self.run_main(["-r", "10"])          # 只给 -r 时默认 10 道题
        self.assertEqual(0, code)
        self.assertIn("共生成 10 道题目", output)

    def test_generate_then_grade(self):
        code, _ = self.run_main(["-n", "12", "-r", "20"])
        self.assertEqual(0, code)
        with open("Exercises.txt", encoding="utf-8") as handle:
            self.assertEqual(12, len(handle.read().splitlines()))

        code, _ = self.run_main(["-e", "Exercises.txt", "-a", "Answers.txt"])
        self.assertEqual(0, code)
        with open("Grade.txt", encoding="utf-8") as handle:
            self.assertEqual(
                "Correct: 12 (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)\nWrong: 0 ()\n", handle.read()
            )

    def test_only_e_without_a(self):
        code, output = self.run_main(["-e", "Exercises.txt"])
        self.assertEqual(1, code)
        self.assertIn("错误", output)

    def test_thousand_problems_within_seconds(self):
        """需求 9 的冒烟测试：一千道题要秒级完成。"""
        code, output = self.run_main(["-n", "1000", "-r", "100"])
        self.assertEqual(0, code)
        self.assertIn("共生成 1000 道题目", output)
        with open("Answers.txt", encoding="utf-8") as handle:
            self.assertEqual(1000, len(handle.read().splitlines()))
        used = float(re.search(r"用时 (\d+\.\d+) 秒", output).group(1))
        self.assertLess(used, 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
