import gzip
import xml.etree.ElementTree as ET
import json
import re
from collections import Counter

xml_path = "../tenhou_mjlogs/2026062700gm-00a9-0000-0b1a0522&tw=0.mjlog"

with gzip.open(xml_path, "rb") as f:
    root = ET.fromstring(f.read())

with open("output.json", encoding="utf-8") as f:
    data = json.load(f)

xml_events = []

for elem in root.iter():
    tag = elem.tag

    if re.fullmatch(r"[TUVW]\d+", tag):
        xml_events.append("zimo")
    elif re.fullmatch(r"[DEFG]\d+", tag):
        xml_events.append("dapai")
    elif tag == "N":
        xml_events.append("fulou")
    elif tag == "AGARI":
        xml_events.append("hule")

json_events = []
for event in data["log"]:
    for key in ("zimo", "dapai", "fulou", "hule"):
        if key in event:
            json_events.append(key)
            break

print("XML:", Counter(xml_events))
print("JSON:", Counter(json_events))
print("イベント数一致:", len(xml_events) == len(json_events))
print("順序一致:", xml_events == json_events)

if xml_events != json_events:
    for i, (x, j) in enumerate(zip(xml_events, json_events)):
        if x != j:
            print("最初の不一致:", i, "XML:", x, "JSON:", j)
            break

    if len(xml_events) != len(json_events):
        print("XMLのイベント数:", len(xml_events))
        print("JSONのイベント数:", len(json_events))


