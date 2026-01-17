exceptions_domains = {
    "youtube.com",
    "reddit.com",
    "x.com",
    "example.com",
    "patreon.com",
    "127.0.0.1",
    "localhost",
    "codeload.github.com",
    "api.chess.com",
    "client-metrics-cf.chess.com",
    "today",
    "255.255.255.255",
    "broadcasthost",
    "localdomain",
    "ipinfo.io",
    "crunchbase.com",
    "ft.com",
    "aol.com",
    "guce.aol.com",
    "search.aol.com",
}

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

for filename in lists:
    print(f"verifying {filename} for exceptions")

    output = []
    last_was_blank = True

    with open(filename, "r") as f:
        for raw in f:
            line = raw.strip()

            # Preserve blank lines
            if not line or line == "":
                last_was_blank = True
                continue

            # Full-line comment
            if line.startswith("#"):
                if last_was_blank:
                    output.append("")
                output.append(line)
                last_was_blank = False
                continue

            # Split inline comment
            if "#" in line and not line.startswith("#"):
                domain, comment = line.split("#", 1)
                domain = domain.strip()
                comment = comment.strip()
            else:
                domain, comment = line, None

            # Normalize domain
            domain = domain.replace("https://", "").replace("http://", "").strip()

            if domain in exceptions_domains:
                continue

            # Insert comment block if needed
            if comment:
                if not last_was_blank:
                    output.append("")
                output.append(f"# {comment}")
                last_was_blank = False

            # Write domain
            output.append(domain)
            last_was_blank = False

    # Write back safely
    with open(filename, "w") as f:
        f.write("\n".join(output).rstrip() + "\n")
