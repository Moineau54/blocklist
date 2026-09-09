import argparse
import sys
import urllib.error
import urllib.request
from collections import defaultdict

from rich.console import Console
from rich.progress import track

console = Console()

BASE_URL = "https://raw.githubusercontent.com/drb-ra/C2IntelFeeds/master/feeds/"

FEEDS = {
    "7day": "domainC2s-filter-abused.csv",
    "7day-unfiltered": "domainC2s.csv",
    "30day": "domainC2s-30day-filter-abused.csv",
    "30day-unfiltered": "domainC2s-30day.csv",
    "90day": "domainC2s-90day-filter-abused.csv",
    "90day-unfiltered": "domainC2s-90day.csv",
}


def fetch_feed(name: str, timeout: float) -> str:
    url = BASE_URL + FEEDS[name]
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def parse_feed(text: str) -> dict[str, set[str]]:
    """Group domains by their reported IOC description."""
    grouped = defaultdict(set)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domain, _, ioc = line.partition(",")
        domain = domain.strip().lower()
        ioc = ioc.strip() or "C2IntelFeeds"
        if domain:
            grouped[ioc].add(domain)
    return grouped


def load_existing_domains(filename: str) -> set[str]:
    existing = set()
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    existing.add(line.lower())
    except FileNotFoundError:
        pass
    return existing


def append_domains(filename: str, grouped: dict[str, set[str]], existing: set[str]) -> int:
    added = 0
    with open(filename, "a") as f:
        for ioc in track(sorted(grouped), description=f"writing new domains to {filename}"):
            new_domains = sorted(d for d in grouped[ioc] if d not in existing)
            if not new_domains:
                continue
            f.write(f"\n# {ioc} (C2IntelFeeds)\n")
            for domain in new_domains:
                f.write(f"{domain}\n")
                existing.add(domain)
                added += 1
    return added


def main():
    parser = argparse.ArgumentParser(
        description="Fetch C2 domains from drb-ra/C2IntelFeeds and append new ones to malware.txt"
    )
    parser.add_argument(
        "--windows",
        nargs="+",
        choices=FEEDS.keys(),
        default=["7day", "7day-unfiltered", "30day", "30day-unfiltered", "90day", "90day-unfiltered"],
        help="Feed time windows to fetch and merge (default: all windows, filtered and unfiltered)",
    )
    parser.add_argument(
        "--output", default="malware.txt", help="Output file (default: malware.txt)"
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="HTTP timeout in seconds (default: 10.0)"
    )
    args = parser.parse_args()

    grouped: dict[str, set[str]] = defaultdict(set)
    for window in args.windows:
        console.print(f"[bold cyan]Fetching {window} feed...[/bold cyan]")
        try:
            text = fetch_feed(window, args.timeout)
        except (urllib.error.URLError, TimeoutError) as e:
            console.print(f"[bold red]Failed to fetch {window} feed: {e}[/bold red]")
            sys.exit(1)

        for ioc, domains in parse_feed(text).items():
            grouped[ioc].update(domains)

    total_fetched = sum(len(v) for v in grouped.values())
    console.print(f"[green]Fetched {total_fetched} unique domains across {len(grouped)} IOC categories[/green]")

    existing = load_existing_domains(args.output)
    added = append_domains(args.output, grouped, existing)

    console.print(f"[bold green]Added {added} new domains to {args.output}[/bold green]")


if __name__ == "__main__":
    main()
