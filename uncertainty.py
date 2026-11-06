"""A/B 类不确定度、传播、有效数字和线性回归。

只做数学，不读取仪器真值。输入全部来自学生在阶段0/1～3 填写的数据。
"""
import math

import numpy as np


def mean(values):
    values = [float(value) for value in values or []]
    return sum(values) / len(values) if values else None


def sample_std(values):
    values = [float(value) for value in values or []]
    if len(values) < 2:
        return 0.0
    average = mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / (len(values) - 1))


def u_a(values):
    values = [float(value) for value in values or []]
    if len(values) < 2:
        return 0.0
    return sample_std(values) / math.sqrt(len(values))


def u_b(resolution):
    try:
        resolution = float(resolution)
    except (TypeError, ValueError):
        return 0.0
    return abs(resolution) / math.sqrt(3) if resolution else 0.0


def combine(*components):
    total = 0.0
    for value in components:
        try:
            total += float(value) ** 2
        except (TypeError, ValueError):
            continue
    return math.sqrt(total)


def relative(value, uncertainty):
    value = float(value)
    if value == 0:
        return float("inf")
    return abs(float(uncertainty) / value)


def readings_summary(values, resolution, label):
    values = [float(value) for value in values or []]
    if not values:
        raise ValueError(f"{label}还没有读数。")
    average = mean(values)
    uncertainty = combine(u_a(values), u_b(resolution))
    return {"mean": average, "u": uncertainty, "count": len(values),
            "u_a": u_a(values), "u_b": u_b(resolution), "values": values}


def times_summary(times, n_periods, timer_resolution):
    """总时间读数 → 平均总时间、周期 T 和 u(T)。"""
    if not times:
        raise ValueError("还没有总时间读数。")
    n_periods = int(n_periods)
    summary = readings_summary(times, timer_resolution, "总时间")
    period = summary["mean"] / n_periods
    period_u = summary["u"] / n_periods
    return {
        "n": n_periods,
        "count": summary["count"],
        "total_mean": summary["mean"],
        "total_u": summary["u"],
        "period": period,
        "period_u": period_u,
        "u_a": summary["u_a"] / n_periods,
        "u_b": summary["u_b"] / n_periods,
    }


def _object_values(params, object_key, field_key, resolution_key, settings):
    objects = (params or {}).get("objects") or {}
    payload = (objects.get(object_key) or {}).get(field_key) or []
    resolution = (params.get("settings") or {}).get(resolution_key, 0)
    summary = readings_summary(payload, resolution, f"{object_key}.{field_key}")
    return summary


def geometry(params, object_key):
    """由阶段0参数计算几何转动惯量；不读取任何真值。"""
    settings = (params or {}).get("settings") or {}
    if object_key == "cylinder":
        mass = _object_values(params, "cylinder", "mass", "balance_resolution_g", settings)
        diameter = _object_values(params, "cylinder", "diameter", "caliper_resolution_mm", settings)
        radius = diameter["mean"] * 1e-3 / 2
        u_radius = diameter["u"] * 1e-3 / 2
        mass_kg = mass["mean"] * 1e-3
        u_mass = mass["u"] * 1e-3
        value = 0.5 * mass_kg * radius ** 2
        uncertainty = value * combine(relative(mass_kg, u_mass), 2 * relative(radius, u_radius))
        return {"value": value, "u": uncertainty, "label": "塑料圆柱",
                "formula": "I₁ = ½mR²"}
    if object_key == "tube":
        mass = _object_values(params, "tube", "mass", "balance_resolution_g", settings)
        outer = _object_values(params, "tube", "outer", "caliper_resolution_mm", settings)
        inner = _object_values(params, "tube", "inner", "caliper_resolution_mm", settings)
        mass_kg = mass["mean"] * 1e-3
        u_mass = mass["u"] * 1e-3
        ro = outer["mean"] * 1e-3 / 2
        ri = inner["mean"] * 1e-3 / 2
        u_ro = outer["u"] * 1e-3 / 2
        u_ri = inner["u"] * 1e-3 / 2
        value = 0.5 * mass_kg * (ro ** 2 + ri ** 2)
        uncertainty = combine(
            0.5 * (ro ** 2 + ri ** 2) * u_mass,
            mass_kg * ro * u_ro,
            mass_kg * ri * u_ri,
        )
        return {"value": value, "u": uncertainty, "label": "金属圆筒",
                "formula": "I = ½m(R外² + R内²)"}
    if object_key == "sphere":
        mass = _object_values(params, "sphere", "mass", "balance_resolution_g", settings)
        diameter = _object_values(params, "sphere", "diameter", "caliper_resolution_mm", settings)
        mass_kg = mass["mean"] * 1e-3
        u_mass = mass["u"] * 1e-3
        radius = diameter["mean"] * 1e-3 / 2
        u_radius = diameter["u"] * 1e-3 / 2
        value = 0.4 * mass_kg * radius ** 2
        uncertainty = value * combine(relative(mass_kg, u_mass), 2 * relative(radius, u_radius))
        return {"value": value, "u": uncertainty, "label": "实心球体",
                "formula": "I = ⅖mR²"}
    if object_key == "rod":
        mass = _object_values(params, "rod", "mass", "balance_resolution_g", settings)
        length = _object_values(params, "rod", "length", "ruler_resolution_mm", settings)
        mass_kg = mass["mean"] * 1e-3
        u_mass = mass["u"] * 1e-3
        length_m = length["mean"] * 1e-3
        u_length = length["u"] * 1e-3
        value = mass_kg * length_m ** 2 / 12
        uncertainty = value * combine(relative(mass_kg, u_mass), 2 * relative(length_m, u_length))
        return {"value": value, "u": uncertainty, "label": "金属细杆",
                "formula": "I = (1/12)mL²"}
    if object_key == "slider":
        mass = _object_values(params, "slider", "mass", "balance_resolution_g", settings)
        diameter = _object_values(params, "slider", "diameter", "caliper_resolution_mm", settings)
        mass_kg = mass["mean"] * 1e-3
        u_mass = mass["u"] * 1e-3
        radius = diameter["mean"] * 1e-3 / 2
        u_radius = diameter["u"] * 1e-3 / 2
        value = 0.5 * mass_kg * radius ** 2
        uncertainty = value * combine(relative(mass_kg, u_mass), 2 * relative(radius, u_radius))
        return {"value": value, "u": uncertainty, "label": "滑块",
                "formula": "I_c = ½mr²"}
    raise ValueError("没有这个物体。")


def calibration(params, t0_times, t1_times, n_periods):
    settings = (params or {}).get("settings") or {}
    timer = settings.get("timer_resolution_s", 0.001)
    t0 = times_summary(t0_times, n_periods, timer)
    t1 = times_summary(t1_times, n_periods, timer)
    if t1["period"] <= t0["period"]:
        raise ValueError("T₁ 应该大于 T₀；先检查两次测量是否装错或读数对调。")
    i1 = geometry(params, "cylinder")
    diff = t1["period"] ** 2 - t0["period"] ** 2
    u_diff = combine(2 * t1["period"] * t1["period_u"],
                     2 * t0["period"] * t0["period_u"])
    k_value = 4 * math.pi ** 2 * i1["value"] / diff
    u_k = k_value * combine(relative(i1["value"], i1["u"]), relative(diff, u_diff))
    i0_value = i1["value"] * t0["period"] ** 2 / diff
    i0_term = 2 * t0["period"] * t0["period_u"]
    u_i0 = i0_value * combine(
        relative(i1["value"], i1["u"]),
        relative(t0["period"] ** 2, i0_term),
        relative(diff, u_diff),
    )
    return {
        "t0": t0, "t1": t1, "i1": i1,
        "diff": diff, "diff_u": u_diff,
        "K": {"value": k_value, "u": u_k},
        "I0": {"value": i0_value, "u": u_i0},
    }


def inertia_from_period(k_value, u_k, period, u_period, i0_value=0.0, u_i0=0.0):
    total = k_value * period ** 2 / (4 * math.pi ** 2)
    u_total = total * combine(relative(k_value, u_k), 2 * relative(period, u_period))
    value = total - i0_value
    uncertainty = combine(u_total, u_i0)
    return {"value": value, "u": uncertainty, "total": total, "u_total": u_total}


def percent_error(experimental, u_experimental, geometric, u_geometric):
    if geometric == 0:
        raise ValueError("几何转动惯量为 0，无法算百分偏差。")
    value = (experimental - geometric) / geometric
    uncertainty = combine(
        u_experimental / abs(geometric),
        abs(experimental) * u_geometric / geometric ** 2,
    )
    return {"value": value, "u": uncertainty}


def regression(x_values, y_values):
    x = np.asarray([float(item) for item in x_values], dtype=float)
    y = np.asarray([float(item) for item in y_values], dtype=float)
    if len(x) < 3 or len(y) != len(x):
        raise ValueError("作直线至少需要 3 个点。")
    design = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - (slope * x + intercept)
    dof = len(x) - 2
    s_yx = math.sqrt(float(np.sum(residual ** 2)) / dof) if dof > 0 else 0.0
    x_mean = float(np.mean(x))
    sxx = float(np.sum((x - x_mean) ** 2))
    if sxx <= 0:
        raise ValueError("横坐标没有变化，无法作直线。")
    u_slope = s_yx / math.sqrt(sxx)
    u_intercept = s_yx * math.sqrt(1.0 / len(x) + x_mean ** 2 / sxx)
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - float(np.sum(residual ** 2)) / ss_tot if ss_tot > 0 else 1.0
    return {"slope": float(slope), "slope_u": u_slope,
            "intercept": float(intercept), "intercept_u": u_intercept,
            "r2": r2, "count": len(x)}


def mean_estimates(values, uncertainties):
    values = [float(value) for value in values or []]
    uncertainties = [float(value) for value in uncertainties or []]
    if not values:
        raise ValueError("没有可平均的估计值。")
    if len(values) != len(uncertainties):
        raise ValueError("估计值和不确定度数量不一致。")
    average = sum(values) / len(values)
    if len(values) == 1:
        uncertainty = uncertainties[0]
    else:
        between = sample_std(values) / math.sqrt(len(values))
        within = math.sqrt(sum(item ** 2 for item in uncertainties)) / len(values)
        uncertainty = combine(between, within)
    return {"value": average, "u": uncertainty, "count": len(values)}


def sig_figs_for(value, uncertainty):
    if uncertainty <= 0:
        text = f"{value:.6g}"
        return text, len(text.replace("-", "").replace(".", "").lstrip("0"))
    exponent = math.floor(math.log10(uncertainty))
    first = uncertainty / 10 ** exponent
    sig = 2 if first < 3 else 1
    decimals = max(0, -exponent + (sig - 1))
    if value != 0 and (abs(value) < 1e-3 or abs(value) >= 1e5):
        text = f"{value:.{sig - 1}e}"
    else:
        text = f"{value:.{decimals}f}"
    return text, sig


def format_result(value, uncertainty, unit="", label=""):
    """返回“值 ± U 单位”和有效数字说明；不确定度取 1～2 位。"""
    if value is None:
        return "—", ""
    if uncertainty is None or uncertainty <= 0:
        return f"{value:.6g} {unit}".strip(), ""
    exponent = math.floor(math.log10(uncertainty))
    first = uncertainty / 10 ** exponent
    sig = 2 if first < 3 else 1
    decimals = max(0, -exponent + (sig - 1))
    u_rounded = round(uncertainty, decimals)
    value_rounded = round(value, decimals)
    if value_rounded != 0 and (abs(value_rounded) < 1e-3 or abs(value_rounded) >= 1e5):
        text = f"{value_rounded:.{sig - 1}e} ± {u_rounded:.{sig - 1}e} {unit}".strip()
    else:
        text = f"{value_rounded:.{decimals}f} ± {u_rounded:.{decimals}f} {unit}".strip()
    return text, f"不确定度取 {sig} 位，结果末位与不确定度对齐"


def check_relative(student, expected, tolerance=0.01):
    try:
        student = float(student)
    except (TypeError, ValueError):
        return False, "没有填数字"
    if expected == 0:
        return abs(student) < tolerance, ""
    difference = abs(student - expected) / abs(expected)
    if difference <= tolerance:
        return True, ""
    return False, f"相对偏差 {difference * 100:.1f}%"


def uncertainty_budget(*parts):
    """把 (名称, 值, 不确定度) 组成文字预算，供页面或 AI 解释。"""
    lines = ["| 量 | 值 | 不确定度 |", "| --- | --- | --- |"]
    for name, value, uncertainty in parts:
        lines.append(f"| {name} | {value:.6g} | {uncertainty:.3g} |")
    return "\n".join(lines)
