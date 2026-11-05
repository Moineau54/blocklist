#!/usr/bin/env python3
"""Sort blocklist entries, keeping '# ' sections in place."""

import sys
from pathlib import Path

# A section = the comment lines that open it + the entries under it
Section = tuple[list[str], list[str]]


def parse(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    comments: list[str] = []
    entries: list[str] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue  # blank lines are rebuilt on write
        if line.startswith("#"):
            # A comment after entries means a new section starts
            if entries:
                sections.append((comments, entries))
                comments, entries = [], []
            comments.append(line)
        else:
            entries.append(line)

    if comments or entries:
        sections.append((comments, entries))
    return sections


def sort_entries(entries: list[str]) -> list[str]:
    # dedupe (case-insensitive) and sort
    unique = {e.lower(): e for e in entries}
    return [unique[k] for k in sorted(unique)]


def render(sections: list[Section]) -> str:
    blocks = []
    for comments, entries in sections:
        blocks.append("\n".join(comments + sort_entries(entries)))
    return "\n\n".join(blocks) + "\n"


def main() -> None:
    blocklists: list[str] = sys.argv[1:] or [
        "advertisement.txt",
        "ai_girlfriend_chatbots.txt",
        "all_lists.txt",
        "fingerprinting.txt",
        "gambling.txt",
        "phishing.txt",
        "porn.txt",
        "socials.txt",
        "spam.txt",
        "telemetry.txt",
        "to_block_bydefault.txt",
        "to_monitor.txt",
        "tracking.txt",
        "exceptions/exceptions.txt",
        "malware.txt"
    ]
    for list_ in blocklists:
        path = Path(list_)
        if not path.is_file():
            print(f"skipped {list_}: not found", file=sys.stderr)
            continue
        sections = parse(path.read_text(encoding="utf-8").splitlines())
        path.write_text(render(sections), encoding="utf-8")
        print(f"sorted {list_}: {len(sections)} section(s)")


if __name__ == "__main__":
    main()
