"""真实/虚拟两种实验模式、阶段和阶段0器材参数。

这里只做数据与校验，不计算不确定度，也不推进教学阶段。
参数版本只追加，不覆盖旧版本；当前采用哪一版由学生选择。
"""
from datetime import datetime
import math
import re
from uuid import uuid4

from torsion import nameplate_instrument

MODE_REAL = "real"
MODE_VIRTUAL = "virtual"
MODES = (MODE_REAL, MODE_VIRTUAL)
MODE_LABELS = {MODE_REAL: "真实实验模式", MODE_VIRTUAL: "虚拟实验模式"}

STAGE_PARAMS = "params"
STAGE_CALIBRATE = "calibrate"
STAGE_SHAPES = "shapes"
STAGE_PARALLEL = "parallel"
STAGE_SUMMARY = "summary"
STAGES = (STAGE_PARAMS, STAGE_CALIBRATE, STAGE_SHAPES, STAGE_PARALLEL, STAGE_SUMMARY)
STAGE_LABELS = {
    STAGE_PARAMS: "阶段0 器材参数",
    STAGE_CALIBRATE: "阶段1 标定",
    STAGE_SHAPES: "阶段2 规则刚体",
    STAGE_PARALLEL: "阶段3 平行轴",
    STAGE_SUMMARY: "阶段4 图表与报告",
}

STAGE_HINTS = {
    STAGE_PARAMS: "**阶段0**：参数可随时修改、追加；每次保存生成一个新版本。"
                  "阶段1～3 使用你选定的“当前采用版本”。",
    STAGE_CALIBRATE: "**阶段1 标定**：空盘与加圆柱不限组数，学生填 I₁、K、I₀，"
                     "程序算 A/B 类不确定度和有效数字，AI 检查并解释。",
    STAGE_SHAPES: "**阶段2 规则刚体**：圆筒、球体、细杆，学生填 I实验、I几何、百分偏差，"
                  "AI 检查并回答阶段问题。",
    STAGE_PARALLEL: "**阶段3 平行轴**：细杆基准、五个对称距离、四组不对称；"
                    "学生填 I总、斜率、截距，程序按学生点画图，AI 检查。",
    STAGE_SUMMARY: "**阶段4 图表与报告**：按学生数据生成图表和标准实验报告草稿，不自动提交。",
}

SETTING_FIELDS = (
    ("n_periods", "周期数 N", "", "10", "一次计时包含几个周期，5～20 的整数。"),
    ("angle_deg", "摆角", "°", "60", "本实验固定 60°，在讲义允许的 40°～90° 内。"),
    ("timer_resolution_s", "计时器分辨力", "s", "0.001", "用于 B 类不确定度。"),
    ("balance_resolution_g", "天平误差限", "g", "0.1", "用于质量 B 类不确定度；可按实验室仪器修改。"),
    ("caliper_resolution_mm", "卡尺误差限", "mm", "0.02", "用于直径/长度 B 类不确定度。"),
    ("ruler_resolution_mm", "钢尺误差限", "mm", "1.0", "量细杆等较长尺寸时使用。"),
)

OBJECT_FIELDS = (
    ("cylinder", "塑料圆柱", (
        ("mass", "质量", "g", "例如 620.0", "天平读数；可追加多次。"),
        ("diameter", "直径", "mm", "例如 99.98, 100.02, 100.00",
         "三次读数用逗号、顿号、空格或换行分开；也可以只填一个。"),
    )),
    ("tube", "金属圆筒", (
        ("mass", "质量", "g", "例如 620.0", "天平读数；可追加多次。"),
        ("outer", "外径", "mm", "例如 99.96, 100.04, 100.00", "外径三次读数；逗号、顿号、空格或换行分开。"),
        ("inner", "内径", "mm", "例如 89.98, 90.02, 90.00", "内径必须填，不能只用外径；分隔方式同上。"),
    )),
    ("sphere", "实心球体", (
        ("mass", "质量", "g", "例如 550.0", "天平读数；可追加多次。"),
        ("diameter", "直径", "mm", "例如 89.96, 90.04, 90.00", "用大卡尺量直径。"),
    )),
    ("rod", "金属细杆", (
        ("mass", "质量", "g", "例如 168.0", "天平读数。"),
        ("length", "长度", "mm", "例如 500.0", "杆全长；代入公式前换成 m。"),
    )),
    ("slider", "滑块（一只）", (
        ("mass", "质量", "g", "例如 240.0", "两只相同滑块，填一只的质量。"),
        ("diameter", "直径", "mm", "例如 30.00", "用于滑块自身转动惯量。"),
    )),
)

SETTING_UI = {
    "n_periods": "p_n", "angle_deg": "p_angle", "timer_resolution_s": "p_timer",
    "balance_resolution_g": "p_balance", "caliper_resolution_mm": "p_caliper",
    "ruler_resolution_mm": "p_ruler",
}
OBJECT_UI = {}


def ui_key(object_key, field_key):
    return f"p_{object_key}_{field_key}"


for _object_key, _name, _fields in OBJECT_FIELDS:
    for _field_key, _label, _unit, _example, _info in _fields:
        OBJECT_UI[(_object_key, _field_key)] = ui_key(_object_key, _field_key)

FIELD_KEYS = tuple(SETTING_UI.values()) + tuple(OBJECT_UI.values()) + ("p_note",)


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _default_settings():
    values = {}
    for key, _label, _unit, example, _info in SETTING_FIELDS:
        values[key] = example
    return values


def blank_form():
    form = {key: "" for key in FIELD_KEYS}
    form["p_n"] = "10"
    form["p_angle"] = "60"
    form["p_timer"] = "0.001"
    form["p_balance"] = "0.1"
    form["p_caliper"] = "0.02"
    form["p_ruler"] = "1.0"
    return form


def _split_numbers(text):
    raw = str(text or "").strip()
    if not raw:
        return []
    normalized = re.sub(r"[,，;；、\s]+", ",", raw)
    return [part for part in normalized.split(",") if part]


def parse_readings(text, label):
    values = []
    for part in _split_numbers(text):
        try:
            value = float(part)
        except ValueError:
            raise ValueError(f"{label}要填数字，用逗号、空格或换行分开，不要带单位。")
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{label}必须是正的有限数字。")
        values.append(value)
    return values


def _parse_setting(text, key, label, minimum=None, maximum=None, integer=False):
    parts = _split_numbers(text)
    if not parts:
        raise ValueError(f"请填写{label}。")
    try:
        value = float(parts[0])
    except ValueError:
        raise ValueError(f"{label}要填数字。")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label}必须是正的有限数字。")
    if integer:
        if abs(value - round(value)) > 1e-9:
            raise ValueError(f"{label}必须是整数。")
        value = int(round(value))
    if minimum is not None and value < minimum:
        raise ValueError(f"{label}不能小于 {minimum:g}。")
    if maximum is not None and value > maximum:
        raise ValueError(f"{label}不能大于 {maximum:g}。")
    return value


def form_to_param(form):
    """把页面表单转成参数版本。允许暂时缺项，缺项在预览里标出来。"""
    form = form or {}
    settings = {
        "n_periods": _parse_setting(form.get("p_n"), "n_periods", "周期数 N", 5, 20, True),
        "angle_deg": _parse_setting(form.get("p_angle"), "angle_deg", "摆角", 40, 90),
        "timer_resolution_s": _parse_setting(
            form.get("p_timer"), "timer_resolution_s", "计时器分辨力"),
        "balance_resolution_g": _parse_setting(
            form.get("p_balance"), "balance_resolution_g", "天平误差限"),
        "caliper_resolution_mm": _parse_setting(
            form.get("p_caliper"), "caliper_resolution_mm", "卡尺误差限"),
        "ruler_resolution_mm": _parse_setting(
            form.get("p_ruler"), "ruler_resolution_mm", "钢尺误差限"),
    }
    objects = {}
    missing = []
    for object_key, name, fields in OBJECT_FIELDS:
        objects[object_key] = {}
        for field_key, label, unit, _example, _info in fields:
            text = form.get(ui_key(object_key, field_key))
            values = parse_readings(text, f"{name}{label}")
            objects[object_key][field_key] = values
            if not values:
                missing.append(f"{name}{label}")
    note = str(form.get("p_note") or "").strip()[:800]
    return {
        "settings": settings,
        "objects": objects,
        "note": note,
        "complete": not missing,
        "missing": missing,
    }


def _fmt(value):
    if isinstance(value, int):
        return str(value)
    text = f"{float(value):.8g}"
    return text


def _mean(values):
    return sum(values) / len(values) if values else None


def param_to_form(param):
    form = blank_form()
    settings = (param or {}).get("settings") or {}
    for key, ui in SETTING_UI.items():
        if key in settings:
            form[ui] = _fmt(settings[key])
    objects = (param or {}).get("objects") or {}
    for object_key, _name, fields in OBJECT_FIELDS:
        payload = objects.get(object_key) or {}
        for field_key, _label, _unit, _example, _info in fields:
            values = payload.get(field_key) or []
            form[ui_key(object_key, field_key)] = ", ".join(_fmt(value) for value in values)
    form["p_note"] = (param or {}).get("note") or ""
    return form


def _settings_md(param):
    settings = param.get("settings") or {}
    lines = ["| 设置 | 值 |", "| --- | --- |"]
    labels = {key: (label, unit) for key, label, unit, _example, _info in SETTING_FIELDS}
    for key, _label, _unit, _example, _info in SETTING_FIELDS:
        label, unit = labels[key]
        value = settings.get(key, "—")
        lines.append(f"| {label} | {_fmt(value)} {unit} |")
    return "\n".join(lines)


def _objects_md(param):
    lines = ["| 物体 | 量 | 原始读数 | 平均 |", "| --- | --- | --- | --- |"]
    objects = param.get("objects") or {}
    for object_key, name, fields in OBJECT_FIELDS:
        payload = objects.get(object_key) or {}
        for field_key, label, unit, _example, _info in fields:
            values = payload.get(field_key) or []
            raw = "、".join(_fmt(value) for value in values) if values else "未填"
            mean = _mean(values)
            average = f"{_fmt(mean)} {unit}" if mean is not None else "—"
            lines.append(f"| {name} | {label} | {raw} | {average} |")
    return "\n".join(lines)


def param_preview(param):
    if not param:
        return "还没有参数版本。填写下面的表，点「保存为新版本」。"
    state = "已填齐" if param.get("complete") else ("还缺：" + "、".join(param.get("missing") or []))
    note = (param.get("note") or "").strip()
    text = [f"**这一版的填写状态：** {state}"]
    if note:
        text.extend(["", f"备注：{note}"])
    text.extend(["", _settings_md(param), "", _objects_md(param)])
    return "\n".join(text)


def param_summary(param):
    if not param:
        return "尚无参数"
    total = sum(len(fields) for _key, _name, fields in OBJECT_FIELDS)
    filled = 0
    for object_key, _name, fields in OBJECT_FIELDS:
        payload = (param.get("objects") or {}).get(object_key) or {}
        for field_key, _label, _unit, _example, _info in fields:
            if payload.get(field_key):
                filled += 1
    return f"{filled}/{total} 项" + ("，已填齐" if filled == total else "")


def virtual_param():
    plate = nameplate_instrument()
    objects = {
        "cylinder": {
            "mass": [plate["cylinder_mass_kg"] * 1000],
            "diameter": [float(value) for value in plate["cylinder_diameter_mm"]],
        },
        "tube": {
            "mass": [plate["tube_mass_kg"] * 1000],
            "outer": [float(value) for value in plate["tube_outer_mm"]],
            "inner": [float(value) for value in plate["tube_inner_mm"]],
        },
        "sphere": {
            "mass": [plate["sphere_mass_kg"] * 1000],
            "diameter": [float(value) for value in plate["sphere_diameter_mm"]],
        },
        "rod": {
            "mass": [plate["rod_mass_kg"] * 1000],
            "length": [float(plate["rod_length_mm"])],
        },
        "slider": {
            "mass": [plate["slider_mass_kg"] * 1000],
            "diameter": [float(plate["slider_diameter_mm"])],
        },
    }
    settings = {
        "n_periods": 10,
        "angle_deg": 60.0,
        "timer_resolution_s": 0.001,
        "balance_resolution_g": 0.1,
        "caliper_resolution_mm": 0.02,
        "ruler_resolution_mm": 1.0,
    }
    return {
        "id": "virtual-v1",
        "label": "虚拟器材（程序给定）",
        "created_at": "—",
        "mode": MODE_VIRTUAL,
        "system": True,
        "settings": settings,
        "objects": objects,
        "note": "虚拟模式的器材参数由程序给定，只读。",
        "complete": True,
        "missing": [],
    }


def blank_state():
    state = {
        "mode": MODE_REAL,
        "stage": STAGE_PARAMS,
        MODE_REAL: {"param_versions": [], "active_param_id": None, "stage": STAGE_PARAMS},
        MODE_VIRTUAL: {"param_versions": [], "active_param_id": None, "stage": STAGE_PARAMS},
    }
    _ensure_virtual(state)
    return state


def _ensure_virtual(state):
    payload = state.setdefault(MODE_VIRTUAL, {})
    payload.setdefault("param_versions", [])
    payload.setdefault("stage", STAGE_PARAMS)
    if not payload["param_versions"]:
        version = virtual_param()
        payload["param_versions"].append(version)
        payload["active_param_id"] = version["id"]
    if payload.get("active_param_id") not in {item["id"] for item in payload["param_versions"]}:
        payload["active_param_id"] = payload["param_versions"][-1]["id"]


def ensure_state(session):
    state = session.get("experiment")
    if not isinstance(state, dict):
        state = blank_state()
        session["experiment"] = state
    state.setdefault("mode", MODE_REAL)
    if state["mode"] not in MODES:
        state["mode"] = MODE_REAL
    state.setdefault("stage", STAGE_PARAMS)
    for mode in MODES:
        payload = state.setdefault(mode, {})
        payload.setdefault("param_versions", [])
        payload.setdefault("stage", STAGE_PARAMS)
        payload.setdefault("active_param_id", None)
    _ensure_virtual(state)
    return state


def versions(state, mode):
    return list((state.get(mode) or {}).get("param_versions") or [])


def active_param(state, mode):
    payload = state.get(mode) or {}
    active_id = payload.get("active_param_id")
    found = [item for item in payload.get("param_versions") or [] if item.get("id") == active_id]
    if found:
        return found[-1]
    items = payload.get("param_versions") or []
    return items[-1] if items else None


def set_mode(state, mode):
    if mode not in MODES:
        raise ValueError("请选择真实实验模式或虚拟实验模式。")
    state["mode"] = mode
    state["stage"] = (state.get(mode) or {}).get("stage") or STAGE_PARAMS
    return state


def set_stage(state, stage):
    if stage not in STAGES:
        raise ValueError("没有这个实验阶段。")
    state["stage"] = stage
    state.setdefault(state["mode"], {})["stage"] = stage
    return state


def add_version(state, mode, param, label=None):
    if mode != MODE_REAL:
        raise ValueError("虚拟模式的器材参数由程序给定，不能修改。")
    payload = state.setdefault(MODE_REAL, {})
    items = payload.setdefault("param_versions", [])
    version = dict(param)
    version.update(
        id="pv_" + uuid4().hex[:10],
        label=label or f"v{len(items) + 1}",
        created_at=now(),
        mode=MODE_REAL,
        system=False,
    )
    items.append(version)
    payload["active_param_id"] = version["id"]
    return version


def set_active(state, mode, version_id):
    payload = state.setdefault(mode, {})
    found = [item for item in payload.get("param_versions") or [] if item.get("id") == version_id]
    if not found:
        raise ValueError("没有这个参数版本。")
    payload["active_param_id"] = version_id
    return found[-1]


def find_version(state, mode, version_id):
    for item in versions(state, mode):
        if item.get("id") == version_id:
            return item
    return None


def version_choices(state, mode):
    items = versions(state, mode)
    choices = []
    for index, item in enumerate(items, start=1):
        label = item.get("label") or f"v{index}"
        created = (item.get("created_at") or "")[:16].replace("T", " ")
        summary = param_summary(item)
        choices.append((f"{label} · {created} · {summary}", item["id"]))
    return choices


def versions_md(state, mode, active_id=None):
    items = versions(state, mode)
    if not items:
        return "还没有参数版本。填好上面的表，点「保存为新版本」。"
    lines = ["| 版本 | 时间 | 状态 | 备注 |", "| --- | --- | --- | --- |"]
    for index, item in enumerate(items, start=1):
        label = item.get("label") or f"v{index}"
        if item.get("id") == active_id:
            label += "（当前采用）"
        created = (item.get("created_at") or "—")[:16].replace("T", " ")
        note = (item.get("note") or "").replace("|", "｜")[:40]
        lines.append(f"| {label} | {created} | {param_summary(item)} | {note} |")
    return "\n".join(lines)


def active_md(state, mode):
    param = active_param(state, mode)
    if not param:
        return "还没有选定参数版本。阶段1～3 会等你在阶段0 保存并选定一版。"
    label = param.get("label") or "参数版本"
    created = (param.get("created_at") or "—")[:16].replace("T", " ")
    note = f"；备注：{param['note']}" if param.get("note") else ""
    return (f"**当前采用：** {label} · {created} · {param_summary(param)}{note}")


def stage_placeholder(stage):
    return STAGE_HINTS.get(stage, STAGE_HINTS[STAGE_PARAMS])
