"""性能分析：跑一遍 cProfile，打印耗时排名，并画出一张性能分析图。

用法：
    python3 profile_report.py                 # 默认 -n 10000 -r 100，对应题目里的“一万道题”
    python3 profile_report.py -n 20000 -r 100

做三件事：
    1. 真的生成一遍题目（默认一万道），统计总用时；
    2. 打印「自身耗时」「累计耗时」两张排名表，用来定位消耗最大的函数；
    3. 把排名前几名的耗时画成 profile_chart.svg（只用标准库，不依赖第三方画图库）。

生成的 profile_chart.svg 可以用浏览器打开截图，也可以在
「预览」里另存为 PNG 上传到博客园。
"""

import argparse
import cProfile
import os
import pstats
import time

import generator

try:                                        # pillow 是可选的：装了就额外导出一张 PNG
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PILLOW = True
except ImportError:                         # 没装也没关系，SVG 那张图照样能用
    HAVE_PILLOW = False

TOP = 8
SVG_FILE = "profile_chart.svg"
PNG_FILE = "profile_chart.png"
FONT_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def run_profile(count, r):
    """带性能采样地生成一遍题目，返回 (采样器, 实际题数, 总秒数)。"""
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    problems = generator.make_problems(count, r)
    generator.write_problems(problems)
    profiler.disable()
    return profiler, len(problems), time.perf_counter() - started


def collect_rows(profiler):
    """把采样结果整理成 [(函数名, 自身耗时, 累计耗时, 调用次数), ...]。

    profiler 可以是 cProfile.Profile 对象，也可以是 pstats.Stats（读 .prof 文件得来的）。
    """
    stats = profiler if isinstance(profiler, pstats.Stats) else pstats.Stats(profiler)
    rows = []
    for (filename, line, name), (calls, _, own, cumulative, _) in stats.stats.items():
        where = os.path.basename(filename) or "built-in"
        rows.append((f"{name} ({where}:{line})", own, cumulative, calls))
    return rows


def print_table(rows, key, title, top=TOP):
    """按自身/累计耗时打印排名表。"""
    print(f"\n== {title}（前 {top} 名）==")
    print(f"{'函数':<46}{'秒':>8}{'占比':>9}{'调用次数':>10}")
    total = sum(row[key] for row in rows) or 1.0
    for name, own, cumulative, calls in sorted(rows, key=lambda row: row[key], reverse=True)[:top]:
        value = own if key == 1 else cumulative
        print(f"{name:<46}{value:>8.3f}{value / total:>8.1%}{calls:>10}")


def make_svg(rows, count, used, size, top=TOP, path=SVG_FILE):
    """把耗时排名画成横向条形图（左：自身耗时，右：累计耗时）。"""
    bar_width, bar_height, gap = 260, 18, 14
    label_width, value_width = 215, 175      # 左边函数名、右边数值各留多宽
    top_margin = 100
    panel_width = label_width + bar_width + value_width
    width = 20 + 2 * panel_width
    height = top_margin + top * (bar_height + gap) + 60

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g font-family="PingFang SC, Helvetica, Arial, sans-serif">',
        '<text x="20" y="34" font-size="18" font-weight="bold">'
        f"性能分析：生成 {size} 道题目，共 {used:.2f} 秒</text>",
        '<text x="20" y="54" font-size="12" fill="#666">'
        f"cProfile 采样 · 命令行参数 -n {count} · 时间单位：秒（s）</text>",
    ]

    for panel, (key, title) in enumerate([(1, "自身耗时 tottime"), (2, "累计耗时 cumtime")]):
        x0 = 20 + panel * panel_width + label_width        # 条形图的起点
        parts.append(
            f'<text x="{x0}" y="{top_margin - 14}" font-size="14" font-weight="bold">{title}</text>'
        )
        ranked = sorted(rows, key=lambda row: row[key], reverse=True)[:top]
        longest = max(row[key] for row in ranked) or 1.0
        for index, (name, own, cumulative, calls) in enumerate(ranked):
            value = own if key == 1 else cumulative
            y = top_margin + index * (bar_height + gap)
            length = max(2.0, bar_width * value / longest)
            colour = "#3a7afe" if key == 1 else "#f2994a"
            parts.append(
                f'<text x="{x0 - 8}" y="{y + bar_height - 4}" font-size="12" text-anchor="end">'
                f"{escape(short_name(name))}</text>"
            )
            parts.append(
                f'<rect x="{x0}" y="{y}" width="{length:.1f}" height="{bar_height}" '
                f'rx="3" fill="{colour}"/>'
            )
            parts.append(
                f'<text x="{x0 + length + 8}" y="{y + bar_height - 4}" font-size="12" fill="#333">'
                f"{value:.3f}s · {calls} 次</text>"
            )

    parts.append("</g></svg>")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(parts))
    return path


def short_name(name):
    """函数名太长就截短，免得挤出画面。"""
    name = name.split(" (")[0]
    return name if len(name) <= 26 else name[:25] + "…"


def escape(text):
    """SVG 也是 XML：< > & 这些符号必须转义，否则浏览器会当成标签。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_png(rows, count, used, size, top=TOP, path=PNG_FILE):
    """用 pillow 再导出一张 PNG（博客园上传图片更方便）。"""
    scale = 2                                   # 导出 2 倍图，放到网页上更清晰
    bar_width, bar_height, gap = 260, 20, 18
    label_width, value_width = 230, 190
    top_margin = 110
    panel_width = label_width + bar_width + value_width
    width = 20 + 2 * panel_width
    height = top_margin + top * (bar_height + gap) + 50
    image = Image.new("RGB", (width * scale, height * scale), "white")
    draw = ImageDraw.Draw(image)

    def font(size_px):
        for name in FONT_CANDIDATES:
            if os.path.exists(name):
                try:
                    return ImageFont.truetype(name, size_px * scale)
                except OSError:
                    continue
        return ImageFont.load_default()

    def text(x, y, content, size, fill="#111111", anchor="la", bold=False):
        draw.text(
            (x * scale, y * scale),
            content,
            font=font(size),
            fill=fill,
            anchor=anchor,
            # pillow 只加载了常规字重，加粗就用描边模拟一下
            stroke_width=int(scale * 0.7) if bold else 0,
            stroke_fill=fill,
        )

    text(20, 12, f"性能分析：生成 {size} 道题目，共 {used:.2f} 秒", 20, bold=True)
    text(20, 46, f"cProfile 采样 · 命令行参数 -n {count} · 时间单位：秒（s）", 13, "#666666")

    for panel, (key, title) in enumerate([(1, "自身耗时 tottime"), (2, "累计耗时 cumtime")]):
        x0 = 20 + panel * panel_width + label_width
        text(x0, top_margin - 34, title, 15, bold=True)
        ranked = sorted(rows, key=lambda row: row[key], reverse=True)[:top]
        longest = max(row[key] for row in ranked) or 1.0
        for index, (name, own, cumulative, calls) in enumerate(ranked):
            value = own if key == 1 else cumulative
            y = top_margin + index * (bar_height + gap)
            length = max(3.0, bar_width * value / longest)
            text(x0 - 10, y + bar_height // 2, short_name(name), 13, anchor="rm")
            draw.rounded_rectangle(
                [x0 * scale, y * scale, (x0 + length) * scale, (y + bar_height) * scale],
                radius=4 * scale,
                fill="#3a7afe" if key == 1 else "#f2994a",
            )
            text(x0 + length + 8, y + bar_height // 2, f"{value:.3f}s · {calls} 次", 13, "#333333", "lm")

    image.save(path)
    return path


def main():
    parser = argparse.ArgumentParser(description="跑 cProfile 性能分析并画图")
    parser.add_argument("-n", type=int, default=10000, help="生成题目的个数，默认 10000")
    parser.add_argument("-r", type=int, default=100, help="数值范围，默认 100")
    parser.add_argument("--top", type=int, default=TOP, help="表格与图上展示前几名")
    args = parser.parse_args()

    print(f"正在采样：生成 {args.n} 道题目（-r {args.r}）……")
    profiler, size, used = run_profile(args.n, args.r)
    profiler.dump_stats("profile.prof")
    print(f"实际生成 {size} 道题，用时 {used:.2f} 秒；采样数据已存到 profile.prof")

    rows = collect_rows(profiler)
    print_table(rows, 1, "自身耗时 tottime", args.top)
    print_table(rows, 2, "累计耗时 cumtime", args.top)
    print(f"\n性能分析图已写入 {make_svg(rows, args.n, used, size, args.top)}")
    if HAVE_PILLOW:
        print(f"同时也导出了 {make_png(rows, args.n, used, size, args.top)}")
    else:
        print("（没装 pillow，跳过 PNG；需要的话 pip install pillow 再跑一次）")


if __name__ == "__main__":
    main()
