"""试点登录：课程码、名单、可选识别码、失败限速。只在 PILOT_MODE=1 且带浏览器 token 时使用。

不打印课程码、识别码或名单内容。
"""
import csv
import hashlib
import hmac
import io
import os
import re
import threading
import time
from pathlib import Path


class AuthError(ValueError):
    """可以显示给学生的登录拒绝。消息里没有课程码和识别码。"""


ROOT = Path(__file__).resolve().parent
WINDOW_SECONDS = 600
MAX_ROWS = 2000
_GUARD = threading.Lock()
_FAILS_BY_ID = {}
_FAILS_GLOBAL = []


def reset():
    """清空失败计数。测试使用。"""
    with _GUARD:
        _FAILS_BY_ID.clear()
        _FAILS_GLOBAL.clear()


def _positive(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _same(left, right):
    a = hashlib.sha256(str(left).encode("utf-8")).digest()
    b = hashlib.sha256(str(right).encode("utf-8")).digest()
    return hmac.compare_digest(a, b)


def _course_code():
    code = os.environ.get("COURSE_CODE", "").strip()
    if not code:
        raise AuthError("主机还没有配置课程码。")
    return code


def _roster_path():
    raw = os.environ.get("ROSTER_FILE", "").strip()
    if not raw:
        raise AuthError("主机还没有配置名单。")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise AuthError("主机还没有配置名单。")
    return path


def _read_text(path):
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AuthError("名单文件编码无法识别，请另存为 UTF-8。")


def _header_key(name):
    key = (name or "").strip().lstrip("\ufeff").lower()
    return {
        "student_id": "student_id", "学号": "student_id",
        "name": "name", "姓名": "name",
        "pin": "pin", "识别码": "pin",
    }.get(key)


def read_roster(path):
    """每次登录重读文件，教师改完名单立刻生效。同一学号只保留第一行。"""
    text = _read_text(path)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise AuthError("名单文件缺少学号列。")
    columns = {field: _header_key(field) for field in reader.fieldnames}
    if "student_id" not in columns.values():
        raise AuthError("名单文件缺少学号列。")
    rows = {}
    count = 0
    for raw in reader:
        count += 1
        if count > MAX_ROWS:
            raise AuthError("名单过长。")
        item = {}
        for field, key in columns.items():
            if key:
                item[key] = (raw.get(field) or "").strip()
        student_id = item.get("student_id") or ""
        if not student_id or student_id in rows:
            continue
        pin = item.get("pin") or ""
        if len(pin) > 64:
            pin = pin[:64]
        rows[student_id] = {"pin": pin}
    return rows


def _prune(now):
    cutoff = now - _positive("LOGIN_WINDOW_SECONDS", WINDOW_SECONDS)
    global _FAILS_GLOBAL
    _FAILS_GLOBAL = [item for item in _FAILS_GLOBAL if item >= cutoff]
    for student_id in list(_FAILS_BY_ID):
        kept = [item for item in _FAILS_BY_ID[student_id] if item >= cutoff]
        if kept:
            _FAILS_BY_ID[student_id] = kept
        else:
            _FAILS_BY_ID.pop(student_id, None)


def _locked(student_id, now):
    _prune(now)
    per_id = _positive("LOGIN_FAILS_PER_ID", 8)
    global_cap = _positive("LOGIN_FAILS_GLOBAL", 60)
    if len(_FAILS_GLOBAL) >= global_cap:
        return True
    return len(_FAILS_BY_ID.get(student_id, ())) >= per_id


def _record_failure(student_id, now):
    with _GUARD:
        _prune(now)
        _FAILS_BY_ID.setdefault(student_id, []).append(now)
        _FAILS_GLOBAL.append(now)
        return _locked(student_id, now)


def _clear_id(student_id):
    with _GUARD:
        _FAILS_BY_ID.pop(student_id, None)


def authorize(student_id, course_code, pin, now=None):
    """课程码、学号格式、名单、识别码都通过才返回。否则抛出 AuthError。"""
    expected = _course_code()
    path = _roster_path()
    roster = read_roster(path)
    moment = time.time() if now is None else float(now)
    identity = str(student_id or "").strip()[:64]
    with _GUARD:
        _prune(moment)
        locked = _locked(identity, moment)
    if locked:
        raise AuthError("尝试次数过多，请稍后再试。")
    given = str(course_code or "")
    if len(given) > 128:
        given = given[:128]
    if not given.strip():
        if _record_failure(identity, moment):
            raise AuthError("尝试次数过多，请稍后再试。")
        raise AuthError("请填写课程码。")
    if not _same(given.strip(), expected):
        if _record_failure(identity, moment):
            raise AuthError("尝试次数过多，请稍后再试。")
        raise AuthError("课程码不正确。")
    if not re.fullmatch(r"[0-9]{1,24}", identity):
        if _record_failure(identity, moment):
            raise AuthError("尝试次数过多，请稍后再试。")
        raise AuthError("学号应为 1～24 位数字，可保留前导零。")
    row = roster.get(identity)
    if row is None:
        if _record_failure(identity, moment):
            raise AuthError("尝试次数过多，请稍后再试。")
        raise AuthError("这个学号不在本次课程名单里。")
    required = row.get("pin") or ""
    supplied = str(pin or "").strip()
    if len(supplied) > 64:
        supplied = supplied[:64]
    if required:
        if not supplied:
            if _record_failure(identity, moment):
                raise AuthError("尝试次数过多，请稍后再试。")
            raise AuthError("请填写个人识别码。")
        if not _same(supplied, required):
            if _record_failure(identity, moment):
                raise AuthError("尝试次数过多，请稍后再试。")
            raise AuthError("个人识别码不正确。")
    _clear_id(identity)
