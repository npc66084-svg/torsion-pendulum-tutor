"""试点多会话：隔离、刷新恢复、重复登录、课程码和名单。不请求真实模型。"""
import os
import shutil
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import app
import pilot_ai
import pilot_auth
import ui
from session_registry import KICK_REASON


ROOT = Path(__file__).resolve().parents[1]
COURSE_CODE = "pilot-test-code"
ROSTER_IDS = (
    "10001", "10002", "10003", "20002", "30003", "30004", "40004",
    "50001", "50002", "50003", "000000",
)


def write_roster(path, student_ids, pins=None):
    pins = pins or {}
    lines = ["student_id,name,pin"]
    for student_id in student_ids:
        lines.append(f"{student_id},示例,{pins.get(student_id, '')}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    for rel in ("SKILL.md", "tasks.py", "knowledge/torsion_pendulum.md"):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dest)
    saved = (app.session, app.params.copy(), dict(app.DOCK), app.PROJECT)
    monkeypatch.setattr(app, "PROJECT", root)
    monkeypatch.setenv("PILOT_MODE", "1")
    monkeypatch.setenv("COURSE_CODE", COURSE_CODE)
    roster = root / "roster.csv"
    write_roster(roster, ROSTER_IDS)
    monkeypatch.setenv("ROSTER_FILE", str(roster))
    app.session = None
    app.params.clear()
    app.params.update(app.DEFAULTS)
    app.DOCK["open"] = False
    app.DOCK["tab"] = "guide"
    app.reset_registry()
    pilot_auth.reset()
    pilot_ai.reset()
    yield root
    app.session = saved[0]
    app.params.clear()
    app.params.update(saved[1])
    app.DOCK.clear()
    app.DOCK.update(saved[2])
    monkeypatch.setattr(app, "PROJECT", saved[3])
    app.reset_registry()
    pilot_auth.reset()
    pilot_ai.reset()


def drive(action, student_id, token="", send_token=True, course_code=None, pin="", **kwargs):
    args = (action, student_id, "calibrate", None, 10, 0, "")
    if send_token:
        if course_code is None:
            course_code = os.environ.get("COURSE_CODE", "")
        views = list(app.handle(
            *args, session_token=token, course_code=course_code, pin=pin, **kwargs))
    else:
        views = list(app.handle(*args, **kwargs))
    return views[-1]


def fill_stage1(student_id, token, note):
    """阶段0 保存一版参数，再在阶段1 添加一组标定并填写 I₁、K、I₀。"""
    drive("save_param", student_id, token,
          p_n="10", p_angle="60", p_timer="0.001", p_balance="0.1",
          p_caliper="0.02", p_ruler="1.0",
          p_cylinder_mass="620.0", p_cylinder_diameter="100.00",
          p_tube_mass="620.0", p_tube_outer="100.00", p_tube_inner="90.00",
          p_sphere_mass="550.0", p_sphere_diameter="90.00",
          p_rod_mass="168.0", p_rod_length="500.0",
          p_slider_mass="240.0", p_slider_diameter="30.00",
          p_note=note)
    drive("set_exp_stage", student_id, token, exp_stage_choice="calibrate")
    return drive(
        "add_cal_group", student_id, token,
        cal_n="10", cal_t0="12.50", cal_t1="13.50", cal_note=note,
        cal_i1="1.25e-4", cal_k="0.021", cal_i0="3.4e-4")


def test_three_students_keep_stage1_apart(project):
    tokens = {}
    for student_id in ("10001", "10002", "10003"):
        started = drive("start", student_id)
        assert started["active"] and student_id in started["save_line"]
        token = started["session_token"]
        note = f"only-{student_id}"
        filled = fill_stage1(student_id, token, note)
        assert note in filled["cal_groups_md"]
        assert note in filled["param_active_md"] or note in filled["param_preview_md"]
        assert filled["cal_i1"] == "1.25e-4"
        assert filled["exp_stage"] == "calibrate"
        tokens[student_id] = filled["session_token"]

    for student_id, token in tokens.items():
        view = drive("set_exp_stage", student_id, token, exp_stage_choice="calibrate")
        assert f"only-{student_id}" in view["cal_groups_md"]
        for other in tokens:
            if other != student_id:
                assert f"only-{other}" not in view["cal_groups_md"]
        saved = list((project / "records" / student_id).glob("session_*.json"))
        assert len(saved) == 1
        text = saved[0].read_text(encoding="utf-8")
        assert f"only-{student_id}" in text
        for other in tokens:
            if other != student_id:
                assert f"only-{other}" not in text


def test_refresh_restores_after_registry_loss(project):
    started = drive("start", "20002")
    token = started["session_token"]
    saved = fill_stage1("20002", token, "keep-me")
    token = saved["session_token"]
    app.reset_registry()
    restored = drive("open_guide", "20002", token)
    assert restored["active"]
    assert "20002" in restored["save_line"]
    assert restored["exp_stage"] == "calibrate"
    assert "keep-me" in restored["cal_groups_md"]
    assert restored["cal_i1"] == "1.25e-4"
    assert restored["tutor_open"] and restored["dock_tab"] == "guide"


def test_group_without_param_version_does_not_crash(project):
    """有标定组但还没保存参数版本时，预览应提示而不是抛 AttributeError。"""
    started = drive("start", "10001")
    token = started["session_token"]
    drive("set_exp_stage", "10001", token, exp_stage_choice="calibrate")
    added = drive("add_cal_group", "10001", token,
                  cal_n="10", cal_t0="12.50", cal_t1="13.50", cal_note="no-param")
    assert "no-param" in added["cal_groups_md"]
    assert "先保存一个参数版本" in added["cal_preview_md"]
    restored = drive("open_guide", "10001", token)
    assert restored["active"]
    assert "先保存一个参数版本" in restored["cal_preview_md"]


def test_second_window_kicks_the_first(project):
    first = drive("start", "30003")
    first_token = first["session_token"]
    drive("set_exp_stage", "30003", first_token, exp_stage_choice="calibrate")
    second = drive("start", "30003")
    assert second["active"] and "30003" in second["save_line"]
    assert second["session_token"] != first_token
    kicked = drive("set_exp_stage", "30003", first_token, exp_stage_choice="shapes")
    assert KICK_REASON in kicked["status"]
    assert not kicked["active"]
    still = drive("set_exp_stage", "30003", second["session_token"], exp_stage_choice="shapes")
    assert still["active"] and still["exp_stage"] == "shapes"


def test_kick_survives_registry_restart(project):
    first = drive("start", "30004")
    second = drive("start", "30004")
    app.reset_registry()
    kicked = drive("open_guide", "30004", first["session_token"])
    assert KICK_REASON in kicked["status"] and not kicked["active"]
    kept = drive("open_guide", "30004", second["session_token"])
    assert kept["active"] and "30004" in kept["save_line"]


def test_forged_token_cannot_open_another_student(project):
    started = drive("start", "40004")
    token = started["session_token"]
    forged = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    view = drive("set_exp_stage", "40004", forged, exp_stage_choice="calibrate")
    assert not view["active"]
    assert "请先" in view["status"]
    real = drive("open_guide", "40004", token)
    assert real["active"] and "40004" in real["save_line"]


def test_bad_student_id_is_rejected(project):
    view = drive("start", "../40004")
    assert not view["active"]
    assert "学号" in view["status"]
    assert not (project / "records").exists() or not any((project / "records").rglob("session_*.json"))


def test_parallel_starts_do_not_cross(project):
    errors = []
    done = {}

    def worker(student_id):
        try:
            started = drive("start", student_id)
            token = started["session_token"]
            done[student_id] = fill_stage1(student_id, token, f"thread-{student_id}")
        except Exception as exc:
            errors.append((student_id, exc))

    threads = [threading.Thread(target=worker, args=(student_id,))
               for student_id in ("50001", "50002", "50003")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    for student_id, view in done.items():
        assert f"thread-{student_id}" in view["cal_groups_md"]
        for other in done:
            if other != student_id:
                assert f"thread-{other}" not in view["cal_groups_md"]


def test_omitted_token_stays_on_single_slot_even_in_pilot_mode(project):
    first = drive("start", "60006", send_token=False)
    assert first["active"] and "session_token" not in first
    assert app.session["student_id"] == "60006"
    kept = app.session
    again = drive("start", "60007", send_token=False)
    assert "已有学习会话" in again["status"]
    assert app.session is kept
    assert app.session["student_id"] == "60006"


def test_launch_defaults_and_pilot_switch(monkeypatch):
    queue_calls = []
    launch_calls = []
    build_calls = []

    class Demo:
        def close(self):
            return None

        def queue(self, **kwargs):
            queue_calls.append(kwargs)

        def launch(self, **kwargs):
            launch_calls.append(kwargs)
            return "ok"

    def fake_build(*args, **kwargs):
        build_calls.append(kwargs)
        return Demo(), {}

    monkeypatch.setattr(ui, "build_ui", fake_build)
    app.demo = None
    monkeypatch.delenv("PILOT_MODE", raising=False)
    monkeypatch.delenv("APP_HOST", raising=False)
    monkeypatch.delenv("APP_PORT", raising=False)
    assert app.launch() == "ok"
    assert build_calls[-1]["pilot"] is False
    assert queue_calls[-1] == {"max_size": 1, "default_concurrency_limit": 1}
    assert launch_calls[-1]["server_name"] == "127.0.0.1"
    assert launch_calls[-1]["server_port"] == 7860
    assert launch_calls[-1]["share"] is False

    monkeypatch.setenv("PILOT_MODE", "1")
    monkeypatch.setenv("APP_HOST", "0.0.0.0")
    monkeypatch.setenv("APP_PORT", "7862")
    app.demo = SimpleNamespace(close=lambda: None)
    assert app.launch() == "ok"
    assert build_calls[-1]["pilot"] is True
    assert queue_calls[-1] == {"default_concurrency_limit": 8}
    assert launch_calls[-1]["server_name"] == "0.0.0.0"
    assert launch_calls[-1]["server_port"] == 7862


def test_single_ui_has_no_token_component():
    demo, controls = ui.build_ui(app.handle, app.get_view_state)
    try:
        assert "session_token" not in controls
        assert "course_code" not in controls
        assert "pin" not in controls
    finally:
        demo.close()


def test_pilot_ui_asks_for_course_code():
    demo, controls = ui.build_ui(
        app.handle, app.get_view_state, pilot=True, open_browser=app.open_browser)
    try:
        assert "session_token" in controls
        assert "course_code" in controls
        assert "pin" in controls
    finally:
        demo.close()


def test_wrong_course_code_and_missing_roster_are_rejected(project, monkeypatch):
    wrong = drive("start", "10001", course_code="not-the-code")
    assert not wrong["active"]
    assert "课程码不正确" in wrong["status"]
    assert "not-the-code" not in wrong["status"]
    assert COURSE_CODE not in wrong["status"]
    assert not (project / "records").exists() or not any((project / "records").rglob("session_*.json"))

    monkeypatch.delenv("COURSE_CODE")
    missing = drive("start", "10001", course_code="not-the-code")
    assert "没有配置课程码" in missing["status"]

    monkeypatch.setenv("COURSE_CODE", COURSE_CODE)
    monkeypatch.delenv("ROSTER_FILE")
    no_roster = drive("start", "10001")
    assert "没有配置名单" in no_roster["status"]


def test_unknown_student_and_bad_pin_are_rejected(project):
    absent = drive("start", "19999")
    assert not absent["active"]
    assert "不在本次课程名单" in absent["status"]
    assert not (project / "records" / "19999").exists()

    roster = project / "roster.csv"
    write_roster(roster, (*ROSTER_IDS, "10021"), pins={"10021": "2468"})
    blank = drive("start", "10021", pin="")
    assert "请填写个人识别码" in blank["status"]
    mismatch = drive("start", "10021", pin="0000")
    assert "个人识别码不正确" in mismatch["status"]
    assert "2468" not in mismatch["status"]
    assert not mismatch["active"]
    matched = drive("start", "10021", pin="2468")
    assert matched["active"] and "10021" in matched["save_line"]


def test_roster_reload_and_demo_student(project):
    roster = project / "roster.csv"
    original = roster.read_text(encoding="utf-8")
    roster.write_text(original.replace("10001,示例,\n", ""), encoding="utf-8")
    blocked = drive("start", "10001")
    assert "不在本次课程名单" in blocked["status"]
    roster.write_text(original, encoding="utf-8")
    allowed = drive("start", "10001")
    assert allowed["active"] and "10001" in allowed["save_line"]

    demo = drive("seed_demo", "19999")
    assert demo["active"] and "000000" in demo["save_line"]
    assert "19999" not in demo["save_line"]


def test_login_failures_are_rate_limited(project, monkeypatch):
    monkeypatch.setenv("LOGIN_FAILS_PER_ID", "3")
    pilot_auth.reset()
    last = None
    for _ in range(3):
        last = drive("start", "10001", course_code="nope")
    assert "尝试次数过多" in last["status"]
    blocked = drive("start", "10001")
    assert not blocked["active"]
    assert "尝试次数过多" in blocked["status"]
    assert not (project / "records" / "10001").exists()

    monkeypatch.setenv("LOGIN_FAILS_GLOBAL", "3")
    monkeypatch.setenv("LOGIN_FAILS_PER_ID", "8")
    pilot_auth.reset()
    for student_id in ("81001", "81002", "81003"):
        drive("start", student_id, course_code="nope")
    locked = drive("start", "10002")
    assert "尝试次数过多" in locked["status"] and not locked["active"]


def test_login_lock_expires(project, monkeypatch):
    monkeypatch.setenv("LOGIN_FAILS_PER_ID", "2")
    pilot_auth.reset()
    with pytest.raises(pilot_auth.AuthError, match="课程码不正确"):
        pilot_auth.authorize("10001", "nope", "", now=1_000_000)
    with pytest.raises(pilot_auth.AuthError, match="尝试次数过多"):
        pilot_auth.authorize("10001", "nope", "", now=1_000_001)
    pilot_auth.authorize("10001", COURSE_CODE, "", now=1_000_001 + 601)


def test_pilot_off_ignores_course_code(project, monkeypatch):
    monkeypatch.setenv("PILOT_MODE", "0")
    view = drive("start", "10001", send_token=False)
    assert view["active"] and "session_token" not in view
    assert app.session["student_id"] == "10001"


def test_concurrent_classes_do_not_cross_notes(project):
    """软件能做的压测：10、20、30 个学生同时开始并各存一条备注。不是教室里的浏览器。"""
    timings = []
    for count, base in ((10, 91_000_000), (20, 92_000_000), (30, 93_000_000)):
        student_ids = [str(base + index) for index in range(count)]
        write_roster(project / "roster.csv", student_ids)
        done = {}
        errors = []

        def worker(student_id):
            try:
                started = drive("start", student_id)
                if not started["active"]:
                    raise AssertionError(started["status"])
                filled = drive(
                    "save_param", student_id, started["session_token"],
                    p_n="10", p_angle="60", p_timer="0.001", p_balance="0.1",
                    p_caliper="0.02", p_ruler="1.0", p_note=f"load-{student_id}")
                done[student_id] = filled
            except Exception as exc:
                errors.append((student_id, exc))

        started_at = time.perf_counter()
        threads = [threading.Thread(target=worker, args=(student_id,)) for student_id in student_ids]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        timings.append((count, round(time.perf_counter() - started_at, 3)))
        assert errors == []
        for student_id in student_ids:
            saved = list((project / "records" / student_id).glob("session_*.json"))
            assert len(saved) == 1
            text = saved[0].read_text(encoding="utf-8")
            assert f"load-{student_id}" in text
            for other in student_ids:
                if other != student_id:
                    assert f"load-{other}" not in text
    print("LOAD_TIMINGS", timings)
