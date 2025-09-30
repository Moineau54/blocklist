exceptions_domains = [
    "youtube.com",
    "reddit.com",
    "example.com" # example
]
lists = [
    "advertisement.txt",
    "fingerprinting.txt",
    "malware.txt",
    "phishing.txt",
    "porn.txt",
    "spam.txt",
    "suspicious.txt",
    "telemetry.txt",
    "to_monitor.txt",
    "tracking.txt"
]
for list_ in lists:
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
