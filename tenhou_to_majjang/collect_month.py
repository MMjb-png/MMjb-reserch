
import argparse
import gzip
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "tenhou_mjlogs"

# 対象ルール：四人打ち・鳳凰卓・南場・喰いタンあり・赤ドラあり
TARGET_RULE = "四鳳南喰赤－"


def fetch_daily_list(day: date) -> Path | None:
    """日別の牌譜一覧を取得してHTMLとして保存する。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"scc{day:%Y%m%d}.html"
    output_path = DATA_DIR / filename

    # 既に取得済みなら再利用
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"[Skip] 一覧あり: {filename}")
        return output_path

    url = (
        f"https://tenhou.net/sc/raw/dat/{day:%Y}/"
        f"scc{day:%Y%m%d}.html.gz"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            compressed = response.read()

        content = gzip.decompress(compressed)
        output_path.write_bytes(content)
        print(f"[一覧取得成功] {filename} ({len(content)} bytes)")
        return output_path

    except Exception as exc:
        print(f"[一覧取得失敗] {day}: {exc}")
        return None


def extract_target_ids(path: Path) -> list[str]:
    """対象ルールの行だけから牌譜IDを抽出する。"""
    content = path.read_text(encoding="utf-8", errors="ignore")
    seen = set()
    result = []

    pattern = re.compile(
        r"log=(\d{10}gm-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{8})"
    )

    for line in content.splitlines():
        if TARGET_RULE not in line:
            continue

        match = pattern.search(line)
        if match:
            log_id = match.group(1)
            if log_id not in seen:
                seen.add(log_id)
                result.append(log_id)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="天鳳の四鳳南喰赤－の牌譜を日付指定で収集"
    )
    parser.add_argument("--start", required=True, help="開始日 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="終了日 YYYY-MM-DD")
    parser.add_argument("--interval", type=float, default=3.0,
                        help="牌譜取得間隔（秒）")
    parser.add_argument("--list-only", action="store_true",
                        help="一覧取得とID抽出だけ行い、牌譜は取得しない")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    if end < start:
        parser.error("--end は --start 以降の日付にしてください")

    all_ids = []
    failed_days = []
    current = start

    while current <= end:
        path = fetch_daily_list(current)
        if path is None:
            failed_days.append(current.isoformat())
        else:
            ids = extract_target_ids(path)
            print(f"[対象件数] {current}: {len(ids)}")
            all_ids.extend(ids)

        current += timedelta(days=1)
        time.sleep(0.5)

    # 日付間で重複するIDも除去（順序は維持）
    all_ids = list(dict.fromkeys(all_ids))

    print(f"\n対象牌譜IDの合計: {len(all_ids)}")
    print(f"一覧取得失敗日: {failed_days}")

    # 後から確認・再利用できるようにID一覧を保存
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    id_file = DATA_DIR / f"target_ids_{start:%Y%m%d}_{end:%Y%m%d}.txt"
    id_file.write_text("\n".join(all_ids), encoding="utf-8")
    print(f"ID一覧: {id_file}")

    if args.list_only:
        return

    # 既存のダウンロード関数を利用
    from download_mjlog import download_mjlog

    success = 0
    for index, log_id in enumerate(all_ids, start=1):
        print(f"[{index}/{len(all_ids)}] {log_id}")
        if download_mjlog(log_id, str(LOG_DIR), args.interval):
            success += 1

    print(f"\n牌譜ダウンロード: {success}/{len(all_ids)}")

    # 既存のJSON変換と特徴量抽出を実行
    steps = [
        [sys.executable, "convert_all.py"],
        ["node", "extract_features.js", "paipu_json"],
    ]

    for command in steps:
        print(f"\n[実行] {' '.join(command)}")
        result = subprocess.run(command, cwd=BASE_DIR)
        if result.returncode != 0:
            print("[停止] コマンドが失敗しました。上のエラーを確認してください。")
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()