import csv
import duckdb

DB_PATH = "database.duckdb"
OUT_PATH = "mleague_player_features.csv"

db = duckdb.connect(DB_PATH, read_only=True)

# 1ゲーム・1選手につき1行で集計する
query = """
WITH game_info AS (
    SELECT
        g.id AS game_id,
        g.date,
        g.m_league_game_id,
        p.id AS player_id,
        p.name AS player,
        r.rank,
        r.score AS final_point,
        r.league_points
    FROM game g
    JOIN game_player_result r ON r.game_id = g.id
    JOIN player p ON p.id = r.player_id
),
kyoku_counts AS (
    SELECT
        k.game_id,
        COUNT(DISTINCT k.id) AS kyoku_count
    FROM kyoku k
    GROUP BY k.game_id
),
discard_counts AS (
    SELECT
        k.game_id,
        d.actor_player_id AS player_id,
        COUNT(*) AS discard_count,
        SUM(CASE WHEN d.is_reach_declaration = 1 THEN 1 ELSE 0 END)
            AS riichi_declaration_discard_count
    FROM event e
    JOIN kyoku k ON k.id = e.kyoku_id
    JOIN discard_event d ON d.event_id = e.id
    GROUP BY k.game_id, d.actor_player_id
),
reach_counts AS (
    SELECT
        k.game_id,
        r.actor_player_id AS player_id,
        COUNT(*) AS riichi_count
    FROM event e
    JOIN kyoku k ON k.id = e.kyoku_id
    JOIN reach_event r ON r.event_id = e.id
    GROUP BY k.game_id, r.actor_player_id
),

riichi_dapai_counts AS (
    SELECT
        game_id,
        player_id,
        AVG(discard_number) AS avg_riichi_dapai
    FROM (
        SELECT
            k.game_id,
            d.actor_player_id AS player_id,
            e.kyoku_id,
            ROW_NUMBER() OVER (
                PARTITION BY e.kyoku_id, d.actor_player_id
                ORDER BY e.event_order
            ) AS discard_number,
            d.is_reach_declaration
        FROM event e
        JOIN kyoku k ON k.id = e.kyoku_id
        JOIN discard_event d ON d.event_id = e.id
    ) discards
    WHERE is_reach_declaration = 1
    GROUP BY game_id, player_id
),
furo_by_kyoku AS (
    SELECT DISTINCT
        k.game_id,
        k.id AS kyoku_id,
        f.actor_player_id AS player_id
    FROM event e
    JOIN kyoku k ON k.id = e.kyoku_id
    JOIN (
        SELECT event_id, actor_player_id FROM chi_event
        UNION ALL
        SELECT event_id, actor_player_id FROM pon_event
        UNION ALL
        SELECT event_id, actor_player_id FROM daiminkan_event
    ) f ON f.event_id = e.id
),
furo_counts AS (
    SELECT
        game_id,
        player_id,
        COUNT(*) AS furo_kyoku_count
    FROM furo_by_kyoku
    GROUP BY game_id, player_id
),
agari_counts AS (
    SELECT
        k.game_id,
        a.actor_player_id AS player_id,
        COUNT(*) AS agari_count,
        SUM(CASE WHEN e.type = 'tsumo' THEN 1 ELSE 0 END)
            AS tsumo_agari_count,
        SUM(CASE WHEN e.type = 'ron' THEN 1 ELSE 0 END)
            AS ron_agari_count,
        AVG(a.agari_points) AS avg_agari_points,
        MIN(a.agari_points) AS min_agari_points,
        MAX(a.agari_points) AS max_agari_points
    FROM event e
    JOIN kyoku k ON k.id = e.kyoku_id
    JOIN agari_event a ON a.event_id = e.id
    GROUP BY k.game_id, a.actor_player_id
),
houju_counts AS (
    SELECT
        k.game_id,
        a.target_player_id AS player_id,
        COUNT(*) AS houju_count
    FROM event e
    JOIN kyoku k ON k.id = e.kyoku_id
    JOIN agari_event a ON a.event_id = e.id
    WHERE a.target_player_id IS NOT NULL
    GROUP BY k.game_id, a.target_player_id
)
SELECT
    gi.game_id,
    gi.m_league_game_id,
    gi.date,
    gi.player,
    gi.rank,
    gi.final_point,
    gi.league_points,
    COALESCE(kc.kyoku_count, 0) AS kyoku_count,
    COALESCE(dc.discard_count, 0) AS discard_count,
    COALESCE(rc.riichi_count, 0) AS riichi_count,
    COALESCE(rc.riichi_count, 0) * 1.0
        / NULLIF(kc.kyoku_count, 0) AS riichi_rate,
    rd.avg_riichi_dapai AS avg_riichi_dapai,
    COALESCE(fc.furo_kyoku_count, 0) AS furo_kyoku_count,
    COALESCE(fc.furo_kyoku_count, 0) * 1.0
        / NULLIF(kc.kyoku_count, 0) AS furo_rate,
    COALESCE(ac.agari_count, 0) AS agari_count,
    COALESCE(ac.agari_count, 0) * 1.0
        / NULLIF(kc.kyoku_count, 0) AS agari_rate,
    COALESCE(ac.tsumo_agari_count, 0) AS tsumo_agari_count,
    COALESCE(ac.ron_agari_count, 0) AS ron_agari_count,
    COALESCE(hc.houju_count, 0) AS houju_count,
    COALESCE(hc.houju_count, 0) * 1.0
        / NULLIF(kc.kyoku_count, 0) AS houju_rate,
    ac.avg_agari_points,
    ac.min_agari_points,
    ac.max_agari_points
FROM game_info gi
LEFT JOIN kyoku_counts kc ON kc.game_id = gi.game_id
LEFT JOIN discard_counts dc
    ON dc.game_id = gi.game_id AND dc.player_id = gi.player_id
LEFT JOIN reach_counts rc
    ON rc.game_id = gi.game_id AND rc.player_id = gi.player_id
LEFT JOIN furo_counts fc
    ON fc.game_id = gi.game_id AND fc.player_id = gi.player_id
LEFT JOIN agari_counts ac
    ON ac.game_id = gi.game_id AND ac.player_id = gi.player_id
LEFT JOIN houju_counts hc
    ON hc.game_id = gi.game_id AND hc.player_id = gi.player_id
LEFT JOIN riichi_dapai_counts rd
    ON rd.game_id = gi.game_id
   AND rd.player_id = gi.player_id
ORDER BY gi.game_id, gi.rank
"""

rows = db.execute(query).fetchall()
columns = [desc[0] for desc in db.description]

with open(OUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(rows)

db.close()

print(f"出力完了: {OUT_PATH}")
print(f"行数: {len(rows)}")
print("先頭5行:")
for row in rows[:5]:
    print(row)
