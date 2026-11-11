"""试点模式的 AI 线程池、每分钟次数和报告草稿每日上限。

单机模式不经过这里。调用方仍使用原来的函数；这里只在试点请求上包一层。
"""
import contextvars
import inspect
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo


TIMEOUT_MESSAGE = "AI 请求超时，请稍后再试。本地核对和已填数据仍在。"
FAIL_MESSAGE = "AI 请求失败，请稍后再试。本地核对和已填数据仍在。"
RATE_MESSAGE = "这一分钟的 AI 请求已经用完，请稍后再试。"
DRAFT_MESSAGE = "今天的报告草稿已经用完。本地核对和已填数据仍可使用。"
DRAFT_KINDS = {"summary", "draft"}
ZONE = ZoneInfo("Asia/Shanghai")
ASK_ROUNDS = 4  # ask_agent 最多约 MAX_CALLS+1 次 HTTP


def _positive(name, default):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _accepts(fn, name):
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    if name in params:
        return True
    return any(item.kind == inspect.Parameter.VAR_KEYWORD for item in params.values())


class Gate:
    def __init__(self, workers=6):
        self.workers = workers
        self.pool = None
        self._lock = threading.Lock()
        self._hits = {}
        self._drafts = {}

    def shutdown(self):
        with self._lock:
            pool = self.pool
            self.pool = None
            self._hits.clear()
            self._drafts.clear()
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)

    def _pool(self):
        with self._lock:
            if self.pool is None:
                self.pool = ThreadPoolExecutor(
                    max_workers=self.workers, thread_name_prefix="pilot-ai")
            return self.pool

    def admit(self, student_id, kind, now):
        """通过则记一次用量。超限抛出 RuntimeError，消息可以直接显示。"""
        identity = str(student_id or "")[:64]
        day = datetime.fromtimestamp(now, ZONE).date().isoformat()
        with self._lock:
            hits = [item for item in self._hits.get(identity, ()) if now - item < 60]
            if len(hits) >= _positive("AI_RATE_LIMIT_PER_MIN", 6):
                self._hits[identity] = hits
                raise RuntimeError(RATE_MESSAGE)
            hits.append(now)
            self._hits[identity] = hits
            drafts = {key: value for key, value in self._drafts.get(identity, {}).items() if key >= day}
            if kind in DRAFT_KINDS and drafts.get(day, 0) >= _positive("AI_DRAFT_LIMIT_PER_DAY", 3):
                self._drafts[identity] = drafts
                raise RuntimeError(DRAFT_MESSAGE)
            if kind in DRAFT_KINDS:
                drafts[day] = drafts.get(day, 0) + 1
                self._drafts[identity] = drafts

    def run(self, student_id, kind, fn, *args, now=None, wait=None, **kwargs):
        moment = time.time() if now is None else float(now)
        self.admit(student_id, kind, moment)
        timeout = _positive("AI_TIMEOUT_SECONDS", 30)
        retries = 1
        extra = {}
        if _accepts(fn, "timeout"):
            extra["timeout"] = timeout
        if _accepts(fn, "max_retries"):
            extra["max_retries"] = retries
        call_kwargs = {**kwargs, **extra}
        if wait is None:
            rounds = ASK_ROUNDS if kind == "ask" else 1
            wait = timeout * (retries + 1) * rounds + 5
        def attempt():
            # 每次单独复制上下文。超时后旧线程可能还占着上一份，不能再进入。
            ctx = contextvars.copy_context()

            def invoke():
                try:
                    return "ok", ctx.run(fn, *args, **call_kwargs)
                except Exception as exc:
                    return "err", exc

            future = self._pool().submit(invoke)
            try:
                return future.result(timeout=wait)
            except TimeoutError:
                return "timeout", None

        status, value = attempt()
        if status == "ok":
            return value
        # 外层超时说明调用还在跑，不能再开一次，否则两个线程会同时改同一份会话。
        # HTTP 超时由客户端 max_retries=1 在这次调用内部重试。
        if status == "timeout":
            raise RuntimeError(TIMEOUT_MESSAGE)
        status, value = attempt()
        if status == "ok":
            return value
        if status == "timeout":
            raise RuntimeError(TIMEOUT_MESSAGE)
        raise RuntimeError(FAIL_MESSAGE)


_GATE = None
_GATE_LOCK = threading.Lock()


def current():
    global _GATE
    with _GATE_LOCK:
        if _GATE is None:
            _GATE = Gate(workers=_positive("AI_POOL_WORKERS", 6))
        return _GATE


def run(*args, **kwargs):
    return current().run(*args, **kwargs)


def reset():
    global _GATE
    with _GATE_LOCK:
        if _GATE is not None:
            _GATE.shutdown()
        _GATE = None
