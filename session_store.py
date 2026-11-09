"""单用户记录：按学号与开始时间归档；内存数组不写入 JSON。"""
import hashlib
import json
import re
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


def save_session(session):
    session["updated_at"] = now()
    path = session["_path"]
    data = {k: v for k, v in session.items() if not k.startswith("_")}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        temp.replace(path)
        session["_save_status"] = "已保存"
    except (OSError, ValueError):
        session["_save_status"] = "保存失败：记录仍在内存，请检查目录权限或磁盘后重试。"


def append_event(session, event_type, source, **content):
    event = dict(timestamp=now(), task_id=session["task_id"], stage=session["stage"],
                 type=event_type, source=source, **content)
    session["records"].append(event)
    save_session(session)
    return event
