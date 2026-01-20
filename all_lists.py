import rich
from rich.progress import track

lists = [
    "advertisement.txt",
    "fingerprinting.txt",
    "malware.txt",
    "phishing.txt",
    "spam.txt",
    "suspicious.txt",
    "telemetry.txt",
    "to_monitor.txt",
    "tracking.txt",
    "porn.txt",
    "zoophilia.txt",
    "csam.txt",
    "forums.txt",
]

with open("all_lists.txt", "w") as f:
    f.write("")

parsed_entries = set()

for file in lists:
    print(f"parsing {file}")
    with open(file, "r") as f:
        lines = f.readlines()

    for line in track(lines):
        line = line.strip()
        if line != '' and not line.startswith("#"):
            if line.strip() not in parsed_entries:
                if line.strip().__contains__("http"):
                    parsed_entries.add(
                        line.strip().replace("http://", "").replace("https://", "")
                    )
                else:
                    parsed_entries.add(line.strip())


entry_array = []
entry_array.extend(parsed_entries)
# for entry in track(parsed_entries, description="reordering entries"):
#     if entry.strip() not in entry_array:
#         entry_array.append(entry.strip)

entry_array.sort()

with open("all_lists.txt", "a") as f:
    for entry in track(
        entry_array, description="writing all entries to all_lists.txt"
    ):
        if entry != "":
            f.write(f"\n{entry}")
