"""健康检查和记录备份。不启动教学服务，也不碰真实 records/。"""
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from zoneinfo import ZoneInfo

from scripts.backup_records import backup
from scripts.health_check import check


class _OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def test_health_check_accepts_open_page_and_rejects_closed_port():
    server = HTTPServer(("127.0.0.1", 0), _OkHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    closed = sock.getsockname()[1]
    sock.close()
    try:
        assert check(f"http://127.0.0.1:{port}/", timeout=2)
        assert not check(f"http://127.0.0.1:{closed}/", timeout=1)
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_backup_copies_records_and_drops_old_folders(tmp_path):
    source = tmp_path / "records" / "10001"
    source.mkdir(parents=True)
    (source / "session_demo.json").write_text('{"student_id":"10001"}', encoding="utf-8")
    dest = tmp_path / "备份"
    old = dest / "backup_20200101_000000"
    old.mkdir(parents=True)
    (old / "stale.txt").write_text("old", encoding="utf-8")
    recent = dest / "backup_20261101_000000"
    recent.mkdir()
    moment = datetime(2026, 11, 11, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    target, removed = backup(source.parent, dest, keep_days=14, now=moment)
    assert (target / "10001" / "session_demo.json").is_file()
    assert "backup_20200101_000000" in removed
    assert not old.exists()
    assert recent.exists()


def test_backup_refuses_to_nest_inside_records(tmp_path):
    source = tmp_path / "records"
    source.mkdir()
    nested = source / "备份"
    try:
        backup(source, nested)
    except ValueError as exc:
        assert "不能放在记录目录里面" in str(exc)
    else:
        raise AssertionError("应该拒绝把备份放进 records")
