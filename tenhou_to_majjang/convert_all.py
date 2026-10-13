import json
from pathlib import Path
from tenhou_to_majiang import convert_mjlog

# 入力：リポジトリ直下の天鳳牌譜ディレクトリ
INPUT_DIR = Path("../tenhou_mjlogs")

# 出力：JSON専用ディレクトリ
OUTPUT_DIR = Path("paipu_json")

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(INPUT_DIR.glob("*.mjlog"))

    if not files:
        print(f"入力ファイルが見つかりません: {INPUT_DIR.resolve()}")
        return

    success = 0
    failed = 0

    for file_path in files:
        output_path = OUTPUT_DIR / f"{file_path.stem}.json"

        try:
            paipu = convert_mjlog(file_path)

            with output_path.open("w", encoding="utf-8") as f:
                json.dump(paipu, f, ensure_ascii=False, indent=2)

            success += 1
            print(f"[成功] {file_path.name} -> {output_path}")

        except Exception as e:
            failed += 1
            print(f"[失敗] {file_path.name}: {e}")

    print("\n=== 一括変換結果 ===")
    print(f"対象: {len(files)}")
    print(f"成功: {success}")
    print(f"失敗: {failed}")
    print(f"出力先: {OUTPUT_DIR.resolve()}")

if __name__ == "__main__":
    main()
