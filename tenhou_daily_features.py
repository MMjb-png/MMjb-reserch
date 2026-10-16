#!/usr/bin/env python3
"""日付別天鳳牌譜をJSON保存し、プレイヤー特徴量CSVを出力する。"""
import argparse
import csv
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
REPO = HERE.parent if HERE.name == "tenhou_to_majjang" else HERE
sys.path.insert(0, str(REPO / "tenhou_to_majjang"))
from tenhou_to_majiang import convert_mjlog

FIELDS = [
    "game_id", "player", "rank", "final_point", "point", "kyoku_count",
    "discard_count", "riichi_count", "riichi_rate", "avg_riichi_dapai",
    "furo_kyoku_count", "furo_rate", "agari_count", "agari_rate",
    "tsumo_agari_count", "ron_agari_count", "houju_count", "houju_rate",
    "avg_agari_points", "min_agari_points", "max_agari_points",
]


def read_xml(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return ET.parse(f).getroot()


def final_result(root, qijia):
    """OWARIが4人×(最終点,順位点)の8値形式なら読み取る。"""
    elem = root.find("OWARI")
    if elem is None:
        return None
    nums = re.findall(r"-?\d+(?:\.\d+)?", elem.attrib.get("owari", ""))
    if len(nums) != 8:
        return None
    vals = [float(x) for x in nums]
    scores = [int(round(vals[i] * 100)) for i in range(0, 8, 2)]
    points = [vals[i + 1] for i in range(0, 8, 2)]
    scores = scores[qijia:] + scores[:qijia]
    points = points[qijia:] + points[:qijia]
    ranks = [1 + sum(other > score for other in scores) for score in scores]
    return scores, ranks, points


def features(paipu, game_id, final):
    players = paipu.get("player", ["", "", "", ""])
    kyoku = [0] * 4
    discards = [0] * 4
    riichi = [0] * 4
    riichi_turns = [[] for _ in range(4)]
    furo_hands = [set() for _ in range(4)]
    agari_points = [[] for _ in range(4)]
    tsumo = [0] * 4
    ron = [0] * 4
    houju = [0] * 4
    hand = -1
    hand_discards = [0] * 4

    for event in paipu.get("log", []):
        if "qipai" in event:
            hand += 1
            kyoku = [x + 1 for x in kyoku]
            hand_discards = [0] * 4
        elif "dapai" in event:
            d = event["dapai"]
            s = int(d["l"])
            discards[s] += 1
            hand_discards[s] += 1
            if "*" in str(d.get("p", "")):
                riichi[s] += 1
                riichi_turns[s].append(hand_discards[s])
        elif "fulou" in event:
            furo_hands[int(event["fulou"]["l"])].add(hand)
        elif "hule" in event:
            h = event["hule"]
            winner = int(h["l"])
            val = h.get("defen")
            if isinstance(val, (int, float)):
                agari_points[winner].append(float(val))
            if h.get("baojia") is None:
                tsumo[winner] += 1
            else:
                ron[winner] += 1
                houju[int(h["baojia"])] += 1

    rows = []
    for s in range(4):
        k = kyoku[s]
        vals = agari_points[s]
        row = {
            "game_id": game_id, "player": players[s] if s < len(players) else "",
            "rank": "", "final_point": "", "point": "",
            "kyoku_count": k, "discard_count": discards[s],
            "riichi_count": riichi[s],
            "riichi_rate": round(riichi[s] / k, 6) if k else 0,
            "avg_riichi_dapai": round(mean(riichi_turns[s]), 6) if riichi_turns[s] else "",
            "furo_kyoku_count": len(furo_hands[s]),
            "furo_rate": round(len(furo_hands[s]) / k, 6) if k else 0,
            "agari_count": len(vals), "agari_rate": round(len(vals) / k, 6) if k else 0,
            "tsumo_agari_count": tsumo[s], "ron_agari_count": ron[s],
            "houju_count": houju[s], "houju_rate": round(houju[s] / k, 6) if k else 0,
            "avg_agari_points": round(mean(vals), 2) if vals else "",
            "min_agari_points": min(vals) if vals else "",
            "max_agari_points": max(vals) if vals else "",
        }
        if final:
            scores, ranks, points = final
            row.update(rank=ranks[s], final_point=scores[s], point=points[s])
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description="日付別の天鳳牌譜をJSON保存し特徴量CSVを作成")
    parser.add_argument("--start", default="2026-10-04", help="開始日 YYYY-MM-DD")
    parser.add_argument("--end", default="2026-10-07", help="終了日 YYYY-MM-DD")
    parser.add_argument("--raw-root", type=Path, default=REPO / "data/tenhou")
    parser.add_argument("--json-root", type=Path, default=REPO / "data/json/tenhou")
    parser.add_argument("--csv-root", type=Path, default=REPO / "data/csv/tenhou")
    parser.add_argument("--overwrite-json", action="store_true", help="既存JSONを再変換する")
    args = parser.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if end < start:
        parser.error("--end は --start 以降の日付にしてください")

    day = start
    while day <= end:
        rel = Path(str(day.year)) / f"{day.month:02d}" / f"{day.day:02d}"
        raw_dir = args.raw_root / rel
        json_dir = args.json_root / rel
        csv_path = args.csv_root / rel / "tenhou_player_features.csv"
        files = sorted(raw_dir.glob("*.mjlog"))
        if not files:
            print(f"[スキップ] 牌譜がありません: {raw_dir}")
            day += timedelta(days=1)
            continue

        rows_all, failed, no_final = [], 0, 0
        for raw in files:
            jp = json_dir / (raw.stem + ".json")
            try:
                root = read_xml(raw)
                if args.overwrite_json or not jp.exists():
                    paipu = convert_mjlog(raw)
                    jp.parent.mkdir(parents=True, exist_ok=True)
                    with jp.open("w", encoding="utf-8") as f:
                        json.dump(paipu, f, ensure_ascii=False, indent=2)
                else:
                    with jp.open(encoding="utf-8") as f:
                        paipu = json.load(f)
                # 四人麻雀の南風戦・赤ありのみ対象
                if paipu.get("title") != "四鳳南喰赤":
                    continue

                final = final_result(root, int(paipu.get("qijia", 0)))
                if final is None:
                    no_final += 1
                rows_all.extend(features(paipu, raw.stem, final))
            except Exception as e:
                failed += 1
                print(f"[失敗] {raw.name}: {e}")

        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows_all)
        print(f"\n[{day}] 牌譜={len(files)} CSV行={len(rows_all)} 失敗={failed}")
        print(f"JSON: {json_dir}")
        print(f"CSV:  {csv_path}")
        print(f"最終順位・得点を取得できなかった牌譜: {no_final}")
        day += timedelta(days=1)


if __name__ == "__main__":
    main()
