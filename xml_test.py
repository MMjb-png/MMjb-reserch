import gzip
import xml.etree.ElementTree as ET

file_path = "./tenhou_mjlogs/2026062700gm-00a9-0000-0b1a0522&tw=0.mjlog"

with gzip.open(file_path, "rt", encoding="utf-8") as f:
    xml_text = f.read()

root = ET.fromstring(xml_text)

print("ルート:", root.tag)

for elem in root:
    print(elem.tag, elem.attrib)