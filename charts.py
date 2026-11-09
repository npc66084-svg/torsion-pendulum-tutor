"""阶段2/3 的图。只画学生已经填出的 I 值和距离，不读取隐藏真值。"""
from matplotlib import rcParams
from matplotlib.figure import Figure

import uncertainty

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False


def shapes_figure(rows, errors=None):
    """阶段2 的 I实验 / I几何 对比。rows: [(label, Iexp, Igeo, E), ...]。

    errors 可选：{label: (u_exp, u_geo)}，用来画误差棒。
    """
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
    figure = Figure(figsize=(8, 3.8), layout="constrained")
    axis = figure.subplots()
    labels = [item[0] for item in usable]
    positions = list(range(len(usable)))
    width = 0.36
    exp_errors = [float((errors or {}).get(label, (0.0, 0.0))[0] or 0.0)
                  for label in labels]
    geo_errors = [float((errors or {}).get(label, (0.0, 0.0))[1] or 0.0)
                  for label in labels]

    def yerr(values):
        return values if any(value > 0 for value in values) else None

    axis.bar([pos - width / 2 for pos in positions],
             [item[1] for item in usable], width,
             yerr=yerr(exp_errors), capsize=3,
             label=r"$I_{\mathrm{exp}}$", color="#1f6f6a")
    axis.bar([pos + width / 2 for pos in positions],
             [item[2] for item in usable], width,
             yerr=yerr(geo_errors), capsize=3,
             label=r"$I_{\mathrm{geo}}$", color="#b85c38")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels)
    axis.set_ylabel(r"$I$ / kg·m$^2$")
    axis.set_title(r"阶段2：$I_{\mathrm{exp}}$ 与 $I_{\mathrm{geo}}$ 对比（误差棒为 $u_c$）")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(fontsize=8)
    return figure


def _fit_panel(axis, residual_axis, points, title, xlabel, ylabel, errors=None):
    if not points:
        axis.set_title(title + "（还没有点）")
        axis.set_xlabel(xlabel)
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.25)
        residual_axis.set_visible(False)
        return
    xs = [item[0] for item in points]
    ys = [item[1] for item in points]
    errs = [float(value or 0.0) for value in (errors or [])]
    if len(errs) != len(points) or not any(value > 0 for value in errs):
        errs = None
    axis.errorbar(xs, ys, yerr=errs, fmt="o", capsize=3,
                  label=r"学生填的 $I_{\mathrm{total}}$")
    if len(points) < 3:
        axis.set_title(title + "（至少 3 个点才拟合）")
        residual_axis.set_visible(False)
    else:
        try:
            fit = uncertainty.regression(xs, ys)
        except ValueError:
            axis.set_title(title)
            residual_axis.set_visible(False)
        else:
            left, right = min(xs), max(xs)
            axis.plot([left, right],
                      [fit["slope"] * left + fit["intercept"],
                       fit["slope"] * right + fit["intercept"]],
                      "--", color="#b85c38", label="按学生点拟合")
            residuals = [y - (fit["slope"] * x + fit["intercept"])
                         for x, y in zip(xs, ys)]
            residual_axis.axhline(0, color="#7c7166", linewidth=0.8)
            residual_axis.vlines(xs, 0, residuals, color="#3f6f8a", linewidth=1.2)
            residual_axis.plot(xs, residuals, "o", color="#3f6f8a", markersize=4)
            residual_axis.set_xlabel(xlabel, fontsize=8)
            residual_axis.set_ylabel("残差", fontsize=8)
            residual_axis.tick_params(labelsize=7)
            residual_axis.grid(alpha=0.2)
            axis.set_title(f"{title} ｜ 斜率 {fit['slope']:.3g}，$R^2$={fit['r2']:.4f}")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)


def parallel_figure(symmetric, asymmetric, errors=None):
    """对称 I–d² 与不对称 I–(d1²+d2²)；上排拟合，下排残差。

    errors 可选：(对称 u 列表, 不对称 u 列表)，与 points 一一对应。
    """
    if not symmetric and not asymmetric:
        return None
    sym_errors, asym_errors = errors or ([], [])
    figure = Figure(figsize=(10, 6), layout="constrained")
    axes = figure.subplots(2, 2, gridspec_kw={"height_ratios": [3.2, 1.4]})
    panels = (
        (0, symmetric, sym_errors, r"对称：$I$–$d^2$", r"$d^2$ / m$^2$"),
        (1, asymmetric, asym_errors, r"不对称：$I$–($d_1^2+d_2^2$)",
         r"($d_1^2+d_2^2$) / m$^2$"),
    )
    for column, points, errs, title, xlabel in panels:
        _fit_panel(axes[0][column], axes[1][column], points, title, xlabel,
                   r"$I_{\mathrm{total}}$ / kg·m$^2$", errs)
    return figure
