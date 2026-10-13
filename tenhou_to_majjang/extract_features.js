"use strict";

const fs = require("fs");  //fs:ファイルシステム
const path = require("path"); //path:ファイル名取得


// ================================
// CSV用エスケープ
// ================================
function csvEscape(value) {
    if (value === null || value === undefined) {
        return "";
    }

    const str = String(value);

    if (
        str.includes(",") ||
        str.includes('"') ||
        str.includes("\n")
    ) {
        return '"' + str.replace(/"/g, '""') + '"';
    }

    return str;
}


// ======================================
// プレイヤー名を取得　（余計な情報を省く）
// ======================================
function playerName(name) {
    // kobalabの解析処理と同様に、
    // 改行以降の情報を取り除く
    return String(name).replace(/\n.*$/, "");
}


// ================================
// 1試合を解析
// ================================
function extractGame(paipu, gameId) {

    if (!paipu.player || paipu.player.length !== 4) {
        throw new Error("player情報が4人分ありません");
    }

    if (!Array.isArray(paipu.log)) {
        throw new Error("paipu.log がありません");
    }

    const players = paipu.player.map(playerName); //プレイヤ名保存

    // ----------------------------
    // 1試合分の集計データ
    // ----------------------------
    const data = {

        game_id: gameId,

        player: players,

        rank: paipu.rank || [null, null, null, null],

        final_point: paipu.defen || [null, null, null, null],

        point: paipu.point || [null, null, null, null],

        kyoku_count: [0, 0, 0, 0],

        discard_count: [0, 0, 0, 0],

        riichi_count: [0, 0, 0, 0],

        riichi_dapai_sum: [0, 0, 0, 0],

        furo_kyoku_count: [0, 0, 0, 0],

        agari_count: [0, 0, 0, 0],

        agari_points: [0, 0, 0, 0],

        min_agari_points: [null, null, null, null],

        max_agari_points: [null, null, null, null],

        tsumo_agari_count: [0, 0, 0, 0],

        ron_agari_count: [0, 0, 0, 0],

        houju_count: [0, 0, 0, 0]
    };


    // 電脳麻将形式のqijia
    const qijia = paipu.qijia;


    // ================================
    // 各局を処理
    // ================================
    for (const log of paipu.log) {

        if (!Array.isArray(log) || log.length === 0) {
            continue;
        }


        // ----------------------------
        // 局情報(qipai)
        // ----------------------------
        const qipaiEvent = log.find(data => data.qipai);

        if (!qipaiEvent) {
            continue;
        }

        const qipai = qipaiEvent.qipai;

        const jushu =
            qipai.zhuangfeng * 4 + qipai.jushu;


        // この局の東家を絶対プレイヤー番号に変換
        const dealer =
            (qijia + jushu) % 4;


        // ----------------------------
        // 局数を全員に加算
        // ----------------------------
        for (let relative = 0; relative < 4; relative++) {

            const player =
                (dealer + relative) % 4;

            data.kyoku_count[player]++;
        }


        // ----------------------------
        // 局内の一時データ
        // ----------------------------

        // 各プレイヤーのこの局の打牌数
        const kyokuDiscardCount = [0, 0, 0, 0];

        // この局で副露したプレイヤー
        const furoPlayers = new Set();


        // ============================
        // 局内イベントを順番に処理
        // ============================

        for (const event of log) {


            // ------------------------
            // 打牌
            // ------------------------
            if (event.dapai) {

                const dapai = event.dapai;

                const player =
                    (dealer + dapai.l) % 4;


                data.discard_count[player]++;

                kyokuDiscardCount[player]++;


                // リーチ宣言
                if (
                    typeof dapai.p === "string" &&
                    dapai.p.endsWith("*")
                ) {

                    data.riichi_count[player]++;

                    data.riichi_dapai_sum[player]
                        += kyokuDiscardCount[player];
                }
            }


            // ------------------------
            // 副露
            // ------------------------
            else if (event.fulou) {

                const fulou = event.fulou;

                const player =
                    (dealer + fulou.l) % 4;

                const m = fulou.m;

                // 牌の部分を取得
                const tilePart = m.slice(1);

                // ------------------------
                // 大明槓
                // 例: p555-5
                // ------------------------
                const isDaiminkan =
                    /^[mpsz][0-9]{3}[+\-=][0-9]$/.test(m);

                // ------------------------
                // チー
                // 例: p345-
                //      p40-6
                // ------------------------
                const isChi =
                    /^[mpsz][0-9]{3}[+\-=]$/.test(m) &&
                    !(
                        tilePart[0] === tilePart[1] &&
                        tilePart[1] === tilePart[2]
                    );

                // ------------------------
                // ポン
                // 例: p444+
                //      z555-
                // ------------------------
                const isPon =
                    /^[mpsz][0-9]{3}[+\-=]$/.test(m) &&
                    tilePart[0] === tilePart[1] &&
                    tilePart[1] === tilePart[2];

                // チー・ポン・大明槓だけを
                // furoとして記録
                if (isChi || isPon || isDaiminkan) {
                    furoPlayers.add(player);
                }
            }


            // ------------------------
            // 和了
            // ------------------------
            else if (event.hule) {

                const hule = event.hule;

                const winner =
                    (dealer + hule.l) % 4;


                // 和了回数
                data.agari_count[winner]++;


                // 和了点
                const points =
                    Number(hule.defen) || 0;

                data.agari_points[winner]
                    += points;


                // 最小和了点
                if (
                    data.min_agari_points[winner] === null ||
                    points < data.min_agari_points[winner]
                ) {

                    data.min_agari_points[winner]
                        = points;
                }


                // 最大和了点
                if (
                    data.max_agari_points[winner] === null ||
                    points > data.max_agari_points[winner]
                ) {

                    data.max_agari_points[winner]
                        = points;
                }


                // ツモ / ロン
                if (hule.baojia == null) {

                    data.tsumo_agari_count[winner]++;

                }
                else {

                    data.ron_agari_count[winner]++;


                    // 放銃者
                    const houju =
                        (dealer + hule.baojia) % 4;

                    data.houju_count[houju]++;
                }
            }
        }


        // ============================
        // 局終了時の処理
        // ============================


        // 副露したプレイヤー
        for (const player of furoPlayers) {

            data.furo_kyoku_count[player]++;
        }


    }


    // ================================
    // 1試合 → 4行に変換
    // ================================

    const rows = [];

    for (let player = 0; player < 4; player++) {

        const kyoku =
            data.kyoku_count[player];

        const riichi =
            data.riichi_count[player];

        const furo =
            data.furo_kyoku_count[player];

        const agari =
            data.agari_count[player];

        const houju =
            data.houju_count[player];


        const avgRiichiDapai =
            riichi > 0
                ? data.riichi_dapai_sum[player] / riichi
                : "";


        const avgAgariPoints =
            agari > 0
                ? data.agari_points[player] / agari
                : "";


        rows.push({

            game_id: data.game_id,

            player: data.player[player],

            rank: data.rank[player],

            final_point: data.final_point[player],

            point: data.point[player],

            kyoku_count: kyoku,

            discard_count:
                data.discard_count[player],

            riichi_count: riichi,

            riichi_rate:
                kyoku > 0
                    ? riichi / kyoku
                    : 0,

            avg_riichi_dapai:
                avgRiichiDapai,

            furo_kyoku_count: furo,

            furo_rate:
                kyoku > 0
                    ? furo / kyoku
                    : 0,

            agari_count: agari,

            agari_rate:
                kyoku > 0
                    ? agari / kyoku
                    : 0,

            tsumo_agari_count:
                data.tsumo_agari_count[player],

            ron_agari_count:
                data.ron_agari_count[player],

            houju_count: houju,

            houju_rate:
                kyoku > 0
                    ? houju / kyoku
                    : 0,

            avg_agari_points:
                avgAgariPoints,

            min_agari_points:
                data.min_agari_points[player] ?? "",

            max_agari_points:
                data.max_agari_points[player] ?? ""
        });
    }


    return rows;
}


// ================================
// JSONファイルを1つ読む
// ================================
function readGame(filename) {

    const text =
        fs.readFileSync(filename, "utf8");

    return JSON.parse(text);
}


// ================================
// 入力ファイル一覧を取得
// ================================
function getJsonFiles(input) {

    const stat = fs.statSync(input);

    // 1ファイルの場合
    if (stat.isFile()) {

        if (!input.endsWith(".json")) {
            throw new Error(
                "入力ファイルは .json を指定してください"
            );
        }

        return [input];
    }


    // ディレクトリの場合
    if (stat.isDirectory()) {

        return fs.readdirSync(input)
            .filter(filename => filename.endsWith(".json"))
            .sort()
            .map(filename => path.join(input, filename));
    }


    throw new Error("入力がファイルでもディレクトリでもありません");
}


// ================================
// メイン処理
// ================================
const input = process.argv[2];

if (!input) {

    console.error(
        "使い方:"
    );

    console.error(
        "node extract_features.js test.json"
    );

    console.error(
        "または"
    );

    console.error(
        "node extract_features.js paipu"
    );

    process.exit(1);
}


try {

    const files = getJsonFiles(input);

    if (files.length === 0) {

        throw new Error(
            "JSONファイルが見つかりません"
        );
    }


    const allRows = [];


    for (const filename of files) {

        console.log(
            `解析中: ${filename}`
        );


        const paipu =
            readGame(filename);


        const gameId =
            path.basename(
                filename,
                ".json"
            );


        const rows =
            extractGame(
                paipu,
                gameId
            );


        allRows.push(...rows);
    }


    // ============================
    // CSV出力
    // ============================

    const columns = [

        "game_id",
        "player",

        "rank",
        "final_point",
        "point",

        "kyoku_count",

        "discard_count",

        "riichi_count",
        "riichi_rate",
        "avg_riichi_dapai",

        "furo_kyoku_count",
        "furo_rate",

        "agari_count",
        "agari_rate",

        "tsumo_agari_count",
        "ron_agari_count",

        "houju_count",
        "houju_rate",

        "avg_agari_points",
        "min_agari_points",
        "max_agari_points"
    ];


    const lines = [];

    lines.push(
        columns.join(",")
    );


    for (const row of allRows) {

        lines.push(

            columns
                .map(column =>
                    csvEscape(row[column])
                )
                .join(",")
        );
    }


    const output =
        "player_features.csv";


    fs.writeFileSync(
        output,
        lines.join("\n"),
        "utf8"
    );


    console.log("");
    console.log("================================");
    console.log("特徴量CSVを作成しました");
    console.log("================================");

    console.log(
        `入力ファイル数: ${files.length}`
    );

    console.log(
        `出力行数: ${allRows.length}`
    );

    console.log(
        `出力ファイル: ${output}`
    );

}
catch (error) {

    console.error("");
    console.error("エラーが発生しました");
    console.error(error.message);

    process.exit(1);
}
