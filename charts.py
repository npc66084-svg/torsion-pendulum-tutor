"""阶段2/3 的图。只画学生已经填出的 I 值和距离，不读取隐藏真值。"""
import math

import matplotlib.pyplot as plt
from matplotlib import rcParams

import uncertainty

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False


def shapes_figure(rows):
    """阶段2 的 I实验 / I几何 对比。rows: [(label, Iexp, Igeo, E), ...]"""
    usable = []
    for label, experimental, geometric, error in rows or []:
        try:
            experimental = float(experimental)
            geometric = float(geometric)
        except (TypeError, ValueError):
            continue
        usable.append((label, experimental, geometric, error))
    if not usable:
        return None
    figure, axis = plt.subplots(figsize=(8, 3.8), layout="constrained")
    labels = [item[0] for item in usable]
    positions = list(range(len(usable)))
    width = 0.36
    axis.bar([pos - width / 2 for pos in positions],
             [item[1] for item in usable], width,
             label=r"$I_{\mathrm{exp}}$", color="#1f6f6a")
    axis.bar([pos + width / 2 for pos in positions],
             [item[2] for item in usable], width,
             label=r"$I_{\mathrm{geo}}$", color="#b85c38")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel(r"$I$ / kg·m$^2$")
    axis.set_title(r"阶段2：$I_{\mathrm{exp}}$ 与 $I_{\mathrm{geo}}$ 对比")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(fontsize=8)
    return figure


def parallel_figure(symmetric, asymmetric):
    """对称 I–d² 与不对称 I–(d1²+d2²) 两张图；有 3 个点才画回归线。"""
    if not symmetric and not asymmetric:
        return None
    figure, axes = plt.subplots(1, 2, figsize=(10, 3.8), layout="constrained")
    panels = (
        (axes[0], symmetric, r"对称：$I$–$d^2$", r"$d^2$ / m$^2$",
         r"$I_{\mathrm{total}}$ / kg·m$^2$"),
        (axes[1], asymmetric, r"不对称：$I$–($d_1^2+d_2^2$)",
         r"($d_1^2+d_2^2$) / m$^2$", r"$I_{\mathrm{total}}$ / kg·m$^2$"),
    )
    for axis, points, title, xlabel, ylabel in panels:
        if not points:
            axis.set_title(title + "（还没有点）")
            axis.set_xlabel(xlabel)
            axis.set_ylabel(ylabel)
            axis.grid(alpha=0.25)
            continue
        xs = [item[0] for item in points]
        ys = [item[1] for item in points]
        axis.plot(xs, ys, "o", label=r"学生填的 $I_{\mathrm{total}}$")
        if len(points) >= 3:
            try:
                fit = uncertainty.regression(xs, ys)
                left, right = min(xs), max(xs)
                axis.plot([left, right],
                          [fit["slope"] * left + fit["intercept"],
                           fit["slope"] * right + fit["intercept"]],
                          "--", color="#b85c38", label="按学生点拟合")
                axis.set_title(f"{title} ｜ 斜率 {fit['slope']:.3g}，$R^2$={fit['r2']:.4f}")
            except ValueError:
                axis.set_title(title)
        else:
            axis.set_title(title + "（至少 3 个点才拟合）")
        axis.set_xlabel(xlabel)
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    return figure
