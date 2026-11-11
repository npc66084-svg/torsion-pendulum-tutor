"""试点多会话：隔离、刷新恢复、重复登录。不请求真实模型。"""
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

import app
import ui
from session_registry import KICK_REASON


ROOT = Path(__file__).resolve().parents[1]


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
    app.session = None
    app.params.clear()
    app.params.update(app.DEFAULTS)
    app.DOCK["open"] = False
    app.DOCK["tab"] = "guide"
    app.reset_registry()
    yield root
    app.session = saved[0]
    app.params.clear()
    app.params.update(saved[1])
    app.DOCK.clear()
    app.DOCK.update(saved[2])
    monkeypatch.setattr(app, "PROJECT", saved[3])
    app.reset_registry()


def drive(action, student_id, token="", send_token=True, **kwargs):
    args = (action, student_id, "calibrate", None, 10, 0, "")
    if send_token:
        views = list(app.handle(*args, session_token=token, **kwargs))
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
    finally:
        demo.close()
