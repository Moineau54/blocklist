from pathlib import Path


sources:  list['Path'] = [
    Path('advertisement.txt'),
    Path('ai_girlfriend_chatbots.txt'),
    Path('all_lists.txt'),
    Path('fingerprinting.txt'),
    Path('gambling.txt'),
    Path('phishing.txt'),
    Path('porn.txt'),
    Path('socials.txt'),
    Path('spam.txt'),
    Path('telemetry.txt'),
    Path('to_block_bydefault.txt'),
    Path('to_monitor.txt'),
    Path('tracking.txt')
]
for src in sources:
    # read, dedupe with a set, sort, and write
    with src.open("r", encoding="utf-8") as f:
        # strip newline/whitespace and ignore empty lines
        items = {line.strip() for line in f if line.strip()}

    sorted_items = sorted(items)

    with src.open("w", encoding="utf-8") as f:
        f.write("\n".join(sorted_items) + ("\n" if sorted_items else ""))
