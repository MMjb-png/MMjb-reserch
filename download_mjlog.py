import argparse
import gzip
import re
import time
import urllib.request
from pathlib import Path


def extract_log_ids_from_file(file_path: str) -> list[str]:
    """HTMLファイルやテキストから正規表現で完全な牌譜IDのみを正確に抽出する"""
    path = Path(file_path)

    if not path.is_file():
        print(f"[Error] ファイルが存在しません: {file_path}")
        return []

    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    # 天鳳の牌譜ID（例: 2026062700gm-00b9-0000-03f7e9fd）を抽出するパターン
    pattern = r"(\d{10}gm-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{8})"
    matches = re.findall(pattern, content)

    # 重複の削除（順番を維持）
    seen = set()
    unique_ids = []
    for log_id in matches:
        if log_id not in seen:
            seen.add(log_id)
            unique_ids.append(log_id)

    return unique_ids


def download_mjlog(
    log_id: str, output_dir: str, interval_sec: float = 3.0
) -> bool:
    """1件の牌譜XMLを取得し &tw=0.mjlog で保存する"""
    save_dir = Path(output_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{log_id}&tw=0.mjlog"
    mjlog_path = save_dir / filename

    if mjlog_path.exists():
        print(f"[Skip] 既に存在します: {filename}")
        return True

    url = f"https://tenhou.net/0/log/?{log_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()

        # レスポンスが正常なXMLか判定
        if len(xml_data) >= 100 and b"<mjloggm" in xml_data:
            with gzip.open(mjlog_path, "wb") as f_out:
                f_out.write(xml_data)
            print(f"[Success] 保存完了: {filename}")
            time.sleep(interval_sec)
            return True
        else:
            print(f"[Failed] 不正なデータ (取得不可): {log_id}")
            return False

    except Exception as e:
        print(f"[Error] アクセス失敗 ({log_id}): {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="天鳳のHTMLから牌譜IDを抽出し .mjlog で保存するスクリプト"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="解析するHTMLファイル (例: scc2026062700.html)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="./tenhou_mjlogs",
        help="保存先ディレクトリ",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=3.0,
        help="アクセス間隔秒数",
    )

    args = parser.parse_args()

    print(f"--- 牌譜ID抽出開始: {args.input_file} ---")
    log_ids = extract_log_ids_from_file(args.input_file)
    print(f"抽出された牌譜件数: {len(log_ids)} 件")

    if not log_ids:
        print(
            "牌譜IDが見つかりませんでした。HTML形式のファイルかを試してください。"
        )
        return

    success_count = 0
    for i, log_id in enumerate(log_ids, 1):
        print(f"[{i}/{len(log_ids)}] 処理中: {log_id}")
        if download_mjlog(log_id, args.output, args.interval):
            success_count += 1

    print(
        f"--- 処理完了: {success_count}/{len(log_ids)} 件のダウンロードに成功しました ---"
    )


if __name__ == "__main__":
    main()