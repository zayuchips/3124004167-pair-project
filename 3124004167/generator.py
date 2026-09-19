"""出题模块：生成不重复的题目与答案，并写入 Exercises.txt 和 Answers.txt。"""

import random

from expression import expression_key, random_expression, to_text
from fraction_utils import format_fraction

EXERCISE_FILE = "Exercises.txt"
ANSWER_FILE = "Answers.txt"

# 连续这么多次摇不出「新题目」就认为范围太小、凑不齐了，主动收工。
# 用「连续失败次数」而不是「总次数」，是为了不管 -n 填多大都能在有限时间内结束。
MAX_CONSECUTIVE_FAILURES = 20000


def make_problems(count, r, seed=None):
    """生成 count 道互不重复的题目，返回 [(题目文字, 答案文字), ...]。

    seed 只在测试里用，给定后结果可复现；正常运行时随机。
    """
    if seed is not None:
        random.seed(seed)

    problems = []
    seen = set()
    failures = 0

    while len(problems) < count and failures < MAX_CONSECUTIVE_FAILURES:
        tree, value = random_expression(r)
        key = None if tree is None else expression_key(tree)
        if key is None or key in seen:      # 没摇出来 / 和之前出过的题等价
            failures += 1
            continue
        failures = 0
        seen.add(key)
        problems.append((to_text(tree), format_fraction(value)))

    return problems


def write_problems(problems, exercise_file=EXERCISE_FILE, answer_file=ANSWER_FILE):
    """把题目和答案分别写进两个文件，返回这两个文件名。"""
    with open(exercise_file, "w", encoding="utf-8") as exercise_out, open(
        answer_file, "w", encoding="utf-8"
    ) as answer_out:
        for index, (text, answer) in enumerate(problems, start=1):
            exercise_out.write(f"{index}. {text} =\n")
            answer_out.write(f"{index}. {answer}\n")
    return exercise_file, answer_file
