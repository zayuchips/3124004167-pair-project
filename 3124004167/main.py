"""程序入口：自动生成小学四则运算题目的命令行程序。

用法：
    生成题目   python3 main.py -n 10 -r 10
    判卷       python3 main.py -e Exercises.txt -a Answers.txt
"""

import argparse
import sys
import time

from checker import GRADE_FILE, check
from generator import ANSWER_FILE, EXERCISE_FILE, make_problems, write_problems

DEFAULT_COUNT = 10


def build_parser():
    """定义 -n / -r / -e / -a 四个命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="Myapp",
        description="自动生成小学四则运算题目的命令行程序",
        epilog="生成：python3 main.py -n 10 -r 10    判卷：python3 main.py -e Exercises.txt -a Answers.txt",
    )
    parser.add_argument("-n", type=int, metavar="数量", help="生成题目的个数（不填默认 10）")
    parser.add_argument(
        "-r", type=int, metavar="范围", help="题目中数值（自然数、真分数和真分数分母）的范围，必须给定"
    )
    parser.add_argument("-e", metavar="题目文件", help="待批改的题目文件，需与 -a 一起使用")
    parser.add_argument("-a", metavar="答案文件", help="待批改的答案文件，需与 -e 一起使用")
    return parser


def generate(args, parser):
    """生成题目模式。"""
    if args.r is None:
        print("错误：必须用 -r 参数指定数值范围，例如 python3 main.py -n 10 -r 10")
        parser.print_help()
        return 1
    if args.r < 1:
        print("错误：-r 必须是大于等于 1 的自然数")
        return 1

    count = DEFAULT_COUNT if args.n is None else args.n
    if count < 1:
        print("错误：-n 必须是大于等于 1 的自然数")
        return 1

    started = time.perf_counter()
    problems = make_problems(count, args.r)
    write_problems(problems)
    used = time.perf_counter() - started

    print(f"题目已写入 {EXERCISE_FILE}，答案已写入 {ANSWER_FILE}")
    print(f"共生成 {len(problems)} 道题目，用时 {used:.2f} 秒")
    if len(problems) < count:
        print(f"提示：-r {args.r} 的范围太小，凑不出 {count} 道互不重复的题目，只生成了 {len(problems)} 道")
    return 0


def grade(args):
    """判卷模式。"""
    if not (args.e and args.a):
        print("错误：判卷要同时给出题目文件和答案文件，例如 python3 main.py -e Exercises.txt -a Answers.txt")
        return 1
    try:
        correct, wrong = check(args.e, args.a)
    except FileNotFoundError as error:
        print(f"错误：{error}")
        return 1
    print(f"判卷完成，结果已写入 {GRADE_FILE}")
    print(f"正确 {len(correct)} 题，错误 {len(wrong)} 题")
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.e or args.a:
        return grade(args)
    return generate(args, parser)


if __name__ == "__main__":
    sys.exit(main())
