"""虚拟练习与实验室录入的记录合同。

这里只处理来源、录入文字和有效记录。不调用周期测量，也不读取仪器真值。
旧实验事件没有 origin 时，一律视为虚拟练习。
"""
import math
import re


VIRTUAL = "virtual"
LAB = "lab"
ORIGINS = (VIRTUAL, LAB)
ORIGIN_LABEL = {VIRTUAL: "虚拟练习", LAB: "实验室录入"}
LAB_EVENT_TYPES = ("lab_entry", "lab_correction")

MASS_FIELDS = (
    ("cylinder_mass", "塑料圆柱质量", "g"),
    ("tube_mass", "金属圆筒质量", "g"),
    ("sphere_mass", "实心球体质量", "g"),
    ("rod_mass", "金属细杆质量", "g"),
    ("slider_mass", "滑块质量", "g"),
)
LENGTH_FIELDS = (
    ("rod_length", "金属细杆长度", "mm"),
    ("slider_diameter", "滑块直径", "mm"),
)
DIAMETER_FIELDS = (
    ("cylinder", "cylinder_size", "塑料圆柱直径"),
    ("sphere", "sphere_size", "实心球体直径"),
)
TUBE_DIAMETERS = (
    ("tube_outer", "金属圆筒外径"),
    ("tube_inner", "金属圆筒内径"),
)
QUANTITY_PARTS = {
    "cylinder_inertia": ("cylinder",),
    "torsion_constant": ("cylinder",),
    "carrier_inertia": ("cylinder",),
    "tube_inertia": ("tube",),
    "sphere_inertia": ("sphere",),
    "rod_inertia": ("rod",),
    "sliders_total_inertia": ("rod", "slider"),
}


def blank_equipment():
    return {"version": 0, "use_nameplate": False, "fields": {}, "diameter_mode": {}}


def current_origin(host):
    origin = (host or {}).get("data_origin") or VIRTUAL
    return origin if origin in ORIGINS else VIRTUAL


def origin_label(origin):
    return ORIGIN_LABEL.get(origin, ORIGIN_LABEL[VIRTUAL])


def parse_n(n_periods):
    try:
        count = float(n_periods)
    except (TypeError, ValueError):
        count = float("nan")
    if not math.isfinite(count) or abs(count - round(count)) > 1e-9 or not 5 <= round(count) <= 20:
        raise ValueError("周期数 N 应为 5～20 的整数。")
    return int(round(count))


def _clean_text(text):
    return "".join(ch for ch in str(text) if ch >= " " or ch in "\n\t")


def parse_positive_number(text, label, unit):
    """保留原始数字文本。非法或过大时直接拒绝，不截成另一个数。"""
    raw = _clean_text(text).strip()
    if not raw:
        raise ValueError(f"请填写{label}。")
    if not re.fullmatch(r"\d+(\.\d+)?", raw):
        raise ValueError(f"{label}要填正的有限数字，单位是{unit}。不要带单位或字母，这次没有改成别的数。")
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label}必须是正数。")
    if value > 1e6:
        raise ValueError(f"{label}过大。这次没有截短，也没有另记成一组数。")
    return raw, value


def parse_seconds(text):
    raw, value = parse_positive_number(text, "时间", "秒")
    if value > 100000:
        raise ValueError("这个时间过大，没有另记成一组读数。请确认单位是秒。")
    return raw, value


def clean_note(text):
    cleaned = _clean_text(text or "").strip()
    if len(cleaned) > 200:
        raise ValueError("备注请少于 200 个字。")
    return cleaned


def trim_number(value):
    return f"{float(value):.8f}".rstrip("0").rstrip(".")


def total_display(summary):
    if summary.get("total_time_text"):
        return summary["total_time_text"]
    if summary.get("total_time_s") is None:
        return "—"
    if summary.get("origin") == LAB:
        return trim_number(summary["total_time_s"])
    return f"{summary['total_time_s']:.3f}"


def period_display(summary):
    if summary.get("period_text"):
        return summary["period_text"]
    if summary.get("origin") == LAB:
        return trim_number(summary["period_s"])
    return f"{summary['period_s']:.4f}"


def format_reading(summary):
    return (f"N = {summary['n_periods']}，总时间 {total_display(summary)} s，"
            f"T = {period_display(summary)} s")


def case_status_text(hits):
    if not hits:
        return "未测"
    last = hits[-1]
    count = f"已测 {len(hits)} 次" if len(hits) > 1 else "已测 1 次"
    return f"{count}。最近一次：{format_reading(last)}"


def build_lab_summary(case, n_periods, mode, raw_text, note, measurement_id, corrects=None):
    """由学生输入生成摘要。调用方不得再跑虚拟测量来填这些字段。"""
    count = parse_n(n_periods)
    if mode not in ("total_time", "period"):
        raise ValueError("请选择记总时间，或记单个周期。")
    raw, value = parse_seconds(raw_text)
    remark = clean_note(note)
    if mode == "total_time":
        total_time_s = value
        total_time_text = raw
        period_s = value / count
        period_text = None
    else:
        total_time_s = None
        total_time_text = None
        period_s = value
        period_text = raw
    summary = {
        "kind": "lab_timing",
        "success": True,
        "origin": LAB,
        "measurement_id": measurement_id,
        "experiment_id": measurement_id,
        "case_id": case["case_id"],
        "source": "student",
        "entry_mode": mode,
        "raw_value": raw,
        "total_time_text": total_time_text,
        "period_text": period_text,
        "note": remark,
        "params": {
            "assembly": case["assembly"],
            "n_periods": count,
            "distance_cm": case["distance_cm"],
            "distance2_cm": case["distance2_cm"],
            "placement": case["placement"],
        },
        "assembly_name": case["name"],
        "n_periods": count,
        "total_time_s": total_time_s,
        "period_s": float(period_s),
        "geometry": {
            "kind": "lab",
            "note": "实验室录入的周期。器材以本次保存的参数为准，不使用虚拟仪器内部常量。",
        },
    }
    if corrects:
        summary["corrects"] = corrects
    return summary


def _stored_result(event):
    kind = event.get("type")
    result = event.get("result")
    if not isinstance(result, dict) or "period_s" not in result:
        return None
    if kind == "experiment":
        default_origin = VIRTUAL
    elif kind in LAB_EVENT_TYPES:
        default_origin = LAB
    else:
        return None
    item = dict(result)
    item["origin"] = item.get("origin") or default_origin
    if item["origin"] not in ORIGINS:
        item["origin"] = default_origin
    if not item.get("measurement_id"):
        item["measurement_id"] = item.get("experiment_id")
    return item


def measurement_rows(host, origin=None):
    """按发生顺序给出副本，并标明是否已被更正。计算应丢掉 superseded 的行。"""
    if not host:
        return []
    items = []
    for event in host.get("records") or []:
        item = _stored_result(event)
        if item is not None:
            items.append(item)
    corrected = {item.get("corrects") for item in items if item.get("corrects")}
    seen = set()
    rows = []
    for item in items:
        ident = item.get("measurement_id")
        item["superseded"] = bool(ident and ident in corrected)
        if ident:
            seen.add(ident)
        if origin is not None and item.get("origin") != origin:
            continue
        rows.append(item)
    for raw in host.get("_notebook") or []:
        if not isinstance(raw, dict) or "period_s" not in raw:
            continue
        ident = raw.get("measurement_id") or raw.get("experiment_id")
        if ident and ident in seen:
            continue
        if ident and ident in corrected:
            continue
        item = dict(raw)
        item["origin"] = item.get("origin") or VIRTUAL
        item["measurement_id"] = ident
        item["superseded"] = False
        if origin is not None and item["origin"] != origin:
            continue
        if ident:
            seen.add(ident)
        rows.append(item)
    return rows


def active_measurements(host, origin=None):
    return [item for item in measurement_rows(host, origin) if not item.get("superseded")]


def _split_numbers(text, label, mode):
    raw = _clean_text(text or "").strip()
    if not raw:
        return None
    parts = [part for part in re.split(r"[,，、\s]+", raw) if part]
    values = []
    for part in parts:
        _, value = parse_positive_number(part, label, "mm")
        values.append(value)
    if mode == "mean":
        if len(values) != 1:
            raise ValueError(f"{label}选的是平均直径，只填一个数。")
        return raw, (values[0],)
    if mode != "readings":
        raise ValueError("直径请选择三次读数或平均直径。")
    if len(values) != 3:
        raise ValueError(f"{label}选的是三次读数，请填三个数，用逗号分开。")
    return raw, tuple(values)


def _store_scalar(form, key, label, unit, fields):
    text = _clean_text(form.get(key) or "").strip()
    if not text:
        return
    raw, _ = parse_positive_number(text, label, unit)
    fields[key] = {"text": raw}


def normalize_equipment_form(form):
    """检查已填的格子。允许先空着，但不接受非法数字。"""
    form = form or {}
    fields = {}
    modes = {}
    for key, label, unit in MASS_FIELDS + LENGTH_FIELDS:
        _store_scalar(form, key, label, unit, fields)
    for obj, key, label in DIAMETER_FIELDS:
        mode = form.get(f"{obj}_mode") or "readings"
        parsed = _split_numbers(form.get(key), label, mode)
        modes[obj] = mode if mode in ("readings", "mean") else "readings"
        if parsed:
            raw, _ = parsed
            fields[key] = {"text": raw}
            modes[obj] = mode
    tube_mode = form.get("tube_mode") or "readings"
    if tube_mode not in ("readings", "mean"):
        raise ValueError("直径请选择三次读数或平均直径。")
    modes["tube"] = tube_mode
    for key, label in TUBE_DIAMETERS:
        parsed = _split_numbers(form.get(key), label, tube_mode)
        if parsed:
            raw, _ = parsed
            fields[key] = {"text": raw}
    return fields, modes


def form_from_equipment(equipment):
    equipment = equipment or blank_equipment()
    form = {key: "" for key, _, _ in MASS_FIELDS + LENGTH_FIELDS}
    form.update({key: "" for _, key, _ in DIAMETER_FIELDS})
    form.update({key: "" for key, _ in TUBE_DIAMETERS})
    modes = equipment.get("diameter_mode") or {}
    form["cylinder_mode"] = modes.get("cylinder") or "readings"
    form["tube_mode"] = modes.get("tube") or "readings"
    form["sphere_mode"] = modes.get("sphere") or "readings"
    for key, payload in (equipment.get("fields") or {}).items():
        if isinstance(payload, dict):
            form[key] = payload.get("text") or ""
    return form


def equipment_label(equipment):
    if not equipment or int(equipment.get("version") or 0) <= 0:
        return "还没有保存本次器材参数"
    version = int(equipment["version"])
    if equipment.get("use_nameplate"):
        return f"第 {version} 版，已确认与页面铭牌相同"
    return f"第 {version} 版，学生填写"


def _mass_kg(fields, key):
    payload = fields.get(key)
    if not payload:
        return None
    _, grams = parse_positive_number(payload.get("text"), key, "g")
    return grams / 1000.0


def _length_mm(fields, key, label, mode=None):
    payload = fields.get(key)
    if not payload:
        return None
    if mode is None:
        _, value = parse_positive_number(payload.get("text"), label, "mm")
        return value
    parsed = _split_numbers(payload.get("text"), label, mode)
    if not parsed:
        return None
    _, values = parsed
    return values


def instrument_from_equipment(equipment, quantity, nameplate):
    """实验室核对用的公开参数。未保存或未确认时，不回退到铭牌。"""
    if quantity not in QUANTITY_PARTS:
        raise ValueError("请选择要核对的量。")
    if not equipment or int(equipment.get("version") or 0) <= 0:
        raise ValueError("还没有保存本次器材参数。请填写后保存，或明确选择与页面铭牌相同。不会借用虚拟铭牌。")
    if equipment.get("use_nameplate"):
        if not nameplate:
            raise ValueError("页面铭牌没有准备好。")
        return dict(nameplate)
    fields = equipment.get("fields") or {}
    modes = equipment.get("diameter_mode") or {}
    missing = []
    instrument = {}
    parts = QUANTITY_PARTS[quantity]

    def take_mass(part, key, label, dest):
        value = _mass_kg(fields, key)
        if value is None:
            missing.append(label)
        else:
            instrument[dest] = value

    def take_diam(part, key, label, dest, mode_name):
        value = _length_mm(fields, key, label, modes.get(mode_name) or "readings")
        if value is None:
            missing.append(label)
        else:
            instrument[dest] = value

    if "cylinder" in parts:
        take_mass("cylinder", "cylinder_mass", "塑料圆柱质量", "cylinder_mass_kg")
        take_diam("cylinder", "cylinder_size", "塑料圆柱直径", "cylinder_diameter_mm", "cylinder")
    if "tube" in parts:
        take_mass("tube", "tube_mass", "金属圆筒质量", "tube_mass_kg")
        take_diam("tube", "tube_outer", "金属圆筒外径", "tube_outer_mm", "tube")
        take_diam("tube", "tube_inner", "金属圆筒内径", "tube_inner_mm", "tube")
    if "sphere" in parts:
        take_mass("sphere", "sphere_mass", "实心球体质量", "sphere_mass_kg")
        take_diam("sphere", "sphere_size", "实心球体直径", "sphere_diameter_mm", "sphere")
    if "rod" in parts:
        take_mass("rod", "rod_mass", "金属细杆质量", "rod_mass_kg")
        length = _length_mm(fields, "rod_length", "金属细杆长度")
        if length is None:
            missing.append("金属细杆长度")
        else:
            instrument["rod_length_mm"] = length
    if "slider" in parts:
        take_mass("slider", "slider_mass", "滑块质量", "slider_mass_kg")
        diameter = _length_mm(fields, "slider_diameter", "滑块直径")
        if diameter is None:
            missing.append("滑块直径")
        else:
            instrument["slider_diameter_mm"] = diameter
    if missing:
        raise ValueError("还缺" + "、".join(missing) + "。周期可以先留着，这次不作数值核对，也不会改用虚拟铭牌。")
    return instrument


def forms_differ(saved, form):
    current = form_from_equipment(saved)
    form = form or {}
    keys = [key for key, _, _ in MASS_FIELDS + LENGTH_FIELDS]
    keys += [key for _, key, _ in DIAMETER_FIELDS]
    keys += [key for key, _ in TUBE_DIAMETERS]
    keys += ["cylinder_mode", "tube_mode", "sphere_mode"]
    for key in keys:
        if (form.get(key) or "") != (current.get(key) or ""):
            return True
    return False
