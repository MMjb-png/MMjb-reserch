from urllib.parse import unquote
import argparse
import gzip
import json
import xml.etree.ElementTree as ET
from pathlib import Path


# ============================================================
# 天鳳の牌番号 → 電脳麻将の牌文字列
# ============================================================

def pai(tile_ids, hongpai=True):
    """
    天鳳の牌番号(0～135)を
    電脳麻将形式の牌文字列に変換する。

    例:
        0  -> m1
        16 -> m0  (赤5)
        52 -> p0  (赤5)
        88 -> s0  (赤5)
    """

    if isinstance(tile_ids, int):
        tile_ids = [tile_ids]

    result = ""
    current_suit = ""

    for tile_id in sorted(tile_ids):
        # 萬子・筒子・索子・字牌
        suits = ["m", "p", "s", "z"]
        suit = suits[tile_id // 36]

        if suit != current_suit:
            result += suit
            current_suit = suit

        # 1～9を求める
        number = (tile_id % 36) // 4 + 1

        # 赤5
        if (
            hongpai
            and suit != "z"
            and number == 5
            and tile_id % 4 == 0
        ):
            number = 0

        result += str(number)

    return result

def mianzi(m, hongpai=True):
    """
    天鳳の面子コード m を
    電脳麻将形式の副露面子文字列に変換する。
    """

    # 誰から鳴いたか
    # 0: 鳴きなし
    # 1: 下家
    # 2: 対面
    # 3: 上家
    direction = ["", "+", "=", "-"][m & 0x0003]

    # -------------------------
    # 順子
    # -------------------------
    if m & 0x0004:
        p = (m & 0xFC00) >> 10

        # どの牌を鳴いたか
        r = p % 3

        p //= 3

        # 萬子・筒子・索子
        suit = ["m", "p", "s"][p // 7]

        # 順子の開始数字
        n = p % 7 + 1

        nums = [n, n + 1, n + 2]

        # 牌添字
        indexes = [
            (m & 0x0018) >> 3,
            (m & 0x0060) >> 5,
            (m & 0x0180) >> 7,
        ]

        # 赤5
        for i in range(3):
            if (
                hongpai
                and nums[i] == 5
                and indexes[i] == 0
            ):
                nums[i] = 0

        # 鳴いた牌に + / = / - を付ける
        nums[r] = str(nums[r]) + direction

        return suit + "".join(map(str, nums))

    # -------------------------
    # 刻子・加槓
    # -------------------------
    elif m & 0x0018:
        p = (m & 0xFE00) >> 9

        # どの牌を鳴いたか
        r = p % 3

        p //= 3

        # 萬子・筒子・索子・字牌
        suit = ["m", "p", "s", "z"][p // 9]

        # 牌番号
        n = p % 9 + 1

        nums = [n, n, n, n]

        # 赤5
        if hongpai and suit != "z" and n == 5:
            if (m & 0x0060) == 0:
                nums[3] = 0
            elif r == 0:
                nums[2] = 0
            else:
                nums[1] = 0

        # 加槓
        if m & 0x0010:
            return (
                suit
                + "".join(map(str, nums[:3]))
                + direction
                + str(nums[3])
            )

        # ポン
        return (
            suit
            + "".join(map(str, nums[:3]))
            + direction
        )

    # -------------------------
    # 暗槓・大明槓
    # -------------------------
    else:
        p = (m & 0xFF00) >> 8

        # どの牌を鳴いたか
        r = p % 4

        p //= 4

        # 萬子・筒子・索子・字牌
        suit = ["m", "p", "s", "z"][p // 9]

        # 牌番号
        n = p % 9 + 1

        nums = [n, n, n, n]

        # 赤5
        if hongpai and suit != "z" and n == 5:
            if direction == "":
                # 暗槓
                nums[3] = 0
            elif r == 0:
                # 赤牌を鳴いた場合
                nums[3] = 0
            else:
                nums[2] = 0

        return suit + "".join(map(str, nums)) + direction

# ============================================================
# GO
# ============================================================

def parse_go(type_value):
    """
    GOのtype属性を解析する。

    koba::blogの定義に合わせる。
    """

    type_value = int(type_value)

    hongpai = not (0x02 & type_value)
    ariari = not (0x04 & type_value)
    dongfeng = not (0x08 & type_value)
    sanma = bool(0x10 & type_value)
    soku = bool(0x40 & type_value)

    level = (
        ((0x20 & type_value) >> 4)
        | ((0x80 & type_value) >> 7)
    )

    level_name = ["般", "上", "特", "鳳"][level]

    title = (
        ("三" if sanma else "四")
        + level_name
        + ("東" if dongfeng else "南")
        + ("喰" if ariari else "")
        + ("赤" if hongpai else "")
        + ("速" if soku else "")
    )

    return {
        "hongpai": hongpai,
        "ariari": ariari,
        "dongfeng": dongfeng,
        "sanma": sanma,
        "soku": soku,
        "level": level,
        "title": title,
    }


# ============================================================
# INIT → qipai
# ============================================================

def parse_init(attr, hongpai):
    """
    INITを電脳麻将のqipai形式に変換する。
    """

    seed = list(map(int, attr["seed"].split(",")))
    ten = [
        int(x) * 100
        for x in attr["ten"].split(",")
    ]

    hands = [
        pai(
            list(map(int, attr[f"hai{i}"].split(","))),
            hongpai
        )
        for i in range(4)
    ]

    oya = int(attr["oya"])

    # 親を0番にする
    ten = ten[oya:] + ten[:oya]
    hands = hands[oya:] + hands[:oya]

    qipai = {
        "zhuangfeng": seed[0] // 4,
        "jushu": seed[0] % 4,
        "changbang": seed[1],
        "lizhibang": seed[2],
        "defen": ten,
        "baopai": pai(seed[5], hongpai),
        "shoupai": hands,
    }

    return qipai


# ============================================================
# UN → player
# ============================================================

def parse_players(attr):
    """
    UNのn0～n3をプレイヤー名として取得。
    URLエンコードされているのでデコードする。
    """

    players = []

    for i in range(4):
        name = attr.get(f"n{i}", "")
        name = unquote(name)
        players.append(name)

    return players


# ============================================================
# hule → 和了情報
# ============================================================

HUPAI_NAMES = [
    "門前清自摸和", "立直", "一発", "槍槓", "嶺上開花",
    "海底摸月", "河底撈魚", "平和", "断幺九", "一盃口",
    "自風 東", "自風 南", "自風 西", "自風 北",
    "場風 東", "場風 南", "場風 西", "場風 北",
    "役牌 白", "役牌 發", "役牌 中", "両立直", "七対子",
    "混全帯幺九", "一気通貫", "三色同順", "三色同刻",
    "三槓子", "対々和", "三暗刻", "小三元", "混老頭",
    "二盃口", "純全帯幺九", "混一色", "清一色", "人和",
    "天和", "地和", "大三元", "四暗刻", "四暗刻単騎",
    "字一色", "緑一色", "清老頭", "九蓮宝燈",
    "純正九蓮宝燈", "国士無双", "国士無双１３面",
    "大四喜", "小四喜", "四槓子", "ドラ", "裏ドラ", "赤ドラ",
]

def hule(attr, oya, hongpai=True):
    who = int(attr["who"])
    from_who = int(attr["fromWho"])

    # 天鳳のプレイヤー番号を親基準に変換
    l = (who + 4 - oya) % 4
    baojia = (
        (from_who + 4 - oya) % 4
        if who != from_who else None
    )

    # 手牌と和了牌をまとめて牌文字列に変換
    machi = int(attr["machi"])
    hai = list(map(int, attr["hai"].split(",")))
    shoupai = pai(hai, hongpai)

    # 副露面子（暗槓を含む）
    m = attr.get("m", "")
    if m:
        mianzi_list = [
            mianzi(int(code), hongpai)
            for code in m.split(",")
        ]
        shoupai += "," + ",".join(reversed(mianzi_list))

    # 和了役
    hupai = []
    fanshu = 0
    yakuman = attr.get("yakuman", "")

    if yakuman:
        for yaku_id in map(int, yakuman.split(",")):
            hupai.append({
                "name": HUPAI_NAMES[yaku_id],
                "fanshu": "*"
            })
    else:
        yaku = list(map(int, attr.get("yaku", "").split(",")))
        for i in range(0, len(yaku), 2):
            yaku_id = yaku[i]
            han = yaku[i + 1]
            hupai.append({
                "name": HUPAI_NAMES[yaku_id],
                "fanshu": han
            })
            fanshu += han

    # 各プレイヤーの点数変動
    sc = list(map(int, attr["sc"].split(",")))
    fenpei = [sc[i] * 100 for i in (1, 3, 5, 7)]
    fenpei = fenpei[oya:] + fenpei[:oya]

    ten = list(map(int, attr["ten"].split(",")))

    result = {
        "l": l,
        "shoupai": shoupai,
        "baojia": baojia,
        "defen": ten[1],
        "hupai": hupai,
        "fenpei": fenpei
    }

    if attr.get("doraHaiUra"):
        result["fubaopai"] = [
            pai(int(tile), hongpai)
            for tile in attr["doraHaiUra"].split(",")
        ]

    if yakuman:
        result["damanguan"] = len(yakuman.split(","))
    else:
        result["fu"] = ten[0]
        result["fanshu"] = fanshu

    return {"hule": result}


# ============================================================
# メイン変換
# ============================================================

def convert_mjlog(file_path):
    """
    .mjlogファイルを読み込み、
    電脳麻将形式のdictを返す。
    """

    with gzip.open(
        file_path,
        "rt",
        encoding="utf-8"
    ) as f:
        xml_text = f.read()

    root = ET.fromstring(xml_text)

    paipu = {
        "title": "",
        "player": [],
        "qijia": 0,
        "log": [],
    }

    hongpai = True
    oya = 0
    last_zimo = [None, None, None, None]
    reach = [False, False, False, False]

    for elem in root:

        # ----------------------------------------------------
        # GO
        # ----------------------------------------------------

        if elem.tag == "GO":
            go = parse_go(elem.attrib["type"])

            if go["sanma"]:
                raise ValueError("三麻には現在対応していません")

            hongpai = go["hongpai"]
            paipu["title"] = go["title"]

            print("ルール:", go["title"])

        # ----------------------------------------------------
        # UN
        # ----------------------------------------------------

        elif elem.tag == "UN":
            paipu["player"] = parse_players(elem.attrib)

        # ----------------------------------------------------
        # TAIKYOKU
        # ----------------------------------------------------

        elif elem.tag == "TAIKYOKU":
            paipu["qijia"] = int(elem.attrib["oya"])

            # 半荘のログを初期化
            paipu["log"] = []

        # ----------------------------------------------------
        # INIT
        # ----------------------------------------------------
        elif elem.tag == "REACH":
            player = int(elem.attrib["who"])

            if elem.attrib["step"] == "1":
                reach[player] = True

        elif elem.tag == "INIT":

            oya = int(elem.attrib["oya"])

            qipai = parse_init(
                elem.attrib,
                hongpai
            )

            paipu["log"].append({
                "qipai": qipai
            })
        
        # ----------------------------------------------------
        # TUVW → ツモ
        # ----------------------------------------------------

        elif (
            len(elem.tag) > 1
            and elem.tag[0] in "TUVW"
            and elem.tag[1:].isdigit()
        ):

            player = "TUVW".index(elem.tag[0])
            tile_id = int(elem.tag[1:])

            # 直前にツモった牌を記録
            last_zimo[player] = tile_id

            paipu["log"].append({
                "zimo": {
                    "l": (player + 4 - oya) % 4,
                    "p": pai(tile_id, hongpai)
                }
            })


        elif elem.tag == "N":
            player = int(elem.attrib["who"])
            m = int(elem.attrib["m"])

            relative_player = (player - oya + 4) % 4

            paipu["log"].append({
                "fulou": {
                    "l": relative_player,
                    "m": mianzi(m, hongpai)
                }
            })



        # ----------------------------------------------------
        # AGARI → hule(和了) 
        # ----------------------------------------------------
        elif elem.tag == "AGARI":
            paipu["log"].append(
                hule(elem.attrib, oya, hongpai)
            )
            
        # ----------------------------------------------------
        # DEFG → 打牌
        # ----------------------------------------------------
        elif (
            len(elem.tag) > 1
            and elem.tag[0] in "DEFG"
            and elem.tag[1:].isdigit()
        ):

            player = "DEFG".index(elem.tag[0])
            tile_id = int(elem.tag[1:])

            # ツモ切りか判定
            if last_zimo[player] == tile_id:
                tile = pai(tile_id, hongpai) + "_"
            else:
                tile = pai(tile_id, hongpai)

            if reach[player]:
                tile += "*"
                reach[player] = False

            relative_player = (player - oya + 4) % 4

            paipu["log"].append({
                "dapai": {
                    "l": relative_player,
                    "p": tile
                }
            })

    return paipu


# ============================================================
# main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="天鳳mjlogを電脳麻将形式へ変換"
    )

    parser.add_argument(
        "input_file",
        help="入力する.mjlogファイル"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="output.json",
        help="出力JSONファイル"
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)

    if not input_path.exists():
        print(f"[Error] ファイルがありません: {input_path}")
        return

    print("=== 天鳳 → 電脳麻将 変換開始 ===")

    paipu = convert_mjlog(input_path)

    with open(
        args.output,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            paipu,
            f,
            ensure_ascii=False,
            indent=4
        )

    print(f"[Success] 保存しました: {args.output}")


if __name__ == "__main__":
    main()