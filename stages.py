"""阶段1～3 的测量组、计算估计、学生结果检查和问题目录。"""
from uuid import uuid4

import experiment
import uncertainty

SHAPE_CONDITIONS = ("tube", "sphere", "rod")
SHAPE_LABELS = {"tube": "金属圆筒", "sphere": "实心球体", "rod": "金属细杆"}
SHAPE_GEOMETRY_KEY = {"tube": "tube", "sphere": "sphere", "rod": "rod"}

SYMMETRIC_DISTANCES = (5.0, 10.0, 15.0, 20.0, 25.0)
ASYMMETRIC_PAIRS = ((5.0, 10.0), (10.0, 15.0), (15.0, 20.0), (20.0, 25.0))


def parallel_conditions():
    items = [("rod", "金属细杆（基准）")]
    for distance in SYMMETRIC_DISTANCES:
        items.append((f"sym-{distance:g}", f"对称 d = {distance:g} cm"))
    for first, second in ASYMMETRIC_PAIRS:
        items.append((f"asym-{first:g}-{second:g}",
                      f"不对称 {first:g} / {second:g} cm"))
    return items


PARALLEL_CONDITIONS = dict(parallel_conditions())
PARALLEL_LABELS = {key: label for key, label in parallel_conditions()}

QUESTIONS = {
    "shapes": (
        ("q1", "圆筒和塑料圆柱的质量、外径接近，为什么转动惯量仍可能差很多？"),
        ("q2", "哪些物体要减载物盘的 I₀，哪些不要？为什么？"),
        ("q3", "球体的几何转动惯量为什么用 2/5，而不是 1/2？"),
    ),
    "parallel": (
        ("q1", "对称放置时，I–d² 图的斜率和截距各对应什么？"),
        ("q2", "两侧距离不同时，横坐标为什么用 d₁²+d₂²？斜率对应什么？"),
        ("q3", "细杆单独测量的点为什么不能当成 d = 0 的滑块点？"),
    ),
}


def blank_stage_data():
    return {
        "calibrate": {
            "groups": [],
            "results": {"I1": "", "K": "", "I0": ""},
            "checks": [],
            "answers": {},
            "answers_feedback": "",
            "last_check_md": "",
            "last_check": None,
        },
        "shapes": {
            "groups": [],
            "results": {key: {"Iexp": "", "Igeo": "", "E": ""} for key in SHAPE_CONDITIONS},
            "checks": [],
            "answers": {},
            "answers_feedback": "",
            "last_check_md": "",
            "last_check": None,
        },
        "parallel": {
            "groups": [],
            "results": {
                "I_total": {key: "" for key, _label in parallel_conditions()},
                "slope_sym": "", "intercept_sym": "",
                "slope_asym": "", "intercept_asym": "",
            },
            "checks": [],
            "answers": {},
            "answers_feedback": "",
            "last_check_md": "",
            "last_check": None,
        },
        "summary": {"charts": False, "text": ""},
    }


def ensure_stages(state, mode):
    payload = state.setdefault(mode, {})
    stages = payload.get("stages")
    if not isinstance(stages, dict):
        stages = blank_stage_data()
        payload["stages"] = stages
    defaults = blank_stage_data()
    for key, value in defaults.items():
        stages.setdefault(key, value)
        if isinstance(value, dict):
            for field, default in value.items():
                stages[key].setdefault(field, default)
    for key in SHAPE_CONDITIONS:
        stages["shapes"]["results"].setdefault(key, {"Iexp": "", "Igeo": "", "E": ""})
    for key, _label in parallel_conditions():
        stages["parallel"]["results"]["I_total"].setdefault(key, "")
    for field in ("slope_sym", "intercept_sym", "slope_asym", "intercept_asym"):
        stages["parallel"]["results"].setdefault(field, "")
    for key in ("calibrate", "shapes", "parallel"):
        stages[key].setdefault("last_check_md", "")
        stages[key].setdefault("last_check", None)
        stages[key].setdefault("answers_feedback", "")
    stages["summary"].setdefault("text", "")
    return stages


def stage(state, mode, key):
    return ensure_stages(state, mode)[key]


def _clean_note(note):
    return str(note or "").strip()[:300]


def add_calibration_group(state, mode, n_periods, t0_text, t1_text, note=""):
    t0 = experiment.parse_readings(t0_text, "空盘总时间")
    t1 = experiment.parse_readings(t1_text, "加圆柱总时间")
    if not t0:
        raise ValueError("空盘总时间至少要填一个读数。")
    if not t1:
        raise ValueError("加圆柱总时间至少要填一个读数。")
    active = experiment.active_param(state, mode) or {}
    group = {
        "id": "cal_" + uuid4().hex[:8],
        "n_periods": int(n_periods),
        "t0": t0,
        "t1": t1,
        "note": _clean_note(note),
        "param_id": active.get("id"),
        "param_label": active.get("label"),
        "created_at": experiment.now(),
    }
    stage(state, mode, "calibrate")["groups"].append(group)
    return group


def add_measurement_group(state, mode, stage_key, condition, n_periods, times_text, note=""):
    if stage_key not in ("shapes", "parallel"):
        raise ValueError("这个阶段没有测量组。")
    if stage_key == "shapes" and condition not in SHAPE_CONDITIONS:
        raise ValueError("没有这个规则刚体。")
    if stage_key == "parallel" and condition not in PARALLEL_CONDITIONS:
        raise ValueError("没有这个平行轴条件。")
    times = experiment.parse_readings(times_text, "总时间")
    if not times:
        raise ValueError("总时间至少要填一个读数。")
    active = experiment.active_param(state, mode) or {}
    group = {
        "id": "g_" + uuid4().hex[:8],
        "stage": stage_key,
        "condition": condition,
        "n_periods": int(n_periods),
        "times": times,
        "note": _clean_note(note),
        "param_id": active.get("id"),
        "param_label": active.get("label"),
        "created_at": experiment.now(),
    }
    stage(state, mode, stage_key)["groups"].append(group)
    return group


def groups_for(state, mode, stage_key, condition=None):
    items = stage(state, mode, stage_key).get("groups") or []
    if condition is None:
        return list(items)
    return [item for item in items if item.get("condition") == condition]


def active_groups_for(state, mode, stage_key, condition=None):
    return [item for item in groups_for(state, mode, stage_key, condition)
            if not item.get("superseded")]


def void_last_group(state, mode, stage_key, condition=None):
    items = [item for item in groups_for(state, mode, stage_key, condition)
             if not item.get("superseded")]
    if not items:
        raise ValueError("没有可作废的测量组。")
    target = items[-1]
    target["superseded"] = True
    return target


def void_group(state, mode, stage_key, group_id):
    for item in groups_for(state, mode, stage_key):
        if item.get("id") == group_id:
            if item.get("superseded"):
                raise ValueError("这一组已经作废。")
            item["superseded"] = True
            return item
    raise ValueError("没有这个测量组。")


def _fmt_total(times):
    """一组总时间的显示文本；多读数时标出次数，数值保留到 0.001 s。"""
    values = [float(value) for value in (times or [])]
    if not values:
        return "—"
    text = f"{sum(values) / len(values):.3f}"
    return text if len(values) == 1 else f"{text}（{len(values)} 次）"


def _fmt_period(times, n_periods):
    """由一组总时间求周期 T，保留 4 位小数；只做除法，不算不确定度。"""
    values = [float(value) for value in (times or [])]
    if not values or not n_periods:
        return "—"
    return f"{sum(values) / len(values) / int(n_periods):.4f}"


def group_choices(state, mode, stage_key, condition=None):
    items = groups_for(state, mode, stage_key, condition)
    choices = []
    for index, item in enumerate(items, start=1):
        if stage_key == "calibrate":
            label = (f"第 {index} 组 · N={item['n_periods']} · "
                     f"T₀={_fmt_period(item['t0'], item['n_periods'])} · "
                     f"T₁={_fmt_period(item['t1'], item['n_periods'])} s")
        else:
            labels = SHAPE_LABELS if stage_key == "shapes" else PARALLEL_LABELS
            label = (f"第 {index} 组 · {labels.get(item.get('condition'), item.get('condition'))} · "
                     f"N={item['n_periods']} · {len(item['times'])}次 · "
                     f"T={_fmt_period(item['times'], item['n_periods'])} s")
        if item.get("superseded"):
            label += "（已作废）"
        choices.append((label, item["id"]))
    return choices


def param_change_note(state, mode):
    """切换当前参数版本后，说明阶段1～3 会用新版本统一重算。"""
    groups = [group for key in ("calibrate", "shapes", "parallel")
              for group in groups_for(state, mode, key) if not group.get("superseded")]
    if not groups:
        return ""
    active = experiment.active_param(state, mode) or {}
    stale = [group for group in groups if group.get("param_id") != active.get("id")]
    if not stale:
        return ""
    labels = []
    for group in stale:
        label = group.get("param_label") or "未记录版本"
        if label not in labels:
            labels.append(label)
    return (f"\n注意：阶段1～3 已有 {len(stale)} 组是在 {'、'.join(labels)} 下测的，"
            f"现在会统一按「{active.get('label') or '当前版本'}」重算；"
            "之前算出的 K、I₀ 和几何值可能对不上。")


def _group_period(group, settings):
    timer = (settings or {}).get("timer_resolution_s", 0.001)
    return uncertainty.times_summary(group["times"], group["n_periods"], timer)


def _combine_groups(groups, settings):
    estimates = [_group_period(group, settings) for group in groups]
    periods = [item["period"] for item in estimates]
    uncertainties = [item["period_u"] for item in estimates]
    combined = uncertainty.mean_estimates(periods, uncertainties)
    return {
        "T": combined["value"], "u_T": combined["u"], "count": combined["count"],
        "groups": estimates,
    }


def calibration_estimate(state, mode, params):
    groups = active_groups_for(state, mode, "calibrate")
    if not groups:
        raise ValueError("阶段1 还没有标定组。")
    settings = (params or {}).get("settings") or {}
    timer = settings.get("timer_resolution_s", 0.001)
    estimates = []
    for index, group in enumerate(groups, start=1):
        try:
            result = uncertainty.calibration(params, group["t0"], group["t1"], group["n_periods"])
        except ValueError as exc:
            raise ValueError(f"标定第 {index} 组：{exc}")
        estimates.append(result)
    k_values = [item["K"]["value"] for item in estimates]
    k_uncertainties = [item["K"]["u"] for item in estimates]
    i0_values = [item["I0"]["value"] for item in estimates]
    i0_uncertainties = [item["I0"]["u"] for item in estimates]
    k = uncertainty.mean_estimates(k_values, k_uncertainties)
    i0 = uncertainty.mean_estimates(i0_values, i0_uncertainties)
    t0 = uncertainty.mean_estimates(
        [item["t0"]["period"] for item in estimates],
        [item["t0"]["period_u"] for item in estimates])
    t1 = uncertainty.mean_estimates(
        [item["t1"]["period"] for item in estimates],
        [item["t1"]["period_u"] for item in estimates])
    return {
        "K": k, "I0": i0, "I1": estimates[-1]["i1"],
        "T0": t0, "T1": t1, "groups": len(groups),
        "raw": estimates,
    }


def _a_type_note(groups):
    return "（只有 1 组，A 类未估计）" if groups == 1 else ""


def calibration_preview(state, mode, params):
    estimate = calibration_estimate(state, mode, params)
    t0_text, _ = uncertainty.format_result(estimate["T0"]["value"], estimate["T0"]["u"], "s")
    t1_text, _ = uncertainty.format_result(estimate["T1"]["value"], estimate["T1"]["u"], "s")
    lines = [f"标定组：{estimate['groups']} 组", ""]
    if estimate["groups"] < 3:
        lines.extend([
            f"现在只有 {estimate['groups']} 组，A 类不确定度还没有估计（单组时为 0），"
            "上面的 ± 只含计时误差；建议凑到 3 组以上再下结论。",
            "",
        ])
    lines.extend([
        f"- T₀ = {t0_text}",
        f"- T₁ = {t1_text}",
        "",
        "由阶段0 的圆柱质量和直径算 I₁；由 T₀、T₁ 算 K 和 I₀。",
        "± 后是合成标准不确定度 u_c（k=1）。这里只显示 T₀、T₁；I₁、K、I₀ 请你自己算，再填到下面。",
    ])
    return "\n".join(lines)


def shape_estimate(state, mode, condition, params):
    groups = active_groups_for(state, mode, "shapes", condition)
    if not groups:
        raise ValueError(f"{SHAPE_LABELS[condition]}还没有测量组。")
    settings = (params or {}).get("settings") or {}
    combined = _combine_groups(groups, settings)
    calibration = calibration_estimate(state, mode, params)
    if condition in ("tube", "sphere"):
        inertia = uncertainty.inertia_from_period(
            calibration["K"]["value"], calibration["K"]["u"],
            combined["T"], combined["u_T"],
            calibration["I0"]["value"], calibration["I0"]["u"])
    else:
        inertia = uncertainty.inertia_from_period(
            calibration["K"]["value"], calibration["K"]["u"],
            combined["T"], combined["u_T"])
    geometric = uncertainty.geometry(params, SHAPE_GEOMETRY_KEY[condition])
    error = uncertainty.percent_error(
        inertia["value"], inertia["u"], geometric["value"], geometric["u"])
    return {
        "T": combined, "inertia": inertia, "geometric": geometric,
        "error": {"value": error["value"] * 100, "u": error["u"] * 100},
        "groups": len(groups),
    }


def shape_preview(state, mode, params):
    lines = []
    for condition in SHAPE_CONDITIONS:
        try:
            estimate = shape_estimate(state, mode, condition, params)
        except ValueError as exc:
            message = str(exc)
            if message.startswith(SHAPE_LABELS[condition]):
                message = message[len(SHAPE_LABELS[condition]):]
            lines.append(f"- {SHAPE_LABELS[condition]}：{message}")
            continue
        t_text, _ = uncertainty.format_result(estimate["T"]["T"], estimate["T"]["u_T"], "s")
        lines.append(f"- {SHAPE_LABELS[condition]}：T = {t_text}，{estimate['groups']} 组"
                     f"{_a_type_note(estimate['groups'])}")
    if not lines:
        return "还没有测量组。"
    lines.extend(["", "± 后是合成标准不确定度 u_c（k=1）。"])
    return "\n".join(lines)


def parallel_estimate(state, mode, condition, params):
    if condition not in PARALLEL_CONDITIONS:
        raise ValueError("没有这个平行轴条件。")
    groups = active_groups_for(state, mode, "parallel", condition)
    if not groups:
        raise ValueError(f"{PARALLEL_LABELS[condition]}还没有测量组。")
    settings = (params or {}).get("settings") or {}
    combined = _combine_groups(groups, settings)
    calibration = calibration_estimate(state, mode, params)
    total = uncertainty.inertia_from_period(
        calibration["K"]["value"], calibration["K"]["u"],
        combined["T"], combined["u_T"])
    return {"T": combined, "total": total, "groups": len(groups)}


def parallel_preview(state, mode, params):
    lines = []
    for condition, label in parallel_conditions():
        try:
            estimate = parallel_estimate(state, mode, condition, params)
        except ValueError as exc:
            message = str(exc)
            if message.startswith(label):
                message = message[len(label):]
            lines.append(f"- {label}：{message}")
            continue
        t_text, _ = uncertainty.format_result(
            estimate["T"]["T"], estimate["T"]["u_T"], "s")
        lines.append(f"- {label}：T = {t_text}，{estimate['groups']} 组"
                     f"{_a_type_note(estimate['groups'])}")
    if not lines:
        return "还没有测量组。"
    lines.extend(["", "± 后是合成标准不确定度 u_c（k=1）。"])
    return "\n".join(lines)


def _student_float(text):
    if text is None or text == "":
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _check_item(key, label, student_text, expected, unit="", tolerance=0.01, absolute=False):
    student = _student_float(student_text)
    if student is None:
        return {"key": key, "label": label, "student": None, "ok": False,
                "issue": "还没有填", "unit": unit}
    if absolute:
        difference = abs(student - expected)
        ok = difference <= tolerance
        note = "" if ok else f"与原始数据相差 {difference:.3g} {unit}".strip()
    else:
        ok, note = uncertainty.check_relative(student, expected, tolerance)
    item = {"key": key, "label": label, "student": student, "ok": ok,
            "issue": note, "unit": unit}
    return item


def check_calibration(state, mode, params):
    estimate = calibration_estimate(state, mode, params)
    results = stage(state, mode, "calibrate")["results"]
    items = [
        _check_item("I1", "圆柱 I₁", results.get("I1"),
                    estimate["I1"]["value"], "kg·m²"),
        _check_item("K", "扭转常数 K", results.get("K"),
                    estimate["K"]["value"], "N·m/rad"),
        _check_item("I0", "载物盘 I₀", results.get("I0"),
                    estimate["I0"]["value"], "kg·m²"),
    ]
    for item, key in zip(items, ("I1", "K", "I0")):
        if item["ok"]:
            u = {"I1": estimate["I1"]["u"], "K": estimate["K"]["u"],
                 "I0": estimate["I0"]["u"]}[key]
            item["formatted"], item["sig_note"] = uncertainty.format_result(
                item["student"], u, item["unit"])
        elif item["student"] is not None:
            u = {"I1": estimate["I1"]["u"], "K": estimate["K"]["u"],
                 "I0": estimate["I0"]["u"]}[key]
            _, item["sig_note"] = uncertainty.format_result(
                estimate[key]["value"], u, item["unit"])
            item["u_text"] = f"按原始数据，不确定度约为 {u:.3g} {item['unit']}"
    return {"stage": "calibrate", "items": items,
            "passed": all(item["ok"] for item in items),
            "estimate": estimate}


def check_shapes(state, mode, params):
    results = stage(state, mode, "shapes")["results"]
    items = []
    for condition in SHAPE_CONDITIONS:
        row = results.get(condition) or {}
        try:
            estimate = shape_estimate(state, mode, condition, params)
        except ValueError as exc:
            items.append({"key": condition, "label": SHAPE_LABELS[condition],
                          "student": None, "ok": False, "issue": str(exc), "unit": ""})
            continue
        for key, label, expected, unit, tolerance, absolute in (
            ("Iexp", "I实验", estimate["inertia"]["value"], "kg·m²", 0.01, False),
            ("Igeo", "I几何", estimate["geometric"]["value"], "kg·m²", 0.01, False),
            ("E", "百分偏差", estimate["error"]["value"], "%", 1.0, True),
        ):
            item = _check_item(f"{condition}.{key}", f"{SHAPE_LABELS[condition]} {label}",
                               row.get(key), expected, unit, tolerance, absolute)
            item["condition"] = condition
            item["field"] = key
            item["passed"] = item["ok"]
            if item["ok"]:
                u = {"Iexp": estimate["inertia"]["u"], "Igeo": estimate["geometric"]["u"],
                     "E": estimate["error"]["u"]}[key]
                item["formatted"], item["sig_note"] = uncertainty.format_result(
                    item["student"], u, unit)
            items.append(item)
    return {"stage": "shapes", "items": items,
            "passed": all(item["ok"] for item in items)}


def _regression_from_student(results):
    symmetric = []
    asymmetric = []
    for distance in SYMMETRIC_DISTANCES:
        key = f"sym-{distance:g}"
        value = _student_float((results.get("I_total") or {}).get(key))
        if value is not None:
            symmetric.append(((distance * 1e-2) ** 2, value))
    for first, second in ASYMMETRIC_PAIRS:
        key = f"asym-{first:g}-{second:g}"
        value = _student_float((results.get("I_total") or {}).get(key))
        if value is not None:
            asymmetric.append((((first * 1e-2) ** 2) + ((second * 1e-2) ** 2), value))
    return symmetric, asymmetric


def student_points(results):
    return _regression_from_student(results)


def shape_uncertainties(state, mode, params):
    """{对象名: (u_I实验, u_I几何)}，给阶段2 图加误差棒；缺数据的对象不出现。"""
    errors = {}
    for condition in SHAPE_CONDITIONS:
        try:
            estimate = shape_estimate(state, mode, condition, params)
        except ValueError:
            continue
        errors[SHAPE_LABELS[condition]] = (estimate["inertia"]["u"],
                                           estimate["geometric"]["u"])
    return errors


def parallel_uncertainties(state, mode, params, results):
    """(对称 u 列表, 不对称 u 列表)，顺序与学生填的 I总 点一致。"""
    total = (results or {}).get("I_total") or {}

    def collect(keys):
        values = []
        for key in keys:
            try:
                values.append(parallel_estimate(state, mode, key, params)["total"]["u"])
            except ValueError:
                values.append(0.0)
        return values

    sym_keys = [f"sym-{distance:g}" for distance in SYMMETRIC_DISTANCES
                if _student_float(total.get(f"sym-{distance:g}")) is not None]
    asym_keys = [f"asym-{first:g}-{second:g}" for first, second in ASYMMETRIC_PAIRS
                 if _student_float(total.get(f"asym-{first:g}-{second:g}")) is not None]
    return collect(sym_keys), collect(asym_keys)


def _slope_item(key, label, student_text, regression, field, unit=""):
    student = _student_float(student_text)
    expected = regression[field]
    if student is None:
        return {"key": key, "label": label, "student": None, "ok": False,
                "issue": "还没有填", "unit": unit}
    ok, note = uncertainty.check_relative(student, expected, 0.05)
    item = {"key": key, "label": label, "student": student, "ok": ok,
            "issue": note, "unit": unit}
    if ok:
        item["formatted"], item["sig_note"] = uncertainty.format_result(
            student, regression[field + "_u"], unit)
    else:
        item["u_text"] = (f"按你填的 I总 点，回归的{label}不确定度约为 "
                          f"{regression[field + '_u']:.3g} {unit}").strip()
    return item


def check_parallel(state, mode, params):
    results = stage(state, mode, "parallel")["results"]
    items = []
    for condition, label in parallel_conditions():
        try:
            estimate = parallel_estimate(state, mode, condition, params)
        except ValueError as exc:
            items.append({"key": condition, "label": label, "student": None,
                          "ok": False, "issue": str(exc), "unit": "kg·m²"})
            continue
        item = _check_item(condition, f"{label} I总",
                           (results.get("I_total") or {}).get(condition),
                           estimate["total"]["value"], "kg·m²")
        item["condition"] = condition
        if item["ok"]:
            item["formatted"], item["sig_note"] = uncertainty.format_result(
                item["student"], estimate["total"]["u"], "kg·m²")
        elif item["student"] is not None:
            item["u_text"] = f"按原始数据，不确定度约为 {estimate['total']['u']:.3g} kg·m²"
        items.append(item)

    symmetric, asymmetric = _regression_from_student(results)
    for prefix, points, label in (
        ("sym", symmetric, "对称"),
        ("asym", asymmetric, "不对称"),
    ):
        if len(points) < 3:
            for field, field_label in (("slope", "斜率"), ("intercept", "截距")):
                items.append({
                    "key": f"{prefix}_{field}", "label": f"{label}{field_label}",
                    "student": None, "ok": False, "unit": "",
                    "issue": f"至少需要 3 个{label} I总 点",
                })
            continue
        regression = uncertainty.regression([item[0] for item in points],
                                            [item[1] for item in points])
        items.append(_slope_item(f"{prefix}_slope", f"{label}斜率",
                                 results.get(f"slope_{prefix}"), regression, "slope", "kg"))
        items.append(_slope_item(f"{prefix}_intercept", f"{label}截距",
                                 results.get(f"intercept_{prefix}"), regression,
                                 "intercept", "kg·m²"))
    return {"stage": "parallel", "items": items,
            "symmetric": symmetric, "asymmetric": asymmetric,
            "passed": all(item["ok"] for item in items)}


def questions_for(stage_key):
    return list(QUESTIONS.get(stage_key) or [])


def _param_mismatch_note(state, mode, groups):
    """组表下方提醒：有组不是在当前版本下测的，结果会被重算。"""
    active_id = (experiment.active_param(state, mode) or {}).get("id")
    stale = [group for group in groups
             if not group.get("superseded") and group.get("param_id") != active_id]
    if not stale:
        return ""
    labels = []
    for group in stale:
        label = group.get("param_label") or "未记录版本"
        if label not in labels:
            labels.append(label)
    return (f"\n\n注意：有 {len(stale)} 组是在 {'、'.join(labels)} 下测的；"
            "上表按当前采用版本重算。")


def groups_md(state, mode, stage_key):
    groups = groups_for(state, mode, stage_key)
    if not groups:
        return "还没有测量组。填上总时间，点「添加一组」。"
    if stage_key == "calibrate":
        lines = ["| 组 | N | 空盘总时间 / s | 加圆柱总时间 / s | T₀ / s | T₁ / s | 备注 |",
                 "| --- | --- | --- | --- | --- | --- | --- |"]
        for index, group in enumerate(groups, start=1):
            label = "第 " + str(index) + " 组" + ("（已作废）" if group.get("superseded") else "")
            lines.append(
                f"| {label} | {group['n_periods']} | {_fmt_total(group['t0'])} | "
                f"{_fmt_total(group['t1'])} | {_fmt_period(group['t0'], group['n_periods'])} | "
                f"{_fmt_period(group['t1'], group['n_periods'])} | {group.get('note') or '—'} |")
        return "\n".join(lines) + _param_mismatch_note(state, mode, groups)
    lines = ["| 组 | 条件 | N | 总时间 / s | T / s | 备注 |",
             "| --- | --- | --- | --- | --- | --- |"]
    labels = SHAPE_LABELS if stage_key == "shapes" else PARALLEL_LABELS
    for index, group in enumerate(groups, start=1):
        label = "第 " + str(index) + " 组" + ("（已作废）" if group.get("superseded") else "")
        lines.append(
            f"| {label} | {labels.get(group.get('condition'), group.get('condition'))} | "
            f"{group['n_periods']} | {_fmt_total(group['times'])} | "
            f"{_fmt_period(group['times'], group['n_periods'])} | {group.get('note') or '—'} |")
    return "\n".join(lines) + _param_mismatch_note(state, mode, groups)


def check_markdown(result):
    lines = ["| 量 | 结果 | 说明 |", "| --- | --- | --- |"]
    for item in result["items"]:
        if item.get("ok"):
            result_text = item.get("formatted") or "相符"
            note = item.get("sig_note") or "相符"
        elif item.get("student") is None:
            result_text = "—"
            note = item.get("issue") or "还没有填"
        else:
            result_text = "与原始数据不一致"
            note = item.get("issue") or "请检查公式、单位和读数"
            if item.get("u_text"):
                note += "；" + item["u_text"]
        lines.append(f"| {item['label']} | {result_text} | {note} |")
    passed = sum(1 for item in result["items"] if item.get("ok"))
    lines.append("")
    lines.append(f"**{passed}/{len(result['items'])} 项相符。**")
    lines.append("")
    lines.append("表中 ± 后是合成标准不确定度 u_c（k=1）。")
    return "\n".join(lines)
