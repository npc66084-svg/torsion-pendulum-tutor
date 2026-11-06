"""页面用的示意图与进度条。只画几何关系，不读取或计算转动惯量真值。"""
from html import escape

from torsion import ASSEMBLIES

_CENTER = 340.0
_SCALE = 8.2
_BASE_Y = 238.0


def _num(value):
    return f"{float(value):g}"


def _distance_label(distance_cm):
    return f"{_num(distance_cm)} cm"


def _object_svg(assembly, measured):
    """按对象画载物盘、圆筒、球体或细杆。坐标是示意，不按真实尺寸。"""
    parts = []
    if assembly == "carrier":
        parts.append(_disk())
        parts.append(_label(_CENTER, 128, "空载物盘", 13, "#1b3a4b", "middle", "600"))
    elif assembly == "carrier_cylinder":
        parts.append(_disk())
        parts.append(
            '<rect x="282" y="104" width="116" height="52" rx="6" fill="#cfe0da" '
            'stroke="#1f6f6a" stroke-width="1.6"/>')
        parts.append(
            '<ellipse cx="340" cy="104" rx="58" ry="11" fill="#e6f0ec" '
            'stroke="#1f6f6a" stroke-width="1.6"/>')
        parts.append(_label(_CENTER, 138, "塑料圆柱", 12, "#1f6f6a", "middle", "600"))
    elif assembly == "carrier_tube":
        parts.append(_disk())
        parts.append(
            '<rect x="278" y="100" width="124" height="56" rx="5" fill="#eadfce" '
            'stroke="#b85c38" stroke-width="1.8"/>')
        parts.append(
            '<rect x="302" y="116" width="76" height="40" rx="3" fill="#fffdf8" '
            'stroke="#b85c38" stroke-width="1.2" stroke-dasharray="4 3"/>')
        parts.append(_label(_CENTER, 138, "金属圆筒", 12, "#b85c38", "middle", "600"))
        parts.append(_label(340, 94, "外径 / 内径", 10, "#8a5a44", "middle", "400"))
    elif assembly == "carrier_sphere":
        parts.append(_disk())
        parts.append(
            '<circle cx="340" cy="120" r="42" fill="#dfe8f0" stroke="#3f6f8a" stroke-width="1.8"/>')
        parts.append(
            '<ellipse cx="326" cy="106" rx="12" ry="7" fill="#ffffff" opacity="0.55"/>')
        parts.append(_label(_CENTER, 138, "实心球体", 12, "#3f6f8a", "middle", "600"))
    elif assembly == "rod":
        parts.append(_rod())
        parts.append(_label(_CENTER, 150, "金属细杆", 12, "#1b3a4b", "middle", "600"))
    elif assembly == "rod_sliders":
        parts.append(_rod())
        parts.append(
            '<circle cx="340" cy="166" r="9" fill="#1f6f6a" stroke="#fffdf8" stroke-width="2"/>')
        parts.append(_label(_CENTER, 150, "细杆 + 两侧滑块", 12, "#1f6f6a", "middle", "600"))
    else:
        parts.append(_disk())
    if measured:
        parts.append(
            '<g><rect x="522" y="18" width="92" height="24" rx="12" fill="#e3f2ec" '
            'stroke="#1f6f6a"/><text x="568" y="35" text-anchor="middle" font-size="12" '
            'fill="#1f6f6a" font-weight="600">本轮已测</text></g>')
    else:
        parts.append(
            '<g><rect x="522" y="18" width="92" height="24" rx="12" fill="#f6efe4" '
            'stroke="#d8c8b4"/><text x="568" y="35" text-anchor="middle" font-size="12" '
            'fill="#8a7a68">待测量</text></g>')
    return "".join(parts)


def _disk():
    return (
        '<ellipse cx="340" cy="166" rx="118" ry="24" fill="#d9e4df" stroke="#1f6f6a" '
        'stroke-width="2"/>'
        '<ellipse cx="340" cy="160" rx="118" ry="24" fill="#edf4f1" stroke="#1f6f6a" '
        'stroke-width="2"/>'
        '<ellipse cx="340" cy="160" rx="34" ry="8" fill="#c3d6cf"/>'
    )


def _rod():
    return (
        '<rect x="92" y="160" width="496" height="12" rx="6" fill="#e6d6bf" '
        'stroke="#8a6b4a" stroke-width="1.8"/>'
        '<rect x="92" y="160" width="496" height="4" rx="2" fill="#f5ead9" opacity="0.8"/>'
    )


def _sliders(first, second):
    """滑块位置按厘米换算成示意像素；两侧距离相同就画左右对称。"""
    parts = []
    if first is None:
        return parts
    if second is None:
        offsets = (-float(first), float(first))
        labels = (_distance_label(first), _distance_label(first))
    else:
        offsets = (-float(first), float(second))
        labels = (_distance_label(first), _distance_label(second))
    for offset, label in zip(offsets, labels):
        x = _CENTER + offset * _SCALE
        parts.append(
            f'<rect x="{x - 11:.1f}" y="150" width="22" height="32" rx="7" '
            'fill="#b85c38" stroke="#8a3f24" stroke-width="1.4"/>')
        parts.append(
            f'<line x1="{_CENTER}" y1="{_BASE_Y - 8:.0f}" x2="{x:.1f}" '
            f'y2="{_BASE_Y - 8:.0f}" stroke="#b85c38" stroke-width="1.4" '
            'stroke-dasharray="5 4" marker-end="url(#arrow)"/>')
        parts.append(_label((_CENTER + x) / 2, _BASE_Y + 12,
                            f"d = {label}" if offset > 0 else f"d = {label}",
                            11, "#b85c38", "middle", "600"))
    return "".join(parts)


def _label(x, y, text, size=12, color="#3d4a46", anchor="start", weight="400"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'fill="{color}" font-weight="{weight}">{escape(text)}</text>')


def apparatus_svg(assembly, distance_cm=None, distance2_cm=None,
                  task_title="", measured=False):
    """返回当前任务的仪器示意图 HTML。没有测量时也画出来，帮助学生认对象。"""
    assembly = assembly or "carrier"
    name = ASSEMBLIES.get(assembly, "扭摆")
    parts = [
        '<div class="apparatus-wrap">',
        '<svg class="apparatus-svg" viewBox="0 0 680 292" role="img" '
        f'aria-label="扭摆装置示意图：{escape(name)}">',
        '<defs>'
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#b85c38"/></marker>'
        '<linearGradient id="wire" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#6b7c85"/><stop offset="1" stop-color="#9aa8ae"/>'
        '</linearGradient>'
        '</defs>',
        # 底座、支架、转轴
        f'<rect x="48" y="{_BASE_Y}" width="584" height="24" rx="10" fill="#d8c9b6" '
        'stroke="#b8a691" stroke-width="1.5"/>',
        f'<rect x="66" y="{_BASE_Y + 6}" width="548" height="5" rx="2.5" fill="#efe3d3"/>',
        '<line x1="340" y1="26" x2="340" y2="152" stroke="#c9d3d7" stroke-width="1.4" '
        'stroke-dasharray="6 5"/>',
        '<rect x="298" y="12" width="84" height="13" rx="6" fill="#3d4a46"/>',
        '<path d="M340 25 L340 68 L332 74 L348 80 L332 86 L348 92 L332 98 L340 104 L340 112" '
        'fill="none" stroke="url(#wire)" stroke-width="3" stroke-linejoin="round"/>',
        _label(352, 70, "扭簧", 12, "#5c564e", "start", "500"),
        _label(346, 34, "转轴", 11, "#5c564e", "start", "500"),
        # 摆角提示
        '<path d="M 340 160 A 58 58 0 0 1 398 160" fill="none" stroke="#1f6f6a" '
        'stroke-width="1.6" stroke-dasharray="4 4"/>',
        _label(414, 130, "摆角 60°", 11, "#1f6f6a", "start", "600"),
    ]
    parts.append(_object_svg(assembly, measured))
    if assembly == "rod_sliders":
        parts.append(_sliders(distance_cm, distance2_cm))
    parts.append(
        '<line x1="92" y1="160" x2="588" y2="160" stroke="#e4d9cc" stroke-width="1"/>'
        if assembly in ("rod", "rod_sliders") else "")
    parts.append(
        f'<text x="66" y="284" font-size="11" fill="#7c7166">示意图，不按真实比例。'
        f'当前对象：{escape(name)}；摆角固定 60°。</text>')
    parts.append("</svg></div>")
    return "".join(parts)


def progress_html(measured, total, checks, judged, explained, concluded, task_title=""):
    """本题进度条：测量、核对、三个记录框。"""
    total = max(1, int(total))
    measured = max(0, min(int(measured), total))
    percent = int(round(100 * measured / total))
    dots = [
        ("判断", judged), ("过程", explained), ("结论", concluded),
    ]
    dot_html = "".join(
        f'<span class="p-dot {"on" if done else ""}">{label}{"✓" if done else "○"}</span>'
        for label, done in dots)
    return (
        '<div class="progress-card">'
        f'<div class="p-head"><strong>{escape(task_title or "本题进度")}</strong>'
        f'<span class="p-count">已测 {measured}/{total} · 已核对 {int(checks)} 次</span></div>'
        f'<div class="p-bar"><span style="width:{percent}%"></span></div>'
        f'<div class="p-dots">{dot_html}</div>'
        '</div>')
