"""试点模式的浏览器会话：签名 token、内存注册表、从 JSON 恢复。

单机模式不调用这里。token 只含学号和会话编号，不含密钥。
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from uuid import uuid4


TTL_SECONDS = 8 * 60 * 60
KICK_REASON = "这个学号已在另一窗口打开，本窗口已退出。"
ENDED_REASON = "上次会话已经结束，请重新开始。"
_NONCE = re.compile(r"[0-9a-f]{32}")
_STUDENT = re.compile(r"[0-9]{1,24}")


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _unb64(text):
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def load_secret(root):
    """签名密钥只留在本机 .pilot/，不进仓库、不进页面。"""
    env = os.environ.get("SESSION_SECRET", "").strip()
    if env:
        return env.encode("utf-8")
    path = Path(root) / ".pilot" / "session_secret"
    if path.is_file():
        found = path.read_text(encoding="utf-8").strip()
        if found:
            return found.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_hex(32)
    path.write_text(secret + "\n", encoding="utf-8")
    return secret.encode("utf-8")


def sign_token(payload, secret):
    body = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    digest = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
    return f"v1.{body}.{_b64(digest)}"


def read_token(token, secret):
    if not token or not isinstance(token, str):
        return None
    try:
        version, body, sig = token.split(".")
        if version != "v1":
            return None
        expected = _b64(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            return None
        data = json.loads(_unb64(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        exp = int(data.get("exp") or 0)
    except (TypeError, ValueError):
        return None
    if exp < time.time():
        return None
    nonce = data.get("nonce")
    if not isinstance(nonce, str) or not _NONCE.fullmatch(nonce):
        return None
    student_id = data.get("student_id")
    session_id = data.get("session_id")
    if student_id is not None and (not isinstance(student_id, str) or not _STUDENT.fullmatch(student_id)):
        return None
    if session_id is not None and (not isinstance(session_id, str) or not _NONCE.fullmatch(session_id)):
        return None
    data["exp"] = exp
    return data


def memory_defaults():
    """JSON 不保存下划线字段。恢复时补上界面需要的内存槽。"""
    return {
        "_save_status": "已保存",
        "_results": [],
        "_notebook": [],
        "_section": "measure",
        "_tutor_open": False,
        "_tutor_seen": 0,
        "_lab_case_id": None,
        "_ask_draft": "",
        "_reading_mode": "latest",
        "_lab_focus": None,
        "_equipment_form": None,
        "_lab_mode": "total_time",
        "_lab_value": "",
        "_lab_note": "",
        "_param_forms": {},
        "_par_show": False,
        "_summary_show": False,
        "_drafts": {},
        "_compare_ids": [],
        "_sheet_md": "",
        "_csv_path": None,
        "_docx_path": None,
        "_ask_selection": None,
        "_last_check": "",
        "_last_check_meta": None,
        "_check_case_id": None,
        "_check_quantity": None,
        "_correct_id": None,
        "_record_id": None,
    }


def hydrate_session(data, path):
    if not isinstance(data, dict):
        raise ValueError("会话文件无法读取。")
    restored = dict(data)
    restored["_path"] = Path(path)
    for key, value in memory_defaults().items():
        restored.setdefault(key, value)
    restored["_save_status"] = "已保存"
    return restored


def load_saved_session(root, student_id, session_id):
    if not student_id or not session_id:
        return None
    if not _STUDENT.fullmatch(str(student_id)) or not _NONCE.fullmatch(str(session_id)):
        return None
    folder = Path(root) / "records" / str(student_id)
    matches = sorted(folder.glob(f"session_*_{session_id}.json"))
    if not matches:
        return None
    path = matches[-1]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if data.get("student_id") != student_id or data.get("session_id") != session_id:
        return None
    return hydrate_session(data, path)


def _active_path(root, student_id):
    return Path(root) / "records" / str(student_id) / "active.json"


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def read_claim(root, student_id):
    """返回 (missing|active|ended, session_id)。没有文件时不阻止恢复。"""
    path = _active_path(root, student_id)
    if not path.is_file():
        return "missing", None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return "missing", None
    if not isinstance(data, dict):
        return "missing", None
    session_id = data.get("session_id")
    if session_id:
        return "active", session_id
    return "ended", None


def write_claim(root, student_id, session_id):
    _write_json(_active_path(root, student_id), {
        "schema_version": "1.2",
        "student_id": student_id,
        "session_id": session_id,
    })


class UserContext:
    def __init__(self, params):
        self.nonce = secrets.token_hex(16)
        self.session = None
        self.params = params
        self.dock = {"open": False, "tab": "guide"}
        self.kicked = False
        self.kick_reason = ""
        self.last_active = time.time()
        self.public_token = ""
        # 普通 Lock：Gradio 可能在不同线程推进同一个生成器，RLock 不能跨线程释放。
        self.lock = threading.Lock()


class SessionRegistry:
    def __init__(self, root, params_factory, secret=None):
        self.root = Path(root)
        self.params_factory = params_factory
        self.secret = secret if secret is not None else load_secret(self.root)
        self._lock = threading.Lock()
        self.by_nonce = {}
        self.by_student = {}

    def _new_context(self):
        return UserContext(self.params_factory())

    def _drop_idle(self, now):
        stale = [nonce for nonce, ctx in self.by_nonce.items()
                 if now - ctx.last_active > TTL_SECONDS]
        for nonce in stale:
            ctx = self.by_nonce.pop(nonce, None)
            if ctx is None or ctx.session is None:
                continue
            student_id = ctx.session.get("student_id")
            if student_id and self.by_student.get(student_id) is ctx:
                self.by_student.pop(student_id, None)

    def issue(self, ctx):
        session = ctx.session or {}
        payload = {
            "nonce": ctx.nonce,
            "student_id": session.get("student_id"),
            "session_id": session.get("session_id"),
            "exp": int(time.time()) + TTL_SECONDS,
        }
        ctx.public_token = sign_token(payload, self.secret)
        return ctx.public_token

    def touch(self, ctx):
        ctx.last_active = time.time()

    def claim(self, ctx, student_id):
        """新的开始学习占用这个学号，并让旧窗口退出。"""
        with self._lock:
            previous = self.by_student.get(student_id)
            if previous is not None and previous is not ctx:
                previous.kicked = True
                previous.kick_reason = KICK_REASON
            self.by_student[student_id] = ctx
            ctx.kicked = False
            ctx.kick_reason = ""
            session_id = (ctx.session or {}).get("session_id")
            if session_id:
                write_claim(self.root, student_id, session_id)

    def release(self, ctx):
        session = ctx.session or {}
        student_id = session.get("student_id")
        if not student_id:
            return
        with self._lock:
            if self.by_student.get(student_id) is not ctx:
                return
            self.by_student.pop(student_id, None)
            write_claim(self.root, student_id, None)

    def resolve(self, token):
        data = read_token(token, self.secret)
        now = time.time()
        with self._lock:
            self._drop_idle(now)
            found = self.by_nonce.get(data["nonce"]) if data is not None else None
            if found is not None:
                found.last_active = now
        if found is not None:
            return found
        loaded = None
        blocked = None
        if data is not None and data.get("student_id") and data.get("session_id"):
            kind, current = read_claim(self.root, data["student_id"])
            if kind == "ended":
                blocked = ENDED_REASON
            elif kind == "active" and current != data["session_id"]:
                blocked = KICK_REASON
            else:
                loaded = load_saved_session(self.root, data["student_id"], data["session_id"])
        ctx = self._new_context()
        if data is not None:
            ctx.nonce = data["nonce"]
        with self._lock:
            self._drop_idle(time.time())
            found = self.by_nonce.get(ctx.nonce)
            if found is not None:
                found.last_active = time.time()
            else:
                ctx.last_active = time.time()
                if blocked == KICK_REASON:
                    ctx.kicked = True
                    ctx.kick_reason = blocked
                elif loaded is not None:
                    student_id = loaded.get("student_id")
                    owner = self.by_student.get(student_id)
                    if owner is not None and owner is not ctx and not owner.kicked:
                        ctx.kicked = True
                        ctx.kick_reason = KICK_REASON
                    else:
                        ctx.session = loaded
                        if student_id:
                            self.by_student[student_id] = ctx
                self.issue(ctx)
                self.by_nonce[ctx.nonce] = ctx
                found = None
        if found is not None:
            return found
        return ctx
