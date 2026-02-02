from rich.progress import track

files = [
    "exceptions/exceptions.txt",
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
    "forums.txt",
    "csam.txt",
    "zoophilia.txt",
    "all_lists.txt",
]

for file in files:
    base_name = file.split(".")[0]
    ublock_origins_file = f"{base_name}_ublock.txt"

    with open(file, "r") as f:
        lines = f.readlines()

    content = ""
    with open(ublock_origins_file, "w") as file_ublock:
        file_ublock.write("")
    for line in track(lines, description=f"creating ublock blocklist for: {file}"):
        line = line.strip()
        if line != "":
            if line.startswith("#") and not line.startswith("##"):
                content = line.strip().replace("#", "!")
                content = f"\n\n{content}"
            elif not line.startswith("##"):
                if not file == "exceptions/exceptions.txt":
                    content = line.strip()
                    content = f"\n||{content}^$important"
                else:
                    content = line.strip()
                    if content.__contains__("# "):
                        if content.startswith("# "):
                            content = f"!{content}"
                        elif content.__contains__(" # "):
                            content = f"\n@@||{content.replace(" # ", "^ ! ")}"
                    else:
                        content = f"\n@@||{content}^"

            elif line.startswith("##"):
                content = f"\n{line.strip()}"

            with open(ublock_origins_file, "a") as file_ublock_content:
                file_ublock_content.write(content)
    print(f"created {ublock_origins_file}")


print("done")
