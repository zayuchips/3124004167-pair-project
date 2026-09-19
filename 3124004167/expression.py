"""四则运算表达式：随机生成、求值、判重、和文字互转。

表达式在内存里用「元组树」表示，一个算式就是一棵树：

    叶子节点：(值,)                 例如 (Fraction(1, 2),)
    内部节点：(运算符, 左子树, 右子树)  例如 ("+", (Fraction(1),), (Fraction(2),))

这么存的好处：括号关系天生就在结构里（哪两棵子树先算一目了然），
不用事后靠字符串去猜；判重、求值、打印都只要递归一趟。
"""

import random
from fractions import Fraction

from fraction_utils import APOSTROPHES, format_fraction

OPERATORS = ("+", "-", "×", "÷")
MAX_OPERATORS = 3         # 题目要求：每道题的运算符不超过 3 个
BUILD_TRIES = 12          # 每个节点最多重摇多少次
TRIVIAL_GUARD = 4         # 范围够大时，顺手避开 0、1 这类“太水”的操作数

# 只有当 -r >= TRIVIAL_GUARD 时才做下面这些筛选：
# 否则范围本来就很小（比如 -r 2 只有 0 和 1），一味挑剔会导致根本出不了题。
TRIVIAL_RULES = {
    "+": lambda left, right: left != 0 and right != 0,
    "-": lambda left, right: right != 0 and left != right,
    "×": lambda left, right: left not in (0, 1) and right not in (0, 1),
    "÷": lambda left, right: right not in (0, 1),
}


# ----------------------------------------------------------------------
# 一、随机生成表达式
# ----------------------------------------------------------------------
def random_operand(r):
    """随机生成一个操作数：自然数（0 ~ r-1）或真分数（分子 < 分母 < r）。"""
    if r < 3 or random.random() < 0.5:
        return Fraction(random.randrange(r))
    denominator = random.randrange(2, r)
    numerator = random.randrange(1, denominator)
    return Fraction(numerator, denominator)


def apply_op(op, left, right):
    """按运算符算出两个数的结果。"""
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "×":
        return left * right
    return left / right


def build_tree(r, operators, tries=BUILD_TRIES):
    """随机造一棵运算符个数恰好为 operators 的表达式树。

    一边造一边检查题目要求：减法不出现负数、除法的结果必须是真分数。
    条件凑不齐就返回 None，交给上一层重摇。
    """
    if operators == 0:
        value = random_operand(r)
        return (value,), value

    for _ in range(tries):
        op = random.choice(OPERATORS)
        left_count = random.randrange(operators)          # 0 ~ operators-1 个
        right_count = operators - 1 - left_count

        left = build_tree(r, left_count, tries)
        if left is None:
            continue
        right = build_tree(r, right_count, tries)
        if right is None:
            continue

        left_tree, left_value = left
        right_tree, right_value = right
        if op == "-":
            if left_value < right_value:                  # 交换左右，保证 e1 >= e2
                left_tree, right_tree = right_tree, left_tree
                left_value, right_value = right_value, left_value
        elif op == "÷" and not 0 < left_value < right_value:
            continue          # 要求“被除数 > 0 且 商 < 1”，也就是商必须是真分数

        if r >= TRIVIAL_GUARD and not TRIVIAL_RULES[op](left_value, right_value):
            continue          # 范围够大，就不要 “× 1”“+ 0” 这种没营养的位置

        return (op, left_tree, right_tree), apply_op(op, left_value, right_value)

    return None


def random_expression(r, retries=120):
    """随机生成一道满足全部要求的题目，实在摇不出就返回 (None, None)。"""
    for _ in range(retries):
        tree, value = build_tree(r, random.randint(1, MAX_OPERATORS))
        if tree is not None:
            return tree, value
    return None, None


# ----------------------------------------------------------------------
# 二、检查与判重
# ----------------------------------------------------------------------
def count_operators(tree):
    """数一数表达式里有几个运算符。"""
    if len(tree) == 1:
        return 0
    return 1 + count_operators(tree[1]) + count_operators(tree[2])


def constraint_errors(tree):
    """逐条检查题目要求，返回问题清单（空列表 = 完全合规）。"""
    errors = []
    if count_operators(tree) > MAX_OPERATORS:
        errors.append("运算符个数超过 3 个")

    def walk(node):
        if len(node) == 1:
            return node[0]
        op, left, right = node
        left_value = walk(left)
        right_value = walk(right)
        if op == "-" and left_value < right_value:
            errors.append("减法出现了负数")
        if op == "÷":
            if right_value == 0:
                errors.append("除数为 0")
                return Fraction(0)
            if not 0 < left_value < right_value:
                errors.append("除法的结果不是真分数")
        return apply_op(op, left_value, right_value)

    walk(tree)
    return errors


def expression_key(tree):
    """判重用的「规范化指纹」。

    题目规定：+ 和 × 的左右两个操作数可以互换，互换后算同一个题目。
    所以只要在每一层把 +、× 的两棵子树按同一套规则排好序，
    两个等价题目的指纹就会完全一样，直接放进 set 就能去重。

    注意 1+2+3 与 3+2+1 不算重复：它们的树形分别是 (1+2)+3 和 (3+2)+1，
    只交换左右的规则无法把一个变成另一个 —— 这正是指纹算法要的结果。
    """
    if len(tree) == 1:
        return ("数值", tree[0])
    op, left, right = tree
    first, second = expression_key(left), expression_key(right)
    if op in ("+", "×") and second < first:
        first, second = second, first
    return (op, first, second)


# ----------------------------------------------------------------------
# 三、表达式 <-> 文字
# ----------------------------------------------------------------------
def to_text(tree, parent_precedence=0, is_right=False):
    """把表达式树打印成文字，只在必需的地方加括号。

    parent_precedence / is_right 记录「我爹的优先级」和「我是爹的右孩子」。
    """
    if len(tree) == 1:
        return format_fraction(tree[0])

    op, left, right = tree
    precedence = 1 if op in ("+", "-") else 2
    text = f"{to_text(left, precedence)} {op} {to_text(right, precedence, True)}"

    # 只有两种情况需要括号：
    # 1. 我的优先级比爹低，例如 (1 + 2) × 3；
    # 2. 我是右孩子、且和爹同级，例如 a - (b + c)、a ÷ (b × c)、a + (b - c)、6 × (1/2 ÷ 4/7)。
    #    这些位置一旦省略括号，算式就会按「从左到右」重新结合，印出来的题面和树不是一个意思
    #    （最典型的是 a × (1/2 ÷ 4/7) 变成 6 × 1/2 ÷ 4/7，那一步的商就不再是真分数）。
    # 左孩子同级时不用加括号：文字按同样的规则解析回来，得到的还是同一棵树。
    need_bracket = precedence < parent_precedence or (
        is_right and precedence == parent_precedence
    )
    return f"({text})" if need_bracket else text


def _read_number(text, i, length):
    """从 text[i] 开始读一个操作数，支持 3、3/5、2'3/8 三种写法。"""
    start = i
    while i < length and text[i].isdigit():
        i += 1
    whole = int(text[start:i])

    if i < length and text[i] in APOSTROPHES:             # 带分数 2'3/8
        i += 1
        start = i
        while i < length and text[i].isdigit():
            i += 1
        numerator = int(text[start:i])
        if i >= length or text[i] != "/":
            raise ValueError("带分数后面必须跟 分子/分母")
        i += 1
        start = i
        while i < length and text[i].isdigit():
            i += 1
        denominator = int(text[start:i])
        if denominator == 0:
            raise ValueError("分母不能为 0")
        return i, Fraction(whole * denominator + numerator, denominator)

    if i < length and text[i] == "/":                     # 真分数 3/5
        i += 1
        start = i
        while i < length and text[i].isdigit():
            i += 1
        denominator = int(text[start:i])
        if denominator == 0:
            raise ValueError("分母不能为 0")
        return i, Fraction(whole, denominator)

    return i, Fraction(whole)


def tokenize(text):
    """把 "1 + 2'3/8 ÷ 3" 这样的文字拆成一串记号。

    遇到等号就停：等号后面是答案，不参与计算。
    """
    tokens = []
    i, length = 0, len(text)
    while i < length:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch == "=":
            break
        elif ch.isdigit():
            i, number = _read_number(text, i, length)
            tokens.append(("数值", number))
        elif ch in "+-×÷*/()":
            tokens.append(("符号", {"*": "×", "/": "÷"}.get(ch, ch)))
            i += 1
        else:
            raise ValueError(f"看不懂的符号：{ch!r}")
    return tokens


class _TreeBuilder:
    """递归下降解析：expression 管 + 和 -，term 管 × 和 ÷，factor 管括号与数字。"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def peek(self):
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None

    def parse(self):
        tree = self.expression()
        if self.position != len(self.tokens):
            raise ValueError("表达式有多余的内容")
        return tree

    def expression(self):
        tree = self.term()
        while True:
            if self._match("+"):
                tree = ("+", tree, self.term())
            elif self._match("-"):
                tree = ("-", tree, self.term())
            else:
                return tree

    def term(self):
        tree = self.factor()
        while True:
            if self._match("×"):
                tree = ("×", tree, self.factor())
            elif self._match("÷"):
                tree = ("÷", tree, self.factor())
            else:
                return tree

    def factor(self):
        token = self.peek()
        if token is None:
            raise ValueError("表达式不完整")
        kind, content = token
        if kind == "数值":
            self.position += 1
            return (content,)
        if content == "(":
            self.position += 1
            tree = self.expression()
            if self.peek() is None or self.peek()[1] != ")":
                raise ValueError("括号没有配对")
            self.position += 1
            return tree
        raise ValueError(f"这里不该出现 {content!r}")

    def _match(self, symbol):
        """当前位置是指定符号就吃掉它，返回 True。"""
        token = self.peek()
        if token is not None and token[0] == "符号" and token[1] == symbol:
            self.position += 1
            return True
        return False


def parse_tree(text):
    """把一段算式文字解析成表达式树。"""
    return _TreeBuilder(tokenize(text)).parse()


def tree_value(tree):
    """递归算出表达式树的值（遇到除以 0 会报错）。"""
    if len(tree) == 1:
        return tree[0]
    op, left, right = tree
    if op == "÷":
        right_value = tree_value(right)
        if right_value == 0:
            raise ValueError("除数不能为 0")
        return tree_value(left) / right_value
    return apply_op(op, tree_value(left), tree_value(right))


def evaluate_text(text):
    """算出一段算式文字的结果，返回 Fraction。"""
    return tree_value(parse_tree(text))


def constraint_errors_text(text):
    """直接检查一段算式文字是否满足题目要求。"""
    return constraint_errors(parse_tree(text))
