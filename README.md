# 结对项目：自动生成小学四则运算题目的命令行程序

学号 3124004167 ｜ 软件工程 计科24级78班 ｜ 作业 [15703](https://edu.cnblogs.com/campus/gdgy/Class78-Grade2024-CS/homework/15703)

## 一、这个程序能做什么

| 模式 | 命令 | 结果 |
| --- | --- | --- |
| 出题 | `python3 main.py -n 10 -r 10` | 生成 10 道题存进 `Exercises.txt`，答案存进 `Answers.txt` |
| 判卷 | `python3 main.py -e Exercises.txt -a Answers.txt` | 统计对错，结果存进 `Grade.txt` |

- `-n` 生成题目的个数（不填默认 10）
- `-r` 题目中数值（自然数、真分数、真分数分母）的范围，**必须给定**，不填会报错并打印帮助信息
- `-e` / `-a` 要批改的题目文件与答案文件，必须成对出现

## 二、运行环境

- Python 3.9 或更高版本
- **不需要任何第三方库**（只用标准库）：生成、判卷、测试、性能分析都可以直接跑
- 只有想额外导出 PNG 性能图时才需要 `pip install pillow`（不装也能生成 SVG 图）

## 三、上手四步

第 1 步，进入代码目录（本仓库里存放代码的文件夹）：

    cd 3124004167

第 2 步，生成 10 道 10 以内的题目：

    python3 main.py -n 10 -r 10

第 3 步，看看生成的文件：

    cat Exercises.txt

    cat Answers.txt

第 4 步，让程序给自己判卷：

    python3 main.py -e Exercises.txt -a Answers.txt

    cat Grade.txt

判卷结果长这样：

    Correct: 8 (1, 2, 4, 5, 6, 8, 9, 10)
    Wrong: 2 (3, 7)

## 四、其他常用命令

生成一万道题（对应作业里的需求 9）：

    python3 main.py -n 10000 -r 100

跑全部单元测试（35 个用例）：

    python3 -m unittest discover -s tests -v

跑性能分析并生成性能分析图：

    python3 profile_report.py

只填 `-r` 不填 `-n` 时默认生成 10 道题：

    python3 main.py -r 10

## 五、目录结构

    3124004167/
    ├── main.py                     命令行入口：解析 -n / -r / -e / -a
    ├── expression.py               表达式核心：随机生成、求值、判重、与文字互转
    ├── generator.py                出题：去重、写 Exercises.txt / Answers.txt
    ├── checker.py                  判卷：写 Grade.txt
    ├── fraction_utils.py           分数的显示与解析（真分数、带分数）
    ├── profile_report.py           性能分析：cProfile 采样 + 画图
    ├── tests/
    │   └── test_program.py         35 个单元测试
    ├── 样例/                       一份可以直接拿来演示的样例数据
    │   ├── Exercises.txt
    │   ├── Answers.txt
    │   ├── 我的答案.txt            （故意错了第 3、7 题）
    │   └── Grade.txt
    ├── profile_chart.png           性能分析图（PNG，可直接上传博客）
    ├── profile_chart.svg           性能分析图（SVG，脚本自动生成）
    └── requirements.txt            说明本项目不依赖第三方库

## 六、作业需求对照表

| 作业要求 | 实现位置 |
| --- | --- |
| `-n` 控制题目个数 | `main.py` 的 `build_parser` / `generate` |
| `-r` 控制数值范围，必须给定，否则报错并给帮助信息 | `main.py` 的 `generate` |
| 计算过程不产生负数 | `expression.py` 的 `build_tree`（减法保证 `e1 >= e2`） |
| 除法结果必须是真分数 | `expression.py` 的 `build_tree`（要求 `0 < 被除数 < 除数`） |
| 每题运算符不超过 3 个 | `expression.py` 的 `MAX_OPERATORS` 与 `build_tree` 的递归深度 |
| 题目不能重复（交换律等价也不许重复） | `expression.py` 的 `expression_key` + `generator.py` 的 `seen` 集合 |
| 题目写入 `Exercises.txt` | `generator.py` 的 `write_problems` |
| 答案写入 `Answers.txt`，真分数写成 `3/5`、`2'3/8` | `generator.py` 的 `write_problems` + `fraction_utils.py` 的 `format_fraction` |
| 支持一万道题目 | `generator.py` 的 `make_problems`（`-n 10000 -r 100` 实测约 0.4 秒） |
| `-e` / `-a` 判卷并输出 `Grade.txt` | `checker.py` 的 `check` |

## 七、实现里值得一提的几个决定

1. **表达式用「元组树」保存**，而不是直接拼字符串。括号关系天生在结构里，求值、判重、打印都只要递归一趟，不用事后靠字符串去猜。
2. **判重按题目原文的规则做**：只允许交换 `+`、`×` 的左右操作数，所以先把两棵子树排序再比较指纹。这样 `1+2+3` 与 `3+2+1` 不会被误判成同一题，而 `3+(2+1)` 与 `1+2+3` 会被判成重复——和作业原文举的例子一致。
3. **打印题面时只在必需的位置加括号**（右孩子同级时一定要加），否则 `6 × (1/2 ÷ 4/7)` 会被印成 `6 × 1/2 ÷ 4/7`，那一步的商就不是真分数了。
4. **数值范围太小时不死循环**：连续 20000 次摇不出新题目就收工，并在终端说明「凑不出这么多不重复的题目」，例如 `-r 1 -n 10000` 只会得到 84 道。
