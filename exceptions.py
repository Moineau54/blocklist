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
            # Preserve blank lines and full-line comments
            if not line:
                last_was_blank = True
                output.append("")  # Append blank line explicitly
                continue

            if line.startswith("#"):
                if last_was_blank:
                    output.append("")  # Add a blank line before comments
                output.append(line)
                last_was_blank = False
                continue

            # Handle inline comments and normalize domain
            if "#" in line:
                domain, comment = map(str.strip, line.split("#", 1))
            else:
                domain, comment = line, None

            # Normalize domain
            domain = domain.lower().replace("https://", "").replace("http://", "")

            if domain in exceptions_domains:
                continue

            # Insert comment block if needed
            if comment:
                if not last_was_blank:
                    output.append("")
                output.append(f"# {comment}")
                last_was_blank = False
                
            # Append the domain
            output.append(domain)
            last_was_blank = False

    # Remove duplicates while retaining order
    seen = set()
    output_ = []
    line = ""
    for line in output:
        if line != "":
            if line and line not in seen:
                seen.add(line)
                output_.append(line)
        else:
            output_.append(line)

    # Write back safely
    line = ""
    with open(filename, "w") as f:
        for line in output_:
            if line != "":
                if line.startswith("#"):
                    f.write(f"\n\n{line}")
                else:
                    f.write(f"\n{line}")
                

