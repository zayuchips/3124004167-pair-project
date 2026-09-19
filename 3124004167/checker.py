"""判卷模块：对比题目文件和答案文件，统计对错并写入 Grade.txt。"""

import os
import re

from expression import evaluate_text
from fraction_utils import parse_fraction

GRADE_FILE = "Grade.txt"
INDEX_PREFIX = re.compile(r"^\s*\d+\s*[.、:：]\s*")     # 行首的题号，例如 "3. "


def _strip_index(line):
    """去掉行首题号："3. 1 + 2 =" -> "1 + 2 =" 。"""
    return INDEX_PREFIX.sub("", line).strip()


def _read_lines(path):
    """读文件，去掉空行。"""
    with open(path, encoding="utf-8") as handle:
        return [line for line in handle.read().splitlines() if line.strip()]


def check(exercise_file, answer_file, grade_file=GRADE_FILE):
    """逐题判分，返回 (正确题号列表, 错误题号列表)。"""
    if not os.path.isfile(exercise_file):
        raise FileNotFoundError(f"找不到题目文件：{exercise_file}")
    if not os.path.isfile(answer_file):
        raise FileNotFoundError(f"找不到答案文件：{answer_file}")

    exercises = _read_lines(exercise_file)
    answers = _read_lines(answer_file)

    correct, wrong = [], []
    for index, (exercise, answer) in enumerate(zip(exercises, answers), start=1):
        try:
            expected = evaluate_text(_strip_index(exercise).rstrip("="))
            given = parse_fraction(_strip_index(answer))
        except (ValueError, ZeroDivisionError):
            wrong.append(index)        # 抄错或者看不懂的答案，一律算错
            continue
        if expected == given:
            correct.append(index)
        else:
            wrong.append(index)

    with open(grade_file, "w", encoding="utf-8") as handle:
        handle.write(f"Correct: {len(correct)} ({', '.join(map(str, correct))})\n")
        handle.write(f"Wrong: {len(wrong)} ({', '.join(map(str, wrong))})\n")
    return correct, wrong
