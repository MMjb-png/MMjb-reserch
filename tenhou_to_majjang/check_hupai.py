import gzip
import json
import xml.etree.ElementTree as ET


INPUT_XML = "../tenhou_mjlogs/2026062700gm-00a9-0000-0b1a0522&tw=0.mjlog"
INPUT_JSON = "output.json"


# 今回の牌譜で実際に使用されているTenhouの役ID
YAKU_NAME = {
    1: "立直",
    2: "一発",
    6: "河底撈魚",
    7: "平和",
    8: "断幺九",
    13: "自風 北",
    18: "役牌 白",
    25: "三色同順",
    52: "ドラ",
    53: "裏ドラ",
    54: "赤ドラ",
}


def get_json_hule(data):
    """
    JSONの中からhuleを順番に取り出す。
    """
    result = []

    if isinstance(data, dict):

        if "hule" in data and isinstance(data["hule"], dict):
            result.append(data["hule"])

        for value in data.values():
            result.extend(get_json_hule(value))

    elif isinstance(data, list):

        for value in data:
            result.extend(get_json_hule(value))

    return result


def make_expected_hupai(attr):
    """
    XMLのAGARIのyakuから、期待されるhupaiを作る。
    conv.hule()は使用しない。
    """

    result = []

    # 通常役
    yaku = attr.get("yaku", "")

    if yaku:

        values = [
            int(x)
            for x in yaku.split(",")
            if x != ""
        ]

        # 役ID, 翻数, 役ID, 翻数, ...
        if len(values) % 2 != 0:
            raise ValueError(
                f"yakuの要素数が奇数です: {yaku}"
            )

        for i in range(0, len(values), 2):

            yaku_id = values[i]
            fanshu = values[i + 1]

            if yaku_id not in YAKU_NAME:
                raise ValueError(
                    f"未登録の役IDです: {yaku_id}"
                )

            result.append({
                "name": YAKU_NAME[yaku_id],
                "fanshu": fanshu,
            })

    # 役満
    yakuman = attr.get("yakuman", "")

    if yakuman:
        print(
            "警告: yakumanがあります:",
            yakuman
        )

    return result


# --------------------------------------------------
# XML
# --------------------------------------------------

with gzip.open(INPUT_XML, "rb") as f:
    root = ET.parse(f).getroot()


expected_hupai = []

for elem in root.iter():

    if elem.tag != "AGARI":
        continue

    expected = make_expected_hupai(elem.attrib)

    expected_hupai.append(expected)


# --------------------------------------------------
# JSON
# --------------------------------------------------

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)


json_hules = get_json_hule(data)

actual_hupai = [
    hule.get("hupai", [])
    for hule in json_hules
]


# --------------------------------------------------
# 件数
# --------------------------------------------------

print("XMLのAGARI件数:", len(expected_hupai))
print("JSONのhule件数:", len(actual_hupai))

if len(expected_hupai) != len(actual_hupai):

    print("AGARI件数一致: False")

    raise SystemExit(1)

print("AGARI件数一致: True")
print()


# --------------------------------------------------
# 内容比較
# --------------------------------------------------

mismatches = []

for i, (expected, actual) in enumerate(
    zip(expected_hupai, actual_hupai),
    start=1
):

    if expected != actual:

        mismatches.append({
            "agari": i,
            "expected": expected,
            "actual": actual,
        })


# --------------------------------------------------
# 結果
# --------------------------------------------------

print("=== hupai検証結果 ===")
print("比較したAGARI:", len(expected_hupai))
print("不一致数:", len(mismatches))


if not mismatches:

    print()
    print(
        "XMLのyakuから作成したhupaiと"
        "JSONのhupaiがすべて一致しました。"
    )

else:

    print()

    for item in mismatches:

        print("--------------------------------")
        print("AGARI:", item["agari"])

        print("XMLから計算:")
        for h in item["expected"]:
            print(
                " ",
                h["name"],
                h["fanshu"]
            )

        print("JSON:")
        for h in item["actual"]:
            print(
                " ",
                h.get("name"),
                h.get("fanshu")
            )
