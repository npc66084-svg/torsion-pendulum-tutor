"""按学号与开始时间归档；内存数组不写入 JSON。同目录写入串行，并维护 index.json。"""
import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
from importlib.metadata import version


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")


def _versions(names):
    """装了哪些就记哪些；缺包时写“未安装”，不能因为缺包而无法开始学习。"""
    found = {}
    for name in names:
        try:
            found[name] = version(name)
        except Exception:
            found[name] = "未安装"
    return found


def create_session(student_id, root, model):
    student_id = str(student_id).strip()
    if not re.fullmatch(r"[0-9]{1,24}", student_id):
        raise ValueError("学号应为 1～24 位数字，可保留前导零。")
    started = now()
    session_id = uuid4().hex
    filename = f"session_{datetime.fromisoformat(started):%Y%m%d_%H%M%S}_{session_id}.json"
    hashes = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()[:12]
              for name in ["SKILL.md", "knowledge/torsion_pendulum.md", "tasks.py"]}
    session = dict(student_id=student_id, session_id=session_id,
                   started_at=started, updated_at=started, schema_version="1.2",
                   model=model, material_versions=hashes,
                   software=_versions(["numpy", "matplotlib", "gradio", "openai",
                                       "python-docx"]),
                   task_id="calibrate", stage="predict", prediction="", hint_count=0,
                   current_experiment_id=None, explanation_submitted=False, summary_submitted=False,
                   data_origin="virtual",
                   equipment={"version": 0, "use_nameplate": False, "fields": {}, "diameter_mode": {}},
                   records=[],
                   _path=Path(root) / "records" / student_id / filename,
                   _save_status="尚未保存", _results=[], _notebook=[],
                   _section="measure", _tutor_open=False, _tutor_seen=0,
                   _lab_case_id=None, _ask_draft="", _reading_mode="latest",
                   _lab_focus=None, _equipment_form=None, _lab_mode="total_time",
                   _lab_value="", _lab_note="")
    append_event(session, "session_start", "program")
    return session


_WRITE_LOCKS = {}
_WRITE_GUARD = threading.Lock()


def _write_lock(path):
    key = str(Path(path).parent)
    with _WRITE_GUARD:
        lock = _WRITE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _WRITE_LOCKS[key] = lock
        return lock


def _write_index(session, path):
    index = path.parent / "index.json"
    payload = {
        "schema_version": session.get("schema_version") or "1.2",
        "student_id": session.get("student_id"),
        "latest": path.name,
        "session_id": session.get("session_id"),
        "updated_at": session.get("updated_at"),
    }
    temp = index.with_name(f"index.json.{uuid4().hex}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(index)


def save_session(session):
    session["updated_at"] = now()
    path = session["_path"]
    data = {k: v for k, v in session.items() if not k.startswith("_")}
    lock = _write_lock(path)
    temp = None
    with lock:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
            temp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False),
                encoding="utf-8")
            temp.replace(path)
            try:
                _write_index(session, path)
            except OSError:
                pass
            session["_save_status"] = "已保存"
        except (OSError, ValueError):
            if temp is not None:
                try:
                    temp.unlink()
                except OSError:
                    pass
            session["_save_status"] = "保存失败：记录仍在内存，请检查目录权限或磁盘后重试。"


def append_event(session, event_type, source, **content):
    event = dict(timestamp=now(), task_id=session["task_id"], stage=session["stage"],
                 type=event_type, source=source, **content)
    session["records"].append(event)
    save_session(session)
    return event
