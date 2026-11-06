"""三个实验共用教学流程，仅题目、默认参数和允许的对象不同。"""

DEFAULTS = dict(assembly="carrier", n_periods=10, distance_cm=10.0, placement="same")
TASKS = {
    "calibrate": {
        "title": "① 标定扭转常数",
        "question": "塑料圆柱放到载物盘上之后，周期会变长、变短，还是不变？扭转常数为什么不能只靠一次测量得到？",
        "focus": "用圆柱的几何转动惯量，以及空盘、空盘加圆柱两次周期的平方差求 K。工具只给计时和铭牌。",
        "observation": "比较加圆柱前后的周期。记下两次的 N、总时间和 T，用三次直径求圆柱的 I，再求 K 和载物盘的 I。圆柱高度写在铭牌上，不进入绕轴公式。",
        "inquiry": "题目问周期怎么变，以及为什么一次测量求不出 K。空盘和空盘加圆柱都要有周期才能求。不要先把 K 或 I 算给学生。学生可以先测再答。",
        "work": "周期数用 10。圆柱的几何转动惯量用质量和三次直径的平均半径，I₁ = ½mR²。高度只在铭牌上，不代入绕轴公式。K 和载物盘的 I₀ 由这两次周期的平方差求出。",
        "summary_prompt": "写明 K 和载物盘的转动惯量各用了哪两次周期。",
        "defaults": DEFAULTS.copy(),
        "assemblies": [("金属载物盘", "carrier"), ("载物盘 + 塑料圆柱", "carrier_cylinder")],
        "tools": ["measure_period", "check_calculation"],
    },
    "shapes": {
        "title": "② 几种规则刚体",
        "question": "塑料圆柱和金属圆筒的质量、外径、高度都接近。圆筒的转动惯量会和圆柱差不多，还是明显更大？原因是什么？",
        "focus": "圆筒用外半径和内半径，球体用 2/5，细杆用 1/12。实验值用任务①的 K 和本次周期，百分偏差由学生计算。",
        "observation": "分别测金属圆筒、实心球体和金属细杆。记下 N、总时间和 T。放在载物盘上的物体要减去载物盘；细杆换下了载物盘，不要再减。圆筒不要丢掉内半径。和几何公式比较，写出百分偏差。",
        "inquiry": "题目问质量接近时圆筒的转动惯量为什么仍和圆柱不同。圆筒、球体、细杆三种都要测。不要先把转动惯量算给学生。学生可以先测再答。",
        "work": "周期数用 10，不用改距离。圆筒同时用外半径和内半径，球体用 2/5 mR²，细杆用 1/12 mL²。圆筒和球体放在载物盘上，实验值减去 I₀。细杆换下了载物盘，不要减 I₀。百分偏差自己算。",
        "summary_prompt": "写出金属圆筒实验值与理论值的百分偏差，并说明质量接近时转动惯量仍可以差很多。",
        "defaults": dict(assembly="carrier_tube", n_periods=10, distance_cm=10.0, placement="same"),
        "assemblies": [
            ("载物盘 + 金属圆筒", "carrier_tube"),
            ("载物盘 + 实心球体", "carrier_sphere"),
            ("金属细杆", "rod"),
        ],
        "tools": ["measure_period", "check_calculation"],
    },
    "parallel": {
        "title": "③ 平行轴定理",
        "question": "两只相同滑块到转轴的距离增大一倍，它们贡献的 md² 变成原来的几倍？两侧距离不同，例如 5 cm 和 10 cm，作图时横坐标还能用同一个 d² 吗？",
        "focus": "对称放置的周期图只标点，不拟合。对称时总转动惯量含 2md²；不对称时是 md1²+md2²。斜率和截距留给学生说明。",
        "observation": "测细杆。对称放置在 5、10、15、20、25 cm 各测一次，算出各点的 I，自己对 d² 作直线并说明斜率和截距。再测 5与10、10与15、15与20、20与25，换横坐标 d1²+d2² 再拟合，比较有什么变化。",
        "inquiry": "题目问距离加倍时 md² 变成几倍，以及两侧距离不同时横坐标怎么取。细杆、五个对称距离、四组不对称放置都要测到。夹具忽略。任务①的 K 仍可引用。图里没有拟合线。学生可以先测再答。",
        "work": "周期数用 10。对称放置自己把转动惯量对 d² 作图。两侧不同时，横坐标用 d1²+d2²。周期图只画两侧相同的点，没有拟合线。",
        "summary_prompt": "说明对称放置时斜率和截距各表示什么；不对称放置改了横坐标之后，拟合有什么变化。",
        "defaults": dict(assembly="rod", n_periods=10, distance_cm=10.0, placement="same"),
        "assemblies": [("金属细杆", "rod"), ("细杆 + 两侧滑块", "rod_sliders")],
        "tools": ["measure_period", "check_calculation"],
    },
}
STAGES = {"predict": "预测", "experiment": "实验", "explain": "解释",
          "summary": "总结", "complete": "已完成"}

# 分组标题只写给学生看的测量用途。情况行的名单以 CASES 为准，页面不再另抄一份。
GROUP_NOTES = {
    "标定": "空盘和加圆柱都要测。K 和载物盘的 I₀ 用两次周期的平方差，页面不算这两个数。",
    "规则刚体": "圆筒和球体放在载物盘上，实验值减去 I₀。细杆换下了载物盘，不要减 I₀。",
    "细杆基准": "单独测金属细杆。这一行不放进周期–距离图，也不当成 d = 0。",
    "两侧对称": "这五行进入周期–距离图。图上只有点，没有拟合线。转动惯量对 d² 的图自己画。d 用厘米选择，代入公式时换成米。",
    "两侧不对称": "这四行不进入周期–距离图。横坐标用 d₁² + d₂²，不能再用同一个 d²。",
}

# 页面上的分组标题。CASES 里的 group 仍作为数据和分组键，不改。
GROUP_TITLES = {
    "标定": "① 标定：空盘与加圆柱",
    "规则刚体": "② 规则刚体：圆筒、球体、细杆",
    "细杆基准": "③ 基准：单独测细杆",
    "两侧对称": "③ 对称放置：五个距离",
    "两侧不对称": "③ 不对称放置：四组距离",
}


def _item(task_id, case_id, group, name, assembly, distance_cm, distance2_cm, placement, purpose):
    """case_id 由任务和条件组成，不用显示顺序或中文名。对称滑块的第二距离保持 None。"""
    return {
        "task_id": task_id,
        "case_id": case_id,
        "group": group,
        "name": name,
        "assembly": assembly,
        "distance_cm": distance_cm,
        "distance2_cm": distance2_cm,
        "placement": placement,
        "purpose": purpose,
    }


CASES = [
    _item("calibrate", "calibrate-carrier", "标定", "金属载物盘",
          "carrier", None, None, "same",
          "这次周期记作 T₀，用来和加上塑料圆柱后的 T₁ 做平方差。"),
    _item("calibrate", "calibrate-carrier_cylinder", "标定", "载物盘 + 塑料圆柱",
          "carrier_cylinder", None, None, "same",
          "这次周期记作 T₁。和 T₀ 的平方差一起用来求 K 和载物盘的 I₀。"),
    _item("shapes", "shapes-carrier_tube", "规则刚体", "载物盘 + 金属圆筒",
          "carrier_tube", None, None, "same",
          "圆筒放在载物盘上。几何值要同时用外半径和内半径。实验值减去 I₀。"),
    _item("shapes", "shapes-carrier_sphere", "规则刚体", "载物盘 + 实心球体",
          "carrier_sphere", None, None, "same",
          "球体放在载物盘上。几何值用 2/5 mR²。实验值减去 I₀。"),
    _item("shapes", "shapes-rod", "规则刚体", "金属细杆",
          "rod", None, None, "same",
          "细杆换下了载物盘。几何值用 1/12 mL²。实验值不要减 I₀。"),
    _item("parallel", "parallel-rod", "细杆基准", "金属细杆",
          "rod", None, None, "same",
          "细杆单独测量，作为基准。不放进周期–距离图，也不当成 d = 0。"),
    _item("parallel", "parallel-sym-5", "两侧对称", "两侧相同，d = 5 cm",
          "rod_sliders", 5.0, None, "same",
          "两侧都在 5 cm。周期–距离图收这个点。作转动惯量图时横坐标用这个 d²。"),
    _item("parallel", "parallel-sym-10", "两侧对称", "两侧相同，d = 10 cm",
          "rod_sliders", 10.0, None, "same",
          "两侧都在 10 cm。周期–距离图收这个点。作转动惯量图时横坐标用这个 d²。"),
    _item("parallel", "parallel-sym-15", "两侧对称", "两侧相同，d = 15 cm",
          "rod_sliders", 15.0, None, "same",
          "两侧都在 15 cm。周期–距离图收这个点。作转动惯量图时横坐标用这个 d²。"),
    _item("parallel", "parallel-sym-20", "两侧对称", "两侧相同，d = 20 cm",
          "rod_sliders", 20.0, None, "same",
          "两侧都在 20 cm。周期–距离图收这个点。作转动惯量图时横坐标用这个 d²。"),
    _item("parallel", "parallel-sym-25", "两侧对称", "两侧相同，d = 25 cm",
          "rod_sliders", 25.0, None, "same",
          "两侧都在 25 cm。周期–距离图收这个点。作转动惯量图时横坐标用这个 d²。"),
    _item("parallel", "parallel-asym-5-10", "两侧不对称", "一侧 5 cm，另一侧 10 cm",
          "rod_sliders", 5.0, 10.0, "5-10",
          "一侧 5 cm，另一侧 10 cm。不进周期–距离图。横坐标用 d₁² + d₂²。"),
    _item("parallel", "parallel-asym-10-15", "两侧不对称", "一侧 10 cm，另一侧 15 cm",
          "rod_sliders", 10.0, 15.0, "10-15",
          "一侧 10 cm，另一侧 15 cm。不进周期–距离图。横坐标用 d₁² + d₂²。"),
    _item("parallel", "parallel-asym-15-20", "两侧不对称", "一侧 15 cm，另一侧 20 cm",
          "rod_sliders", 15.0, 20.0, "15-20",
          "一侧 15 cm，另一侧 20 cm。不进周期–距离图。横坐标用 d₁² + d₂²。"),
    _item("parallel", "parallel-asym-20-25", "两侧不对称", "一侧 20 cm，另一侧 25 cm",
          "rod_sliders", 20.0, 25.0, "20-25",
          "一侧 20 cm，另一侧 25 cm。不进周期–距离图。横坐标用 d₁² + d₂²。"),
]


CHECK_BY_TASK = {
    "calibrate": ("cylinder_inertia", "torsion_constant", "carrier_inertia"),
    "shapes": ("tube_inertia", "sphere_inertia", "rod_inertia", "torsion_constant", "carrier_inertia"),
    "parallel": ("rod_inertia", "sliders_total_inertia", "torsion_constant", "carrier_inertia"),
}


def get_task_cases(task_id):
    """当前任务的情况，顺序与实验要求一致。"""
    return [dict(item) for item in CASES if item["task_id"] == task_id]


def case_by_id(task_id, case_id):
    for item in CASES:
        if item["task_id"] == task_id and item["case_id"] == case_id:
            return dict(item)
    return None


def case_check_label(case):
    """核对滑块时展示的距离。这句和提交给后端的距离是同一条情况。"""
    if case["distance2_cm"] is None:
        distance = case["distance_cm"]
        return f"对称 d = {distance:g} cm"
    return f"左 {case['distance_cm']:g} cm、右 {case['distance2_cm']:g} cm"


def _same_distance(got, want):
    if want is None:
        return got is None
    if got is None:
        return False
    return abs(float(got) - float(want)) < 1e-6


def _hits(notebook, assembly, first, second):
    found = []
    for item in notebook or []:
        params = item["params"]
        if params.get("assembly") != assembly:
            continue
        if not _same_distance(params.get("distance_cm"), first):
            continue
        if not _same_distance(params.get("distance2_cm"), second):
            continue
        found.append(item)
    return found


def match_case(summaries, case):
    """按对象和两侧距离匹配。细杆在任务②和③是同一种测量，周期共用。"""
    return _hits(summaries, case["assembly"], case["distance_cm"], case["distance2_cm"])


def task_guide(task_id, notebook=None):
    """题目、要测的每一种情况，以及算什么。已测的标出周期。"""
    task = TASKS[task_id]
    lines = [f"**{task['title']}**", "", task["question"], "", "**要测的情况**", ""]
    group = None
    for case in get_task_cases(task_id):
        if case["group"] != group:
            group = case["group"]
            lines.extend(["", f"**{group}**", GROUP_NOTES[group], ""])
        hits = match_case(notebook, case)
        if hits:
            extra = f"（{len(hits)} 次）" if len(hits) > 1 else ""
            lines.append(f"- {case['name']} — 已测，T = {hits[-1]['period_s']:.4f} s{extra}")
        else:
            lines.append(f"- {case['name']} — 未测")
        lines.append(f"  {case['purpose']}")
    lines.extend(["", task["work"]])
    return "\n".join(lines)


def formula_md(task_id):
    """当前任务摊在页面上的公式。铭牌数字仍来自知识库，这里不写仪器真值。"""
    if task_id == "calibrate":
        return "\n".join([
            "### 这一题用到的公式",
            "",
            "#### 塑料圆柱的几何转动惯量",
            "",
            r"$$I_1 = \frac{1}{2} m R^2.$$",
            "",
            "R 用三次直径的平均值。铭牌上的高度不代入绕轴公式。",
            "",
            "#### 扭转常数与载物盘转动惯量",
            "",
            r"$$K = \frac{4\pi^2 I_1}{T_1^2 - T_0^2}, \qquad I_0 = \frac{I_1 T_0^2}{T_1^2 - T_0^2}.$$",
            "",
            "求别的物体的实验转动惯量时要用这里的 K。还没有 T₀、T₁ 时，回到上面两行测量。测量不会因为还没写出 K 而被锁住。",
        ])
    if task_id == "shapes":
        return "\n".join([
            "### 这一题用到的公式",
            "",
            "#### 放在载物盘上的实验转动惯量",
            "",
            r"$$I_{\text{实}} = \frac{K T^2}{4\pi^2} - I_0.$$",
            "",
            "圆筒和球体放在载物盘上，实验值减去 I₀。",
            "",
            "#### 细杆的实验转动惯量",
            "",
            r"$$I_{\text{实}} = \frac{K T^2}{4\pi^2}.$$",
            "",
            "金属细杆换下了载物盘，不要再减 I₀。",
            "",
            "#### 几何值与百分偏差",
            "",
            r"圆筒：\(I = \tfrac12 m (R_{\text{外}}^2 + R_{\text{内}}^2)\)；球体：\(I = \tfrac25 mR^2\)；细杆：\(I = \tfrac{1}{12} mL^2\)。",
            "",
            r"$$E = \frac{I_{\text{实}} - I_{\text{理}}}{I_{\text{理}}} \times 100\%.$$",
            "",
            "g、mm、cm 先换成 kg、m。百分偏差自己算。",
        ])
    return "\n".join([
        "### 这一题用到的公式",
        "",
        "#### 滑块绕自身质心",
        "",
        r"\(I_c = \tfrac12 m r^2\)。d 在页面上用厘米，代入时用米。",
        "",
        "#### 两侧距离相同",
        "",
        r"$$I = I_{\text{杆}} + 2 I_c + 2 m d^2.$$",
        "",
        "#### 两侧距离不同",
        "",
        r"$$I = I_{\text{杆}} + 2 I_c + m d_1^2 + m d_2^2.$$",
        "",
        "对称的五个距离进入下面的周期–距离图，只有点，没有拟合线。不对称的四组和单独的细杆都不进这张图。转动惯量对 d² 或 d₁² + d₂² 的图自己画。斜率和截距自己说明。",
    ])


FORMULAS = {
    "calibrate": [
        {"formula_id": "cylinder-geometry", "title": "塑料圆柱的几何转动惯量",
         "text": "I₁ = ½ m R²。R 用三次直径的平均值。高度不代入绕轴公式。"},
        {"formula_id": "k-and-i0", "title": "扭转常数与载物盘转动惯量",
         "text": "K = 4π² I₁ / (T₁² − T₀²)，I₀ = I₁ T₀² / (T₁² − T₀²)。"},
    ],
    "shapes": [
        {"formula_id": "experimental-on-plate", "title": "放在载物盘上的实验转动惯量",
         "text": "I实 = K T² / 4π² − I₀。圆筒和球体用这一式。"},
        {"formula_id": "experimental-rod", "title": "细杆的实验转动惯量",
         "text": "I实 = K T² / 4π²。细杆换下了载物盘，不要再减 I₀。"},
        {"formula_id": "percent-error", "title": "百分偏差",
         "text": "E = (I实 − I理) / I理 × 100%。百分偏差自己算。"},
    ],
    "parallel": [
        {"formula_id": "slider-center", "title": "滑块绕自身质心",
         "text": "I_c = ½ m r²。d 在页面上用厘米，代入时用米。"},
        {"formula_id": "symmetric-i", "title": "两侧距离相同",
         "text": "I = I杆 + 2 I_c + 2 m d²。"},
        {"formula_id": "asymmetric-i", "title": "两侧距离不同",
         "text": "I = I杆 + 2 I_c + m d₁² + m d₂²。"},
    ],
}


def formulas_for(task_id):
    return [dict(item) for item in FORMULAS.get(task_id) or []]


def blank_sheet(task_id):
    """空白记录表：只列这一题的情况和列名，不写任何读数或计算结果。"""
    lines = [
        "| 组 | 情况 | 位置 | N | 总时间 / s | 周期 T / s | 备注 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in get_task_cases(task_id):
        if case["distance_cm"] is None:
            where = "—"
        elif case["distance2_cm"] is None:
            where = f"两侧 {case['distance_cm']:g} cm"
        else:
            where = f"{case['distance_cm']:g} / {case['distance2_cm']:g} cm"
        lines.append(
            f"| {GROUP_TITLES.get(case['group'], case['group'])} | {case['name']} | "
            f"{where} |  |  |  |  |")
    return "\n".join(lines)


def formula_by_id(task_id, formula_id):
    for item in FORMULAS.get(task_id) or []:
        if item["formula_id"] == formula_id:
            return dict(item)
    return None


def visible_question(task_id, active=True):
    """页首只放这一题的物理问题和一句目标。情况行另有可点的测量。"""
    task = TASKS[task_id]
    text = f"**{task['title']}**\n\n{task['question']}\n\n{task['focus']}"
    if not active and task_id == "calibrate":
        text += "\n\n这道题要用空盘和加上圆柱后的周期，标定扭转常数。填学号，点「开始学习」；随后可先测任一情况。"
    elif not active:
        text += "\n\n填写学号，点「开始学习」。写不写判断都可以先测量。"
    return text


def stage_prompt(task_id, stage=None, notebook=None):
    """给模型和界面的同一份说明。阶段不改变题目和要测的情况。"""
    return task_guide(task_id, notebook)
