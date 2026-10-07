import gzip
import json
import xml.etree.ElementTree as ET

import tenhou_to_majiang as conv


INPUT_XML = "../tenhou_mjlogs/2026062700gm-00a9-0000-0b1a0522&tw=0.mjlog"
INPUT_JSON = "output.json"


def find_hule_objects(obj):
    """
    JSONの中を再帰的に探して、huleオブジェクトを順番に取り出す。
    """
    result = []

    if isinstance(obj, dict):
        if "hule" in obj and isinstance(obj["hule"], dict):
            result.append(obj["hule"])

        for value in obj.values():
            result.extend(find_hule_objects(value))

    elif isinstance(obj, list):
        for value in obj:
            result.extend(find_hule_objects(value))

    return result


def make_expected_hule(attr, oya):
    """
    XMLのAGARI属性から、huleの期待値を作る。

    ここでは conv.hule() は使用しない。
    """

    who = int(attr["who"])
    from_who = int(attr["fromWho"])

    # 0 = 東家(親)として相対化
    l = (who + 4 - oya) % 4

    # 放銃者
    if who != from_who:
        baojia = (from_who + 4 - oya) % 4
    else:
        baojia = None

    # 裏ドラ
    if "doraHaiUra" in attr and attr["doraHaiUra"]:
        fubaopai = [
            conv.pai(int(x))
            for x in attr["doraHaiUra"].split(",")
            if x != ""
        ]
    else:
        fubaopai = None

    # 和了点
    ten = [int(x) for x in attr["ten"].split(",")]
    defen = ten[1]

    expected = {
        "l": l,
        "baojia": baojia,
        "fubaopai": fubaopai,
        "defen": defen,
    }

    # 局収支
    sc = [int(x) for x in attr["sc"].split(",")]

    # sc は
    # [点数, 増減, 点数, 増減, ...]
    fenpei = [
        sc[1] * 100,
        sc[3] * 100,
        sc[5] * 100,
        sc[7] * 100,
    ]

    # 親を0番にするため回転
    fenpei = fenpei[oya:] + fenpei[:oya]

    expected["fenpei"] = fenpei

    # 役満
    if "yakuman" in attr and attr["yakuman"]:
        yakuman_list = [
            x for x in attr["yakuman"].split(",")
            if x != ""
        ]

        expected["damanguan"] = len(yakuman_list)

    else:
        # 通常役
        expected["fu"] = ten[0]

        yaku_parts = [
            int(x) for x in attr.get("yaku", "").split(",")
            if x != ""
        ]

        # yaku = [役ID, 翻数, 役ID, 翻数, ...]
        fanshu = 0

        for i in range(1, len(yaku_parts), 2):
            fanshu += yaku_parts[i]

        expected["fanshu"] = fanshu

    return expected


def compare_values(expected, actual, index):
    """
    1つのhuleについて比較する。
    """

    keys = [
        "l",
        "baojia",
        "fubaopai",
        "fu",
        "fanshu",
        "damanguan",
        "defen",
        "fenpei",
    ]

    mismatches = []

    for key in keys:
        expected_value = expected.get(key)
        actual_value = actual.get(key)

        if expected_value != actual_value:
            mismatches.append({
                "index": index,
                "field": key,
                "expected": expected_value,
                "actual": actual_value,
            })

    return mismatches


# --------------------------------------------------
# XML読み込み
# --------------------------------------------------

with gzip.open(INPUT_XML, "rb") as f:
    root = ET.parse(f).getroot()


# --------------------------------------------------
# JSON読み込み
# --------------------------------------------------

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)


json_hules = find_hule_objects(data)

print("JSONのhule件数:", len(json_hules))


# --------------------------------------------------
# XMLのAGARIを調べる
# --------------------------------------------------

xml_hules = []

current_oya = None

for elem in root.iter():

    # 局開始
    if elem.tag == "INIT":
        current_oya = int(elem.attrib["oya"])

    # 和了
    elif elem.tag == "AGARI":

        if current_oya is None:
            print("ERROR: AGARIより前にINITがありません")
            raise SystemExit(1)

        expected = make_expected_hule(
            elem.attrib,
            current_oya
        )

        xml_hules.append({
            "expected": expected,
            "attr": elem.attrib,
            "oya": current_oya,
        })


print("XMLのAGARI件数:", len(xml_hules))
print()


# --------------------------------------------------
# 件数確認
# --------------------------------------------------

if len(xml_hules) != len(json_hules):
    print("ERROR: AGARI件数とhule件数が一致しません")

    print(
        "XML:",
        len(xml_hules),
        "JSON:",
        len(json_hules)
    )

    raise SystemExit(1)


print("AGARI件数一致: True")
print()


# --------------------------------------------------
# 内容確認
# --------------------------------------------------

all_mismatches = []

for i, (xml_item, json_hule) in enumerate(
    zip(xml_hules, json_hules)
):

    mismatches = compare_values(
        xml_item["expected"],
        json_hule,
        i
    )

    all_mismatches.extend(mismatches)


# --------------------------------------------------
# 結果表示
# --------------------------------------------------

print("=== 検証結果 ===")

print(
    "比較したhule:",
    len(xml_hules)
)

print(
    "不一致数:",
    len(all_mismatches)
)

if len(all_mismatches) == 0:

    print()
    print(
        "AGARIから計算した"
        "l / baojia / fubaopai / fu / fanshu / "
        "damanguan / defen / fenpei"
    )

    print(
        "とJSONのhuleがすべて一致しました。"
    )

else:

    print()
    print("不一致の詳細:")

    for item in all_mismatches:
        print()
        print("AGARI番号:", item["index"])
        print("項目:", item["field"])
        print("XMLから計算:", item["expected"])
        print("JSON:", item["actual"])
