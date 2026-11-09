"""把当前实验记录整理成 Word 报告：参数、数据表、结果和两张图。

只读 session 里的 experiment 状态，不调用模型，也不写入隐藏真值。
讨论与结论留空给学自己写，程序不替学生下结论。
"""
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import charts
import experiment
import stages
import uncertainty

INK = RGBColor(0x1B, 0x3A, 0x4B)


def _east_asia(run, name):
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), name)


def _setup(document):
    section = document.sections[0]
    section.top_margin = Cm(2.4)
    section.bottom_margin = Cm(2.4)
    section.left_margin = Cm(2.6)
    section.right_margin = Cm(2.6)
    normal = document.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    rpr = normal.element.get_or_add_rPr()
    rpr.get_or_add_rFonts().set(qn("w:eastAsia"), "宋体")


def _title(document, text):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.name = "Times New Roman"
    run.font.color.rgb = INK
    _east_asia(run, "黑体")


def _center_line(document, text, size=10.5):
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.font.size = Pt(size)
    run.font.name = "Times New Roman"
    _east_asia(run, "宋体")


def _heading(document, text, level=1):
    paragraph = document.add_heading(level=level)
    run = paragraph.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(14 if level == 1 else 11.5)
    run.font.bold = True
    run.font.color.rgb = INK
    _east_asia(run, "黑体")


def _paragraph(document, text, bold=False, indent=True):
    paragraph = document.add_paragraph()
    if indent:
        paragraph.paragraph_format.first_line_indent = Pt(21)
    run = paragraph.add_run(text)
    run.font.bold = bold
    run.font.name = "Times New Roman"
    _east_asia(run, "宋体")
    return paragraph


def _bullets(document, lines):
    for line in lines:
        paragraph = document.add_paragraph(style="List Bullet")
        run = paragraph.add_run(line)
        run.font.name = "Times New Roman"
        _east_asia(run, "宋体")


def _table(document, headers, rows):
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, headers):
        cell.text = str(text)
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9)
                _east_asia(run, "黑体")
    for row in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = "—" if text is None or text == "" else str(text)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)
                    _east_asia(run, "宋体")
    # 表头跨页重复，行内不拆页。
    header_tr = table.rows[0]._tr
    header_pr = header_tr.get_or_add_trPr()
    header_pr.append(OxmlElement("w:tblHeader"))
    for row in table.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    # 两张表紧挨着会被 Word 合并显示，加一个空段落隔开。
    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    return table


def _fmt(value, u=None, unit=""):
    if value is None:
        return "—"
    if u is None:
        return f"{float(value):.6g} {unit}".strip()
    text, _ = uncertainty.format_result(float(value), float(u), unit)
    return text


def _total(times):
    values = [float(value) for value in times or []]
    return sum(values) / len(values) if values else None


def _short(value):
    """讨论里的数用短写法：小于 0.01 用科学计数法，其余保留 4 位有效数字。"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value if value not in (None, "") else "—"
    return f"{number:.3e}" if number and abs(number) < 0.01 else f"{number:.4g}"


def _group_rows(state, mode):
    rows = []
    index = 0
    for group in stages.groups_for(state, mode, "calibrate"):
        if group.get("superseded"):
            continue
        index += 1
        n = int(group.get("n_periods") or 0)
        t0 = _total(group.get("t0"))
        t1 = _total(group.get("t1"))
        rows.append([f"第 {index} 组", n, f"{t0:.3f}" if t0 else "—",
                     f"{t1:.3f}" if t1 else "—",
                     f"{t0 / n:.4f}" if t0 and n else "—",
                     f"{t1 / n:.4f}" if t1 and n else "—",
                     group.get("param_label") or "—"])
    return rows


def _times_rows(state, mode, stage_key):
    """阶段2/3 的每组的条件、总时间和周期，供附录誊抄。作废组不写入报告。"""
    rows = []
    labels = stages.SHAPE_LABELS if stage_key == "shapes" else stages.PARALLEL_LABELS
    index = 0
    for group in stages.groups_for(state, mode, stage_key):
        if group.get("superseded"):
            continue
        index += 1
        n = int(group.get("n_periods") or 0)
        total = _total(group.get("times"))
        rows.append([
            f"第 {index} 组",
            labels.get(group.get("condition"), group.get("condition") or "—"),
            n,
            f"{total:.3f}" if total else "—",
            f"{total / n:.4f}" if total and n else "—",
            group.get("param_label") or "—",
        ])
    return rows


def _shape_rows(state, mode, params):
    rows = []
    results = stages.stage(state, mode, "shapes")["results"]
    for condition in stages.SHAPE_CONDITIONS:
        student = results.get(condition) or {}
        try:
            estimate = stages.shape_estimate(state, mode, condition, params)
        except ValueError:
            estimate = None
        rows.append([
            stages.SHAPE_LABELS[condition],
            student.get("Iexp", ""), student.get("Igeo", ""), student.get("E", ""),
            _fmt(estimate["inertia"]["value"], estimate["inertia"]["u"])
            if estimate else "—",
            _fmt(estimate["geometric"]["value"], estimate["geometric"]["u"])
            if estimate else "—",
            f"{estimate['error']['value']:.2f}" if estimate else "—",
        ])
    return rows


def _parallel_rows(state, mode, params):
    rows = []
    results = stages.stage(state, mode, "parallel")["results"]
    total = results.get("I_total") or {}
    for condition, label in stages.parallel_conditions():
        try:
            estimate = stages.parallel_estimate(state, mode, condition, params)
        except ValueError:
            estimate = None
        rows.append([label, total.get(condition, ""),
                     _fmt(estimate["total"]["value"], estimate["total"]["u"])
                     if estimate else "—"])
    return rows


def _fit_rows(results):
    symmetric, asymmetric = stages.student_points(results)
    rows = []
    for name, points in (("对称", symmetric), ("不对称", asymmetric)):
        fit = None
        if len(points) >= 3:
            fit = uncertainty.regression([item[0] for item in points],
                                         [item[1] for item in points])
        rows.append([name,
                     results.get("slope_sym" if name == "对称" else "slope_asym", ""),
                     f"{fit['slope']:.4g}" if fit else f"点数不足（{len(points)}）",
                     results.get("intercept_sym" if name == "对称" else "intercept_asym", ""),
                     f"{fit['intercept']:.4g}" if fit else "—"])
    return rows


def _add_figure(document, figure, caption, tmp_dir):
    if figure is None:
        return
    path = Path(tmp_dir) / f"fig_{len(document.inline_shapes)}.png"
    figure.savefig(path, dpi=190, bbox_inches="tight")
    document.add_picture(str(path), width=Cm(15.5))
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _center_line(document, caption, size=9)


def build(path, state, mode, tmp_dir):
    """写出一份 .docx。tmp_dir 用来暂存图片。"""
    params = experiment.active_param(state, mode)
    data = stages.ensure_stages(state, mode)
    calibration = data["calibrate"]
    shapes = data["shapes"]
    parallel = data["parallel"]

    document = Document()
    _setup(document)
    _title(document, "扭摆法测转动惯量实验报告")
    _center_line(document, "姓名：____________　班级：____________　日期：____________", 11)
    _center_line(document, f"模式：{experiment.MODE_LABELS.get(mode, mode)}　"
                           f"参数版本：{(params or {}).get('label') or '—'}　"
                           f"生成时间：{datetime.now():%Y-%m-%d %H:%M}", 9.5)

    _heading(document, "一、实验目的")
    _bullets(document, [
        "用扭摆法测定塑料圆柱、金属圆筒、实心球体和金属细杆绕给定轴的转动惯量。",
        "由已知转动惯量的圆柱标定扭转常数 K 和载物盘转动惯量 I₀。",
        "用平行轴定理检验细杆加滑块的转动惯量，并练习 A/B 类不确定度与有效数字。",
    ])

    _heading(document, "二、仪器与器材")
    settings = (params or {}).get("settings") or {}
    _table(document, ["设置", "值"], [
        [label, f"{settings.get(key, '—')} {unit}".strip()]
        for key, label, unit, _example, _info in experiment.SETTING_FIELDS])
    object_rows = []
    objects = (params or {}).get("objects") or {}
    for object_key, name, fields in experiment.OBJECT_FIELDS:
        payload = objects.get(object_key) or {}
        for field_key, label, unit, _example, _info in fields:
            values = payload.get(field_key) or []
            decimals = 1 if field_key == "mass" else 2
            object_rows.append([
                name, f"{label} / {unit}",
                "、".join(f"{float(value):.{decimals}f}" for value in values)
                if values else "未填",
            ])
    _table(document, ["物体", "量", "原始读数"], object_rows)

    _heading(document, "三、实验原理")
    for line in [
        "扭摆的周期 T = 2π√(I/K)，K 为扭转常数，I 为绕转轴的转动惯量。",
        "塑料圆柱 I₁ = ½mR²；金属圆筒 I = ½m(R外²+R内²)；实心球体 I = ⅖mR²；细杆 I = (1/12)mL²。",
        "空盘周期 T₀、加圆柱周期 T₁：K = 4π²I₁/(T₁²−T₀²)，I₀ = I₁T₀²/(T₁²−T₀²)。",
        "放在载物盘上的物体：I实 = KT²/(4π²) − I₀；细杆换下载物盘，不减 I₀。",
        "百分偏差 E = (I实 − I几)/I几 × 100%。",
        "不确定度：uA = s/√n，uB = Δ/√3，uc = √(uA²+uB²)；程序统一给出合成标准不确定度 uc（k=1）。",
    ]:
        _paragraph(document, line)

    _heading(document, "四、实验步骤")
    _bullets(document, [
        "阶段0 登记器材质量、直径和测量设置；每个量可多次读数取平均。",
        "阶段1 分别测空盘和加圆柱 N 个周期的总时间，多组重复，求 T₀、T₁。",
        "阶段2 依次放上圆筒、球体和细杆，测周期并扣除 I₀（细杆不扣）。",
        "阶段3 细杆加两侧滑块，改变距离 d 测周期，作 I–d² 图并比较斜率与截距。",
        "阶段4 汇总数据、作图并写出结论。",
    ])

    _heading(document, "五、数据记录与处理")
    _heading(document, "5.1 标定", 2)
    try:
        estimate = stages.calibration_estimate(state, mode, params)
    except ValueError:
        estimate = None
    if estimate:
        _paragraph(document,
                   f"共 {estimate['groups']} 组。T₀ = "
                   f"{_fmt(estimate['T0']['value'], estimate['T0']['u'], 's')}，"
                   f"T₁ = {_fmt(estimate['T1']['value'], estimate['T1']['u'], 's')}。")
        _table(document, ["量", "学生填写", "程序计算 ± uc"], [
            ["I₁ / kg·m²", calibration["results"].get("I1", ""),
             _fmt(estimate["I1"]["value"], estimate["I1"]["u"], "kg·m²")],
            ["K / N·m/rad", calibration["results"].get("K", ""),
             _fmt(estimate["K"]["value"], estimate["K"]["u"], "N·m/rad")],
            ["I₀ / kg·m²", calibration["results"].get("I0", ""),
             _fmt(estimate["I0"]["value"], estimate["I0"]["u"], "kg·m²")],
        ])
    else:
        _paragraph(document, "还没有可用的标定组。")
    _table(document, ["组", "N", "空盘总时间 / s", "加圆柱总时间 / s",
                      "T₀ / s", "T₁ / s", "参数版本"], _group_rows(state, mode))

    _heading(document, "5.2 规则刚体", 2)
    _table(document, ["对象", "I实验（学生）/ kg·m²", "I几何（学生）/ kg·m²",
                      "E / %（学生）", "程序 I实验 ± uc / kg·m²",
                      "程序 I几何 ± uc / kg·m²", "程序 E / %"],
           _shape_rows(state, mode, params))

    _heading(document, "5.3 平行轴", 2)
    _table(document, ["条件", "I总（学生）/ kg·m²", "程序 I总 ± uc / kg·m²"],
           _parallel_rows(state, mode, params))
    _table(document, ["拟合", "学生斜率", "程序斜率", "学生截距", "程序截距"],
           _fit_rows(parallel["results"]))

    _heading(document, "六、结果与讨论")
    discussion = []
    for condition in stages.SHAPE_CONDITIONS:
        row = (shapes["results"].get(condition) or {})
        if row.get("E") not in (None, ""):
            discussion.append(
                f"{stages.SHAPE_LABELS[condition]}：百分偏差 E = {row['E']} %，"
                f"I实验 = {_short(row.get('Iexp'))} kg·m²，"
                f"I几何 = {_short(row.get('Igeo'))} kg·m²。")
    if discussion:
        _bullets(document, discussion)
    _bullets(document, [
        "误差来源：计时起止、摆角偏离简谐条件、空气阻尼、直径测量的读数分散，以及载物盘 I₀ 的扣除。",
        "圆筒与圆柱质量、外径接近，但质量分布离轴更远，转动惯量不同。",
        "平行轴部分比较斜率与 2m、截距与 I杆+2Ic 的关系，并说明不对称时横坐标为什么用 d₁²+d₂²。",
    ])
    _paragraph(document, "（讨论请结合上面的数据补充自己的分析。）")

    _heading(document, "七、结论")
    _paragraph(document, "（请结合实验数据写出自己的结论，程序不代写。）")

    _heading(document, "八、附录")
    _heading(document, "附录 A：规则刚体测量组", 2)
    _table(document, ["组", "条件", "N", "总时间 / s", "T / s", "参数版本"],
           _times_rows(state, mode, "shapes"))
    _heading(document, "附录 B：平行轴测量组", 2)
    _table(document, ["组", "条件", "N", "总时间 / s", "T / s", "参数版本"],
           _times_rows(state, mode, "parallel"))
    shape_rows = [[stages.SHAPE_LABELS[key], (shapes["results"].get(key) or {}).get("Iexp", ""),
                   (shapes["results"].get(key) or {}).get("Igeo", ""),
                   (shapes["results"].get(key) or {}).get("E", "")]
                  for key in stages.SHAPE_CONDITIONS]
    _add_figure(document,
                charts.shapes_figure(shape_rows, stages.shape_uncertainties(state, mode, params)),
                "图 1　阶段2：I实验 与 I几何 对比（误差棒为 uc）", tmp_dir)
    symmetric, asymmetric = stages.student_points(parallel["results"])
    _add_figure(document,
                charts.parallel_figure(
                    symmetric, asymmetric,
                    errors=stages.parallel_uncertainties(
                        state, mode, params, parallel["results"])),
                "图 2　阶段3：I总–距离平方（上排拟合，下排残差）", tmp_dir)

    document.save(str(path))
    return path
