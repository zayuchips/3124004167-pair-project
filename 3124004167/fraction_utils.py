"""分数显示与解析：把 Fraction 变成人能读的写法，也能把文字变回 Fraction。

程序内部所有数值都用标准库的 fractions.Fraction 保存，
好处是分数运算永远精确，不会出现 0.333333 这种浮点误差。

题目要求的写法：
    自然数    -> 5
    真分数    -> 3/5
    带分数    -> 2'3/8       （二又八分之三）
"""

from fractions import Fraction

# 带分数的分隔符，作业原文用的是中文排版的 "’"，
# 但键盘上一般敲 ASCII 的 "'"，所以两种都认。
APOSTROPHES = "'’′"


def format_fraction(value: Fraction) -> str:
    """把分数变成题目要求的文字写法。"""
    if value.denominator == 1:
        return str(value.numerator)                    # 整数
    if abs(value.numerator) < value.denominator:
        return f"{value.numerator}/{value.denominator}"  # 真分数（含 0）
    sign = "-" if value < 0 else ""
    value = abs(value)
    whole = value.numerator // value.denominator       # 整数部分
    rest = value.numerator % value.denominator         # 剩余分子
    return f"{sign}{whole}'{rest}/{value.denominator}"  # 带分数


def parse_fraction(text: str) -> Fraction:
    """把 "5"、"3/5"、"2'3/8" 这样的文字转回 Fraction。"""
    text = text.strip()
    if not text:
        raise ValueError("空白的答案")
    for mark in APOSTROPHES:
        if mark in text:
            whole, _, rest = text.partition(mark)
            return Fraction(int(whole)) + parse_fraction(rest)
    if "/" in text:
        numerator, _, denominator = text.partition("/")
        if int(denominator) == 0:
            raise ValueError("分母不能为 0")
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(text))
