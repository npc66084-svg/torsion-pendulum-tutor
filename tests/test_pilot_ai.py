"""试点 AI 线程池和限流。不请求真实模型。"""
import inspect
import threading
import time

import pytest

import app
import pilot_ai
import tutor


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(app, "PROJECT", tmp_path)
    monkeypatch.setenv("PILOT_MODE", "1")
    saved = app.session
    app.session = None
    app.reset_registry()
    pilot_ai.reset()
    yield tmp_path
    app.session = saved
    app.reset_registry()
    pilot_ai.reset()


def test_agent_defaults_stay_single_user():
    assert inspect.signature(tutor.review_agent).parameters["timeout"].default == 20
    assert inspect.signature(tutor.answer_agent).parameters["timeout"].default == 20
    assert inspect.signature(tutor.summary_agent).parameters["timeout"].default == 20
    assert inspect.signature(tutor.draft_agent).parameters["timeout"].default == 20
    assert inspect.signature(tutor.ask_agent).parameters["timeout"].default == 60
    assert inspect.signature(tutor.ask_agent).parameters["max_retries"].default == 0


def test_five_pilot_calls_overlap():
    gate = pilot_ai.Gate(workers=6)
    spans = []
    lock = threading.Lock()

    def work():
        start = time.perf_counter()
        time.sleep(0.4)
        end = time.perf_counter()
        with lock:
            spans.append((start, end))
        return "ok"

    errors = []
    moment = 1_700_000_000

    def runner(index):
        try:
            assert gate.run(f"s{index}", "review", work, now=moment) == "ok"
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=runner, args=(index,)) for index in range(5)]
    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.perf_counter() - started
    gate.shutdown()
    assert errors == []
    overlap = 0
    for index, (start, end) in enumerate(spans):
        for other_start, other_end in spans[index + 1:]:
            if min(end, other_end) - max(start, other_start) > 0.1:
                overlap += 1
    assert overlap >= 6
    assert elapsed < 1.6
    print("AI_OVERLAP", round(elapsed, 3), overlap)


def test_student_rate_and_daily_draft_cap():
    gate = pilot_ai.Gate(workers=2)
    moment = 1_700_000_000

    def ok():
        return "ok"

    try:
        for _ in range(6):
            assert gate.run("42", "review", ok, now=moment) == "ok"
        with pytest.raises(RuntimeError, match="这一分钟"):
            gate.run("42", "review", ok, now=moment)
        assert gate.run("43", "review", ok, now=moment) == "ok"
        assert gate.run("42", "review", ok, now=moment + 61) == "ok"

        for _ in range(3):
            assert gate.run("7", "summary", ok, now=moment) == "ok"
        with pytest.raises(RuntimeError, match="报告草稿"):
            gate.run("7", "draft", ok, now=moment)
        assert gate.run("7", "review", ok, now=moment + 1) == "ok"
        assert gate.run("7", "summary", ok, now=moment + 86400) == "ok"
    finally:
        gate.shutdown()


def test_pilot_call_retries_once_then_reports_failure():
    gate = pilot_ai.Gate(workers=2)
    calls = {"n": 0}
    slow_calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("down")
        return "recovered"

    def always_down():
        calls["down"] = calls.get("down", 0) + 1
        raise ConnectionError("down")

    def slow():
        slow_calls["n"] += 1
        time.sleep(0.4)
        return "late"

    try:
        assert gate.run("1", "review", flaky, now=1_700_000_000) == "recovered"
        assert calls["n"] == 2
        with pytest.raises(RuntimeError, match="失败"):
            gate.run("3", "review", always_down, now=1_700_000_050)
        assert calls["down"] == 2
        with pytest.raises(RuntimeError, match="超时"):
            gate.run("2", "review", slow, now=1_700_000_100, wait=0.1)
        time.sleep(0.5)
        assert slow_calls["n"] == 1
    finally:
        gate.shutdown()


def test_pilot_wrapper_sets_timeout_and_keeps_context(project, monkeypatch):
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "30")
    pilot_ai.reset()
    seen = {}

    def spy(**kwargs):
        seen["kwargs"] = kwargs
        seen["active"] = app._ACTIVE.get() is not None
        return "pooled"

    ctx = app.get_registry().resolve("")
    ctx.session = {"student_id": "10001"}
    marker = app._ACTIVE.set(ctx)
    try:
        assert app._ai("review", spy) == "pooled"
    finally:
        app._ACTIVE.reset(marker)
        pilot_ai.reset()
    assert seen["active"] is True
    assert seen["kwargs"]["timeout"] == 30
    assert seen["kwargs"]["max_retries"] == 1


def test_without_pilot_context_ai_stays_inline(monkeypatch):
    monkeypatch.setenv("PILOT_MODE", "0")
    seen = {}

    def spy(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return "plain"

    assert app._ai("review", spy, "a") == "plain"
    assert seen["args"] == ("a",)
    assert seen["kwargs"] == {}
