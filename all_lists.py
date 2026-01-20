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
        if line != "" or not line.startswith("#"):
            if line.strip() not in parsed_entries:
                if line.strip().__contains__("http"):
                    parsed_entries.add(
                        line.strip().replace("http://", "").replace("https://", "")
                    )
                else:
                    parsed_entries.add(line.strip())


sorted(parsed_entries)

with open("all_lists.txt", "a") as f:
    for entry in track(
        parsed_entries, description="writing all entries to all_lists.txt"
    ):
        if entry != "":
            f.write(f"\n{entry}")
