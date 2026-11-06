"""扭摆周期测量与核对。工具只返回计时和铭牌，不返回转动惯量或扭转常数。"""
import math
import numpy as np
from matplotlib import rcParams
from matplotlib.figure import Figure

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

# 仪器真值只留在本模块。摘要、知识库和工具返回值都不要写入它们。
K_TRUE = 0.032
CARRIER_I = 4.80e-4
TIMER_RESOLUTION_S = 0.001
AMPLITUDE_DEG = 60.0
# 学生虚拟测量：标准差和限幅都作用在 N 个周期的总时间上，不是单周期。
STUDENT_TOTAL_NOISE_STD_S = 0.010
STUDENT_TOTAL_NOISE_LIMIT_S = 0.030

CYLINDER_MASS_KG = 0.620
CYLINDER_DIAMETER_MM = (99.98, 100.02, 100.00)
CYLINDER_HEIGHT_MM = 50.0
TUBE_MASS_KG = 0.620
TUBE_OUTER_MM = (99.96, 100.04, 100.00)
TUBE_INNER_MM = (89.98, 90.02, 90.00)
TUBE_HEIGHT_MM = 50.0
SPHERE_MASS_KG = 0.550
SPHERE_DIAMETER_MM = (89.96, 90.04, 90.00)
ROD_MASS_KG = 0.168
ROD_LENGTH_MM = 500.0
SLIDER_MASS_KG = 0.240
SLIDER_DIAMETER_MM = 30.0
SLIDER_DISTANCES_CM = (5.0, 10.0, 15.0, 20.0, 25.0)
# 讲义允许的不对称放置。对称放置用 same，两侧距离由 distance_cm 决定。
PLACEMENTS = {
    "same": None,
    "5-10": (5.0, 10.0),
    "10-15": (10.0, 15.0),
    "15-20": (15.0, 20.0),
    "20-25": (20.0, 25.0),
}

ASSEMBLIES = {
    "carrier": "金属载物盘",
    "carrier_cylinder": "载物盘 + 塑料圆柱",
    "carrier_tube": "载物盘 + 金属圆筒",
    "carrier_sphere": "载物盘 + 实心球体",
    "rod": "金属细杆",
    "rod_sliders": "细杆 + 两侧滑块",
}
QUANTITIES = (
    "cylinder_inertia", "tube_inertia", "sphere_inertia", "rod_inertia",
    "sliders_total_inertia", "torsion_constant", "carrier_inertia",
)


def _mean_mm(readings):
    return sum(readings) / len(readings)


def cylinder_radius_m():
    return _mean_mm(CYLINDER_DIAMETER_MM) * 1e-3 / 2


def cylinder_inertia():
    radius = cylinder_radius_m()
    return 0.5 * CYLINDER_MASS_KG * radius * radius


def tube_radii_m():
    return _mean_mm(TUBE_OUTER_MM) * 1e-3 / 2, _mean_mm(TUBE_INNER_MM) * 1e-3 / 2


def tube_inertia():
    outer, inner = tube_radii_m()
    return 0.5 * TUBE_MASS_KG * (outer * outer + inner * inner)


def sphere_radius_m():
    return _mean_mm(SPHERE_DIAMETER_MM) * 1e-3 / 2


def sphere_inertia():
    radius = sphere_radius_m()
    return 0.4 * SPHERE_MASS_KG * radius * radius


def rod_inertia():
    length = ROD_LENGTH_MM * 1e-3
    return ROD_MASS_KG * length * length / 12


def slider_inertia():
    radius = SLIDER_DIAMETER_MM * 1e-3 / 2
    return 0.5 * SLIDER_MASS_KG * radius * radius


def inertia_of(assembly, distance_cm, distance2_cm=None):
    """实验室内部的转动惯量，供测量和核对使用。"""
    if assembly == "carrier":
        return CARRIER_I
    if assembly == "carrier_cylinder":
        return CARRIER_I + cylinder_inertia()
    if assembly == "carrier_tube":
        return CARRIER_I + tube_inertia()
    if assembly == "carrier_sphere":
        return CARRIER_I + sphere_inertia()
    if assembly == "rod":
        return rod_inertia()
    if assembly == "rod_sliders":
        first = float(distance_cm) * 1e-2
        second = first if distance2_cm is None else float(distance2_cm) * 1e-2
        return rod_inertia() + 2 * slider_inertia() + SLIDER_MASS_KG * (first ** 2 + second ** 2)
    raise ValueError("未知的测量对象。")


def _snap_distance(distance_cm):
    distance = float(distance_cm)
    for allowed in SLIDER_DISTANCES_CM:
        if math.isclose(distance, allowed, abs_tol=1e-6):
            return allowed
    raise ValueError("滑块距离 d 只能是 5、10、15、20、25 cm。")


def resolve_distances(assembly, distance_cm, placement="same"):
    """滑块两侧的距离。对称时两个距离相同；不对称时用讲义给出的四组相邻位置。"""
    if assembly != "rod_sliders":
        return None, None
    placement = placement or "same"
    if placement == "same":
        distance = _snap_distance(distance_cm)
        return distance, None
    pair = PLACEMENTS.get(placement)
    if not pair:
        raise ValueError("不对称放置只能是 5 与 10、10 与 15、15 与 20、20 与 25 cm。")
    return pair


def validate_params(assembly, n_periods, distance_cm, placement="same"):
    if assembly not in ASSEMBLIES:
        raise ValueError("对象应为载物盘、塑料圆柱、金属圆筒、实心球体、金属细杆或细杆+两侧滑块。")
    count = float(n_periods)
    if not np.isfinite(count) or abs(count - round(count)) > 1e-9 or not 5 <= round(count) <= 20:
        raise ValueError("周期数 N 应为 5～20 的整数。")
    count = int(round(count))
    first, second = resolve_distances(assembly, distance_cm, placement)
    return assembly, count, first, second


def _geometry(assembly, distance_cm, distance2_cm):
    if assembly == "carrier":
        return {"kind": "carrier", "note": "载物盘的转动惯量未知，不能由外形直接计算。"}
    if assembly == "carrier_cylinder":
        return {
            "kind": "cylinder",
            "cylinder_mass_g": CYLINDER_MASS_KG * 1000,
            "diameter_readings_mm": list(CYLINDER_DIAMETER_MM),
            "height_mm": CYLINDER_HEIGHT_MM,
            "note": "塑料圆柱放在载物盘上，同轴。直径是三次卡尺读数，先取平均。高度不进入绕轴公式。",
        }
    if assembly == "carrier_tube":
        return {
            "kind": "tube",
            "tube_mass_g": TUBE_MASS_KG * 1000,
            "outer_readings_mm": list(TUBE_OUTER_MM),
            "inner_readings_mm": list(TUBE_INNER_MM),
            "height_mm": TUBE_HEIGHT_MM,
            "note": "金属圆筒与塑料圆柱的质量、外径、高度基本相同。绕轴公式用外半径和内半径，高度不进入公式。",
        }
    if assembly == "carrier_sphere":
        return {
            "kind": "sphere",
            "sphere_mass_g": SPHERE_MASS_KG * 1000,
            "diameter_readings_mm": list(SPHERE_DIAMETER_MM),
            "note": "实心球体放在载物盘上，球心在转轴上。直径是三次卡尺读数。",
        }
    rod = {"kind": "rod", "rod_mass_g": ROD_MASS_KG * 1000, "rod_length_mm": ROD_LENGTH_MM,
           "note": "细杆中心与转轴重合。夹具转动惯量忽略。称量时附件已取下。"}
    if assembly == "rod":
        return rod
    symmetric = distance2_cm is None
    return {
        **rod,
        "kind": "sliders",
        "slider_mass_g": SLIDER_MASS_KG * 1000,
        "slider_count": 2,
        "slider_diameter_mm": SLIDER_DIAMETER_MM,
        "distance_cm": distance_cm,
        "distance2_cm": distance2_cm,
        "note": ("两只滑块对称放置。d 是滑块质心到转轴的距离。夹具转动惯量忽略。"
                 if symmetric else
                 "两只滑块不对称。作图时横坐标用 d1²+d2²，不能再把两侧写成同一个 d。夹具转动惯量忽略。"),
    }


def measure_period(assembly, n_periods, distance_cm, noise_std=0.0, placement="same",
                   noise_limit=None, rng=None):
    """返回光电计时和铭牌。

    noise_std 是加在 N 个周期总时间上的标准差，单位秒，不是单周期。
    0 表示不加波动。noise_limit 先把这一次偏移限制在 ±noise_limit 秒，再按 0.001 s 取整。
    直接调用默认不加波动。学生虚拟测量才传入 0.010 s 和 ±0.030 s。
    """
    assembly, count, distance, distance2 = validate_params(
        assembly, n_periods, distance_cm, placement)
    true_period = 2 * math.pi * math.sqrt(
        inertia_of(assembly, distance or 0, distance2) / K_TRUE)
    total = count * true_period
    if noise_std:
        generator = rng if rng is not None else np.random.default_rng()
        offset = float(generator.normal(0.0, float(noise_std)))
        if noise_limit is not None:
            limit = abs(float(noise_limit))
            offset = min(limit, max(-limit, offset))
        total += offset
    total = round(total / TIMER_RESOLUTION_S) * TIMER_RESOLUTION_S
    if total <= 0:
        raise RuntimeError("计时失败，请重新起摆。")
    period = total / count
    time_s = np.linspace(0, 3, 400)
    angle = AMPLITUDE_DEG * np.cos(2 * math.pi * time_s / period)
    summary = {
        "kind": "torsion_timing", "success": True,
        "params": {"assembly": assembly, "n_periods": count, "distance_cm": distance,
                   "distance2_cm": distance2, "placement": placement if assembly == "rod_sliders" else "same"},
        "assembly_name": ASSEMBLIES[assembly],
        "n_periods": count, "total_time_s": float(total), "period_s": float(period),
        "timer_resolution_s": TIMER_RESOLUTION_S, "amplitude_deg": AMPLITUDE_DEG,
        "geometry": _geometry(assembly, distance, distance2),
    }
    return dict(summary=summary, time_s=time_s, angle_deg=angle)


def with_repeats(summary, earlier):
    """附上同一次会话里相同条件的周期，供学生看重复，不计算转动惯量。"""
    params = summary["params"]
    key = (params["assembly"], params["distance_cm"], params.get("distance2_cm"))
    periods = [item["period_s"] for item in earlier
               if (item["params"]["assembly"], item["params"]["distance_cm"],
                   item["params"].get("distance2_cm")) == key]
    periods.append(summary["period_s"])
    annotated = dict(summary)
    annotated["repeat_count"] = len(periods)
    annotated["repeated_periods_s"] = [float(value) for value in periods]
    annotated["period_sample_std_s"] = (
        float(np.std(periods, ddof=1)) if len(periods) >= 2 else None)
    return annotated


def _mean_period(trials, assembly, distance_cm=None):
    found = []
    for item in trials:
        params = item["params"]
        if params["assembly"] != assembly:
            continue
        if distance_cm is not None and not math.isclose(
                float(params["distance_cm"]), float(distance_cm), abs_tol=1e-6):
            continue
        found.append(item["period_s"])
    if not found:
        return None
    return float(np.mean(found))


def _relative(value, reference):
    return abs(value - reference) / abs(reference)


def nameplate_instrument():
    """页面公开铭牌，给已确认「与铭牌相同」的实验室核对用。不含扭转常数真值。"""
    return {
        "cylinder_mass_kg": CYLINDER_MASS_KG,
        "cylinder_diameter_mm": tuple(CYLINDER_DIAMETER_MM),
        "tube_mass_kg": TUBE_MASS_KG,
        "tube_outer_mm": tuple(TUBE_OUTER_MM),
        "tube_inner_mm": tuple(TUBE_INNER_MM),
        "sphere_mass_kg": SPHERE_MASS_KG,
        "sphere_diameter_mm": tuple(SPHERE_DIAMETER_MM),
        "rod_mass_kg": ROD_MASS_KG,
        "rod_length_mm": ROD_LENGTH_MM,
        "slider_mass_kg": SLIDER_MASS_KG,
        "slider_diameter_mm": SLIDER_DIAMETER_MM,
    }


def _need_spec(spec, key, label):
    value = None if spec is None else spec.get(key)
    if value is None or value == ():
        raise ValueError(f"还缺{label}。周期可以先留着，这次不作数值核对，也不会改用虚拟铭牌。")
    return value


def _radius_from_diameters(diameters_mm):
    if isinstance(diameters_mm, (int, float)):
        return float(diameters_mm) * 1e-3 / 2
    return _mean_mm(diameters_mm) * 1e-3 / 2


def _targets(quantity, spec, distance_cm, trials, placement):
    """由一份器材参数和给定周期得到对照值。对照值不返回给页面。"""
    if quantity == "cylinder_inertia":
        mass = _need_spec(spec, "cylinder_mass_kg", "塑料圆柱质量")
        radius = _radius_from_diameters(_need_spec(spec, "cylinder_diameter_mm", "塑料圆柱直径"))
        true = 0.5 * mass * radius ** 2
        wrongs = {
            "diameter_used_as_radius": 0.5 * mass * (2 * radius) ** 2,
            "missing_one_half": mass * radius ** 2,
        }
    elif quantity == "tube_inertia":
        mass = _need_spec(spec, "tube_mass_kg", "金属圆筒质量")
        outer = _radius_from_diameters(_need_spec(spec, "tube_outer_mm", "金属圆筒外径"))
        inner = _radius_from_diameters(_need_spec(spec, "tube_inner_mm", "金属圆筒内径"))
        true = 0.5 * mass * (outer ** 2 + inner ** 2)
        wrongs = {
            "tube_used_outer_only": 0.5 * mass * outer ** 2,
            "tube_missing_one_half": mass * (outer ** 2 + inner ** 2),
            "diameter_used_as_radius": 0.5 * mass * ((2 * outer) ** 2 + (2 * inner) ** 2),
        }
    elif quantity == "sphere_inertia":
        mass = _need_spec(spec, "sphere_mass_kg", "实心球体质量")
        radius = _radius_from_diameters(_need_spec(spec, "sphere_diameter_mm", "实心球体直径"))
        true = 0.4 * mass * radius ** 2
        wrongs = {
            "sphere_used_cylinder_half": 0.5 * mass * radius ** 2,
            "sphere_missing_two_fifths": mass * radius ** 2,
            "diameter_used_as_radius": 0.4 * mass * (2 * radius) ** 2,
        }
    elif quantity == "rod_inertia":
        mass = _need_spec(spec, "rod_mass_kg", "金属细杆质量")
        length_mm = _need_spec(spec, "rod_length_mm", "金属细杆长度")
        length = float(length_mm) * 1e-3
        true = mass * length ** 2 / 12
        wrongs = {
            "missing_one_twelfth": mass * length ** 2,
            "length_left_in_mm": mass * float(length_mm) ** 2 / 12,
        }
    elif quantity == "sliders_total_inertia":
        mass = _need_spec(spec, "rod_mass_kg", "金属细杆质量")
        length = float(_need_spec(spec, "rod_length_mm", "金属细杆长度")) * 1e-3
        slider_mass = _need_spec(spec, "slider_mass_kg", "滑块质量")
        slider_radius = float(_need_spec(spec, "slider_diameter_mm", "滑块直径")) * 1e-3 / 2
        rod_i = mass * length ** 2 / 12
        slider_i = 0.5 * slider_mass * slider_radius ** 2
        first, second = resolve_distances("rod_sliders", distance_cm, placement)
        d1 = first * 1e-2
        d2 = d1 if second is None else second * 1e-2
        true = rod_i + 2 * slider_i + slider_mass * (d1 ** 2 + d2 ** 2)
        wrongs = {
            "forgot_the_factor_two": rod_i + slider_i + slider_mass * d1 ** 2,
            "used_d_not_d_squared": rod_i + 2 * slider_i + slider_mass * (d1 + d2),
            "forgot_rod": 2 * slider_i + slider_mass * (d1 ** 2 + d2 ** 2),
        }
        if second is not None:
            farther = max(d1, d2)
            wrongs["used_same_distance"] = rod_i + 2 * slider_i + 2 * slider_mass * farther ** 2
    else:
        empty = _mean_period(trials, "carrier")
        loaded = _mean_period(trials, "carrier_cylinder")
        if empty is None or loaded is None:
            raise ValueError("请先分别测量金属载物盘和载物盘+塑料圆柱。")
        gap = loaded ** 2 - empty ** 2
        if gap <= 0:
            raise ValueError("两次周期的平方差不是正数，请核对哪一次是空盘。")
        mass = _need_spec(spec, "cylinder_mass_kg", "塑料圆柱质量")
        radius = _radius_from_diameters(_need_spec(spec, "cylinder_diameter_mm", "塑料圆柱直径"))
        cylinder_i = 0.5 * mass * radius ** 2
        if quantity == "torsion_constant":
            true = 4 * math.pi ** 2 * cylinder_i / gap
            wrongs = {
                "used_period_not_period_squared": 4 * math.pi ** 2 * cylinder_i / (loaded - empty),
                "forgot_empty_plate": 4 * math.pi ** 2 * cylinder_i / loaded ** 2,
            }
        else:
            true = cylinder_i * empty ** 2 / gap
            wrongs = {
                "used_period_not_period_squared": cylinder_i * empty / (loaded - empty),
                "reported_total_instead_of_carrier": cylinder_i * loaded ** 2 / gap,
            }
    return true, wrongs


def assess_student_value(quantity, value, distance_cm, trials, placement="same", instrument=None):
    """核对已提交的数字。相符或指出常见错误，不返回标准值。

    instrument 为空时用页面铭牌。实验室传入学生保存的参数，缺项由 _need_spec 说明。
    """
    if quantity not in QUANTITIES:
        raise ValueError("可核对圆柱、金属圆筒、实心球体、细杆、滑块系统的转动惯量，以及扭转常数和载物盘转动惯量。")
    value = float(value)
    if not np.isfinite(value):
        raise ValueError("请给出有限数值。")
    true, wrongs = _targets(
        quantity, nameplate_instrument() if instrument is None else instrument,
        distance_cm, trials, placement)
    messages = {
        "diameter_used_as_radius": "这个数更接近把直径当成了半径。",
        "missing_one_half": "这个数更接近漏掉了圆柱公式里的 1/2。",
        "missing_one_twelfth": "这个数更接近漏掉了细杆公式里的 1/12。",
        "length_left_in_mm": "这个数更接近长度仍用毫米，没有换成米。",
        "forgot_the_factor_two": "这个数更接近只算了一侧滑块。",
        "used_d_not_d_squared": "这个数更接近用了 d，而不是 d 的平方。",
        "forgot_rod": "这个数更接近没有加上细杆本身。",
        "used_same_distance": "这个数更接近把两侧都放在较远的那个距离上。",
        "tube_used_outer_only": "这个数更接近只使用了外半径，把圆筒当成了实心圆柱。",
        "tube_missing_one_half": "这个数更接近漏掉了圆筒公式里的 1/2。",
        "sphere_used_cylinder_half": "这个数更接近用了圆柱的 1/2，而球体是 2/5。",
        "sphere_missing_two_fifths": "这个数更接近漏掉了球体公式里的 2/5。",
        "used_period_not_period_squared": "这个数更接近用了周期本身，而不是周期的平方。",
        "forgot_empty_plate": "这个数更接近没有用空盘和加圆柱两次周期的平方差。",
        "reported_total_instead_of_carrier": "这个数更接近载物盘加圆柱的总转动惯量。",
    }
    if _relative(value, true) <= 0.02:
        note = "与当前原始读数和公式相符（相对差在 2% 以内）。"
    elif 1e6 <= abs(value / true) <= 1e8:
        note = "这个数更接近还停在 g·cm²，没有换成 kg·m²。"
    else:
        nearest = min(wrongs, key=lambda name: _relative(value, wrongs[name]), default=None)
        if nearest is not None and _relative(value, wrongs[nearest]) <= 0.08:
            note = messages[nearest]
        else:
            note = "与按原始读数和公式得到的结果不一致。请检查单位、平方和是否加了两侧。"
    return {"success": True, "consistent": _relative(value, true) <= 0.02,
            "quantity": quantity, "note": note + "程序不提供标准数值。"}


def _readings(values):
    return "、".join(f"{value:.2f}" for value in values)


def geometry_text(summary):
    geometry = summary["geometry"]
    kind = geometry.get("kind")
    if kind == "cylinder" or (kind is None and "cylinder_mass_g" in geometry):
        height = geometry.get("height_mm")
        height_text = "" if height is None else f"，高度 {height:.1f} mm"
        return (f"塑料圆柱质量 {geometry['cylinder_mass_g']:.1f} g，"
                f"直径三次读数 {_readings(geometry['diameter_readings_mm'])} mm{height_text}。")
    if kind == "tube":
        return (f"金属圆筒质量 {geometry['tube_mass_g']:.1f} g，"
                f"外径三次读数 {_readings(geometry['outer_readings_mm'])} mm，"
                f"内径三次读数 {_readings(geometry['inner_readings_mm'])} mm，"
                f"高度 {geometry['height_mm']:.1f} mm。")
    if kind == "sphere":
        return (f"实心球体质量 {geometry['sphere_mass_g']:.1f} g，"
                f"直径三次读数 {_readings(geometry['diameter_readings_mm'])} mm。")
    if kind == "sliders" or (kind is None and "slider_mass_g" in geometry):
        return (f"细杆 {geometry['rod_mass_g']:.1f} g、长 {geometry['rod_length_mm']:.1f} mm；"
                f"滑块两只，每只 {geometry['slider_mass_g']:.1f} g，直径 {geometry['slider_diameter_mm']:.2f} mm。")
    if kind == "rod" or (kind is None and "rod_mass_g" in geometry):
        return f"细杆质量 {geometry['rod_mass_g']:.1f} g，长度 {geometry['rod_length_mm']:.1f} mm。"
    return geometry["note"]


def _repeat_line(summary):
    count = summary.get("repeat_count", 1)
    if count < 2:
        return ""
    periods = summary.get("repeated_periods_s") or [summary["period_s"]]
    same = all(math.isclose(value, periods[0], abs_tol=1e-12) for value in periods)
    if summary.get("origin") == "lab":
        if same:
            return f"\n同一条件已录入 {count} 次，这几次周期相同。计算只用尚未被更正的记录。"
        return f"\n同一条件已录入 {count} 次。可以自己求平均和 A 类不确定度。"
    if same:
        return (f"\n同一条件已测 {count} 次，这几次读数相同。"
                "各次都保留着。虚拟计时有小幅起伏，不保证每次都不同。")
    std = summary.get("period_sample_std_s")
    std_text = f"样本标准差 {std:.4f} s。" if std else ""
    return (f"\n同一条件已测 {count} 次，各次总时间和周期都保留。{std_text}"
            "可以自己求平均和 A 类不确定度。")


def _total_phrase(summary):
    if summary.get("total_time_s") is None:
        return "总时间未录入"
    if summary.get("origin") == "lab" and summary.get("total_time_text"):
        return f"总时间 {summary['total_time_text']} s"
    return f"总时间 {summary['total_time_s']:.3f} s"


def _period_phrase(summary):
    if summary.get("origin") == "lab" and summary.get("period_text"):
        return f"{summary['period_text']}"
    if summary.get("origin") == "lab":
        text = f"{summary['period_s']:.8f}".rstrip("0").rstrip(".")
        return text
    return f"{summary['period_s']:.4f}"


def _position_text(params):
    first = params.get("distance_cm")
    if first is None:
        return ""
    second = params.get("distance2_cm")
    if second is None:
        return f"，d={first:g} cm"
    return f"，d1={first:g} cm，d2={second:g} cm"


def _position_label(params):
    text = _position_text(params)
    return "—" if not text else text[1:]


def result_text(result):
    if result is None:
        return "还没有测量。"
    summary = result["summary"]
    params = summary["params"]
    closing = ("这是录入的周期，不是虚拟仪器生成的读数。程序不直接给出转动惯量和扭转常数。"
               if summary.get("origin") == "lab"
               else "仪器不直接给出转动惯量和扭转常数。")
    return (f"对象：{summary['assembly_name']}{_position_text(params)}\n"
            f"N={summary['n_periods']}，{_total_phrase(summary)}，"
            f"周期 T={_period_phrase(summary)} s\n"
            f"{geometry_text(summary)}{_repeat_line(summary)}\n"
            f"{closing}")


def result_details(result):
    if result is None:
        return "尚无实验记录。"
    summary = result["summary"]
    if summary.get("origin") == "lab":
        return (f"记录：{summary.get('measurement_id', '')} ｜ 实验室录入\n"
                f"{_total_phrase(summary)}，周期 T={_period_phrase(summary)} s。"
                f"{_repeat_line(summary)}\n"
                "由录入周期只能作示意，不是实测角度曲线。\n"
                f"{summary['geometry']['note']}")
    source = "AI 工具调用" if summary.get("source") == "agent" else "按钮测量"
    periods = summary.get("repeated_periods_s") or [summary["period_s"]]
    listed = "、".join(f"{value:.4f}" for value in periods)
    return (f"实验编号：{summary['experiment_id']} ｜ {source}\n"
            f"摆角 {summary['amplitude_deg']:.0f}°，按简谐模型由测得周期还原曲线。\n"
            f"计时分辨率 {summary['timer_resolution_s']} s。"
            f"同条件各次周期：{listed} s。{_repeat_line(summary)}\n"
            f"{summary['geometry']['note']}")


def _summary_of(item):
    if item is None:
        return None
    if "summary" in item and isinstance(item["summary"], dict) and "period_s" in item["summary"]:
        return item["summary"]
    return item


def _curve_label(summary):
    return f"{summary['assembly_name']}{_position_text(summary['params'])}  T={summary['period_s']:.4f} s"


def comparison_summary(latest, notebook):
    """选一条用来对照的已测摘要：成对对象优先，其次才是另一个滑块距离。"""
    summary = _summary_of(latest)
    if summary is None or not notebook:
        return None
    assembly = summary["params"]["assembly"]
    own_id = summary.get("experiment_id")
    others = []
    for item in notebook:
        if item is summary:
            continue
        if own_id is not None and item.get("experiment_id") == own_id:
            continue
        others.append(item)

    def last_where(predicate):
        found = [item for item in others if predicate(item)]
        return found[-1] if found else None

    if assembly in ("carrier", "carrier_cylinder", "carrier_tube", "carrier_sphere"):
        order = {
            "carrier": ("carrier_cylinder", "carrier_tube", "carrier_sphere"),
            "carrier_cylinder": ("carrier_tube", "carrier", "carrier_sphere"),
            "carrier_tube": ("carrier_cylinder", "carrier"),
            "carrier_sphere": ("carrier", "carrier_cylinder"),
        }[assembly]
        for name in order:
            found = last_where(lambda item, name=name: item["params"]["assembly"] == name)
            if found is not None:
                return found
        return None
    if assembly == "rod":
        return last_where(lambda item: item["params"]["assembly"] == "rod_sliders")
    bare = last_where(lambda item: item["params"]["assembly"] == "rod")
    if bare is not None:
        return bare
    distance = summary["params"]["distance_cm"]
    return last_where(
        lambda item: item["params"]["assembly"] == "rod_sliders"
        and not math.isclose(float(item["params"]["distance_cm"]), float(distance), abs_tol=1e-6))


def plot_swing(result, previous=None):
    """用测得周期还原角位移。时间窗盖住较慢一条的两个周期，图例写出对象和周期。"""
    current = _summary_of(result)
    if current is None:
        return None
    reference = _summary_of(previous)
    slower = current["period_s"]
    if reference is not None:
        slower = max(slower, reference["period_s"])
    window = min(16.0, max(3.0, 2 * slower))
    time_s = np.linspace(0, window, 500)
    figure = Figure(figsize=(9, 3.6), layout="constrained")
    axis = figure.subplots()

    def angle(period):
        return AMPLITUDE_DEG * np.cos(2 * math.pi * time_s / period)

    axis.plot(time_s, angle(current["period_s"]), label=_curve_label(current))
    if reference is not None:
        axis.plot(time_s, angle(reference["period_s"]), "--", label=_curve_label(reference))
    title = ("由录入周期绘出的示意，不是实测角度曲线"
             if current.get("origin") == "lab"
             else "按测得周期还原的摆动，用来比较快慢")
    axis.set(xlabel="时间 / s", ylabel="角位移 / °", title=title)
    axis.set_xlim(0, window)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)
    figure.suptitle(f"{current['assembly_name']}{_position_text(current['params'])} ｜ "
                    f"T={current['period_s']:.4f} s ｜ N={current['n_periods']}", fontsize=10)
    return figure


def plot_swing_many(summaries, title=None):
    """把学生选出的 1～4 条记录按各自周期还原成摆动，只比较快慢。"""
    chosen = []
    for item in summaries or []:
        summary = _summary_of(item)
        if summary is not None and summary.get("period_s"):
            chosen.append(summary)
    if not chosen:
        return None
    chosen = chosen[:4]
    slower = max(item["period_s"] for item in chosen)
    window = min(16.0, max(3.0, 2 * slower))
    time_s = np.linspace(0, window, 600)
    figure = Figure(figsize=(9, 3.8), layout="constrained")
    axis = figure.subplots()
    styles = ("-", "--", "-.", ":")
    for index, summary in enumerate(chosen):
        angle = AMPLITUDE_DEG * np.cos(2 * math.pi * time_s / summary["period_s"])
        axis.plot(time_s, angle, styles[index % len(styles)], label=_curve_label(summary))
    lab = any(item.get("origin") == "lab" for item in chosen)
    axis.set(
        xlabel="时间 / s", ylabel="角位移 / °",
        title=title or ("由录入周期绘出的示意，不是实测角度曲线" if lab
                        else "选出的记录按各自周期还原的摆动，用来比较快慢"))
    axis.set_xlim(0, window)
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)
    figure.suptitle(f"共 {len(chosen)} 条记录 ｜ 摆角 {AMPLITUDE_DEG:.0f}°", fontsize=10)
    return figure


def _table_total(summary):
    if summary.get("total_time_text"):
        return summary["total_time_text"]
    if summary.get("total_time_s") is None:
        return "—"
    if summary.get("origin") == "lab":
        return f"{summary['total_time_s']:.8f}".rstrip("0").rstrip(".")
    return f"{summary['total_time_s']:.3f}"


def _table_period(summary):
    if summary.get("period_text"):
        return summary["period_text"]
    if summary.get("origin") == "lab":
        return f"{summary['period_s']:.8f}".rstrip("0").rstrip(".")
    return f"{summary['period_s']:.4f}"


def data_table(summaries):
    """原始记录，供实验报告誊抄。不计算转动惯量。"""
    if not summaries:
        return "尚无原始记录。测完后，这里列出对象、位置、周期数、总时间和周期。"
    show_origin = any(item.get("origin") for item in summaries)
    if show_origin:
        lines = [
            "| 次序 | 来源 | 对象 | 位置 | N | 总时间 / s | 周期 T / s |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    else:
        lines = [
            "| 次序 | 对象 | 位置 | N | 总时间 / s | 周期 T / s |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    for index, summary in enumerate(summaries, start=1):
        params = summary["params"]
        name = summary["assembly_name"]
        if summary.get("superseded"):
            name += "（已更正）"
        origin = "实验室录入" if summary.get("origin") == "lab" else "虚拟"
        cells = [str(index)]
        if show_origin:
            cells.append(origin)
        cells.extend([
            name, _position_label(params), str(summary["n_periods"]),
            _table_total(summary), _table_period(summary),
        ])
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def plot_distance_trend(summaries):
    """只标出对称放置时已经测到的周期，不连线、不拟合、不换算转动惯量。"""
    if not summaries:
        return None
    grouped = {}
    for summary in summaries:
        params = summary["params"]
        if params.get("assembly") not in (None, "rod_sliders"):
            continue
        if params.get("distance2_cm") is not None:
            continue
        distance = params.get("distance_cm")
        if distance is None:
            continue
        grouped.setdefault(distance, []).append(summary["period_s"])
    if not grouped:
        return None
    distances = sorted(grouped)
    periods = [float(np.mean(grouped[distance])) for distance in distances]
    figure = Figure(figsize=(9, 3.6), layout="constrained")
    axis = figure.subplots()
    axis.plot(distances, periods, "o", linestyle="None")
    # 从 0 起标，避免只测一个距离时纵轴被放大成一条细带。
    axis.set_ylim(0, max(periods) * 1.35)
    for distance, period in zip(distances, periods):
        axis.annotate(f"{period:.4f}", (distance, period), textcoords="offset points",
                      xytext=(0, 7), ha="center", fontsize=8)
    axis.set(xlabel="滑块距离 d / cm", ylabel="周期 T / s",
             title="对称放置时各距离上已测到的周期（只标点，没有拟合线）",
             xticks=list(SLIDER_DISTANCES_CM))
    axis.set_xlim(0, 30)
    axis.grid(alpha=0.25)
    return figure
