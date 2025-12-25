exceptions_domains = [
    "youtube.com",
    "reddit.com",
    "x.com",
    "example.com", # example
    "patreon.com",
    "127.0.0.1",
    "localhost",
    "codeload.github.com",
    "api.chess.com" # for chess.com to work
]

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
    "csam.txt"
]
for list_ in lists:
    print(f"verifying {list_} for exceptions")
    content = []
    end_content = []
    with open(list_, "r") as f:
        content = f.read().split("\n")
    
    for i, line in enumerate(content):
        if line not in exceptions_domains:
            if i == len(content) - 1 and line == "":
                end_content.append(line)
            else:
                end_content.append(line + "\n")
    
    with open(list_, "w") as f:
        for line_to_write in end_content:
            f.write(line_to_write)
