import json

INPUT_JSON = "output.json"

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

count = 0

def find_hule(obj):
    global count

    if isinstance(obj, dict):
        if "hule" in obj and isinstance(obj["hule"], dict):
            count += 1

            print("================================")
            print("hule", count)

            hupai = obj["hule"].get("hupai", [])

            for h in hupai:
                print(
                    "name =",
                    h.get("name"),
                    ", fanshu =",
                    h.get("fanshu")
                )

        for value in obj.values():
            find_hule(value)

    elif isinstance(obj, list):
        for value in obj:
            find_hule(value)


find_hule(data)
