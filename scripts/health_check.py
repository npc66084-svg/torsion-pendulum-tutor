"""检查试点页面是否能打开。不打印环境变量。

用法：python scripts/health_check.py http://127.0.0.1:7862/
不写地址时，用 APP_PORT，没有则用 7862。
"""
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def check(url, timeout=5):
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        url = args[0]
    else:
        port = os.environ.get("APP_PORT", "7862").strip() or "7862"
        url = f"http://127.0.0.1:{port}/"
    ok = check(url)
    print("健康检查通过" if ok else "健康检查失败", url)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
