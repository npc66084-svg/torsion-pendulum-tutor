"""把 records/ 复制到备份目录，并删除超过保留天数的旧备份。

用法：python scripts/backup_records.py --source records --dest 备份 --keep-days 14
备份目录不要放在 records 里面。不上传、不打印名单内容。
"""
import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo


ZONE = ZoneInfo("Asia/Shanghai")


def backup(source, dest, keep_days=14, now=None):
    source = Path(source).resolve()
    dest = Path(dest).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"找不到记录目录：{source}")
    if dest == source or source in dest.parents:
        raise ValueError("备份目录不能放在记录目录里面。")
    moment = now or datetime.now(ZONE)
    dest.mkdir(parents=True, exist_ok=True)
    stamp = moment.strftime("%Y%m%d_%H%M%S")
    target = dest / f"backup_{stamp}"
    if target.exists():
        target = dest / f"backup_{stamp}_{uuid4().hex[:6]}"
    shutil.copytree(source, target)
    cutoff = (moment.date() - timedelta(days=keep_days))
    removed = []
    for child in dest.iterdir():
        if not child.is_dir() or not child.name.startswith("backup_"):
            continue
        digits = "".join(ch for ch in child.name[len("backup_"):] if ch.isdigit())
        if len(digits) < 8:
            continue
        try:
            folder_date = datetime.strptime(digits[:8], "%Y%m%d").date()
        except ValueError:
            continue
        if folder_date <= cutoff:
            shutil.rmtree(child)
            removed.append(child.name)
    return target, removed


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="备份扭摆实验记录")
    parser.add_argument("--source", default=str(root / "records"))
    parser.add_argument("--dest", default=str(root / "备份"))
    parser.add_argument("--keep-days", type=int, default=14)
    args = parser.parse_args(argv)
    try:
        target, removed = backup(args.source, args.dest, keep_days=args.keep_days)
    except (FileNotFoundError, ValueError) as exc:
        print(exc)
        return 1
    print(f"已备份到 {target.name}，删除旧备份 {len(removed)} 个。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
