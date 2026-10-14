import csv
import duckdb

DB_PATH = "database.duckdb"
OUTPUT_PATH = "mleague_player_stats.csv"

query = """
SELECT
    season_start_year,
    stage,
    player_name,
    team_name,
    total_game_count,
    agari_per_kyoku_percent,
    tsumo_agari_per_agari_percent,
    reach_agari_per_agari_percent,
    furo_agari_per_agari_percent,
    dama_agari_per_agari_percent,
    dealin_per_kyoku_percent,
    hitsumo_per_kyoku_percent,
    furo_per_kyoku_percent,
    reach_per_kyoku_percent,
    reach_agari_per_reach_percent,
    ryukyoku_per_kyoku_percent,
    tenpai_per_ryukyoku_percent,
    tenpai_points_per_ryukyoku,
    rank1_count,
    rank2_count,
    rank3_count,
    rank4_count,
    top_per_game_percent,
    top2_per_game_percent,
    avoid_last_per_game_percent,
    best_score,
    league_points_total,
    agari_points_per_agari,
    dealin_points_per_dealin,
    reach_dealin_per_reach_percent,
    reach_declare_dealin_count,
    dora_per_agari,
    aka_dora_per_agari,
    ura_dora_per_reach_agari,
    all_dora_per_agari
FROM player_season_stage_stats
ORDER BY season_start_year, stage, player_name
"""

db = duckdb.connect(DB_PATH, read_only=True)

result = db.execute(query)
columns = [description[0] for description in result.description]
rows = result.fetchall()

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(rows)

db.close()

print(f"出力完了: {OUTPUT_PATH}")
print(f"データ件数: {len(rows)}")
print(f"列数: {len(columns)}")
