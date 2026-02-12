from rich.progress import track

files = [
    "exceptions/exceptions.txt",
    "advertisement.txt",
    "fingerprinting.txt",
    "malware.txt",
    "phishing.txt",
    "socials.txt",
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

    seen_lines = set()
    with open(ublock_origins_file, "w") as file_ublock:
        file_ublock.write("")  # Clear the file before writing

    for line in track(lines, description=f"Creating uBlock blocklist for: {file}"):
        line = line.strip()
        if line != "" and line not in seen_lines:
            seen_lines.add(line)  # Add the line to the set to avoid duplicates

            if line.startswith("#") and not line.startswith("##"):
                content = line.replace("#", "!")
                content = f"\n\n{content}"

            elif not line.startswith("##"):
                if file != "exceptions/exceptions.txt":
                    content = line.strip()
                    if content.startswith("# "):
                        content = f"! {content}"
                    else:
                        content = f"\n||{content}^$important"
                else:
                    content = line.strip()
                    if "# " in content:
                        if content.startswith("# "):
                            content = f"!{content}"
                        else:
                            comment = content.split(" # ")[1]
                            domain = content.split(" # ")[0]
                            content = f"\n! {comment}\n@@||{domain}"
                    else:
                        content = f"\n@@||{content}"

            elif line.startswith("##"):
                content = f"\n{line.strip()}"

            # Write the constructed content to the output file
            with open(ublock_origins_file, "a") as file_ublock_content:
                file_ublock_content.write(content)

    print(f"Created {ublock_origins_file}")

print("Done")
