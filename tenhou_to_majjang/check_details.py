import gzip
import xml.etree.ElementTree as ET
import json
import re
import tenhou_to_majiang as conv

xml_path = "../tenhou_mjlogs/2026062700gm-00a9-0000-0b1a0522&tw=0.mjlog"

with gzip.open(xml_path, "rb") as f:
    root = ET.fromstring(f.read())

with open("output.json", encoding="utf-8") as f:
    data = json.load(f)

expected = []
oya = 0
last_zimo = [None] * 4
reach = [False] * 4

for elem in root.iter():
    tag = elem.tag

    if tag == "INIT":
        oya = int(elem.attrib["oya"])
        last_zimo = [None] * 4
        reach = [False] * 4

    elif tag == "REACH":
        player = int(elem.attrib["who"])
        if elem.attrib["step"] == "1":
            reach[player] = True

    elif re.fullmatch(r"[TUVW]\d+", tag):
        player = "TUVW".index(tag[0])
        tile_id = int(tag[1:])
        last_zimo[player] = tile_id

        expected.append({
            "zimo": {
                "l": (player - oya + 4) % 4,
                "p": conv.pai(tile_id)
            }
        })

    elif re.fullmatch(r"[DEFG]\d+", tag):
        player = "DEFG".index(tag[0])
        tile_id = int(tag[1:])

        tile = conv.pai(tile_id)
        if last_zimo[player] == tile_id:
            tile += "_"

        if reach[player]:
            tile += "*"
            reach[player] = False

        expected.append({
            "dapai": {
                "l": (player - oya + 4) % 4,
                "p": tile
            }
        })

    elif tag == "N":
        player = int(elem.attrib["who"])
        expected.append({
            "fulou": {
                "l": (player - oya + 4) % 4,
                "m": conv.mianzi(int(elem.attrib["m"]))
            }
        })

actual = [
    event for event in data["log"]
    if any(k in event for k in ("zimo", "dapai", "fulou"))
]

print("XMLから生成:", len(expected))
print("JSON:", len(actual))
print("イベント数一致:", len(expected) == len(actual))

mismatches = []
for i, (x, j) in enumerate(zip(expected, actual)):
    if x != j:
        mismatches.append((i, x, j))

print("内容の不一致数:", len(mismatches))

for i, x, j in mismatches[:20]:
    print(f"\nイベント {i}")
    print("期待値:", x)
    print("JSON  :", j)

if len(expected) != len(actual):
    print("イベント数が異なるため、全件の比較はできていません。")
elif not mismatches:
    print("ツモ・打牌・鳴きの内容はすべて一致しました。")
