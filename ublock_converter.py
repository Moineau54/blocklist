
files = [
    "advertisement.txt",
    "fingerprinting.txt",
    "malware.txt",
    "phishing.txt",
    "spam.txt",
    "suspicious.txt",
    "telemetry.txt",
    "to_monitor.txt",
    "tracking.txt"
]

for file in files:
    base_name = file.split(".")[0]
    print(f"processing {file}")
    ublock_origins_file = f"{base_name}_ublock.txt"

    with open(file, "r") as f:
        lines = f.readlines()
    
    content = ""
    with open(ublock_origins_file, "w") as file_ublock:
        file_ublock.write("")
    for line in lines:
        if line.startswith("#"):
            content = line.replace("#", "!")
        elif line != "\n":
            content = f"||{line.replace("\n", "")}^\n"
        else:
            content = line + "\n"
        
        with open(ublock_origins_file, "a") as file_ublock_content:
            file_ublock_content.write(content)
    print(f"created {ublock_origins_file}")

print("done")