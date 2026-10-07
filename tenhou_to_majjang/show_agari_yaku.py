import gzip
import xml.etree.ElementTree as ET

INPUT_XML = "../tenhou_mjlogs/2026062700gm-00a9-0000-0b1a0522&tw=0.mjlog"

with gzip.open(INPUT_XML, "rb") as f:
    root = ET.parse(f).getroot()

count = 0

for elem in root.iter():
    if elem.tag != "AGARI":
        continue

    count += 1

    print("================================")
    print("AGARI", count)

    print("who      =", elem.attrib.get("who"))
    print("fromWho  =", elem.attrib.get("fromWho"))

    print("yaku     =", elem.attrib.get("yaku"))
    print("yakuman  =", elem.attrib.get("yakuman"))

    print()
