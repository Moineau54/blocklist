from pathlib import Path

src = Path("zoophilia.txt")
dst = Path("zoophilia.txt")

# read, dedupe with a set, sort, and write
with src.open("r", encoding="utf-8") as f:
    # strip newline/whitespace and ignore empty lines
    items = {line.strip() for line in f if line.strip()}

sorted_items = sorted(items)

with dst.open("w", encoding="utf-8") as f:
    f.write("\n".join(sorted_items) + ("\n" if sorted_items else ""))


src = Path("porn.txt")
dst = Path("porn.txt")

# read, dedupe with a set, sort, and write
with src.open("r", encoding="utf-8") as f:
    # strip newline/whitespace and ignore empty lines
    items = {line.strip() for line in f if line.strip()}

sorted_items = sorted(items)

with dst.open("w", encoding="utf-8") as f:
    f.write("\n".join(sorted_items) + ("\n" if sorted_items else ""))
