import argparse
from rich.progress import track
from rich.console import Console


console = Console()


def process_file(file):
    with open(file, "r") as f:
        lines = f.readlines()
        
    console.print(f"[bold green]{file} {len(lines)} lines to process[/bold green]")

    unique_lines = []
    

    with open(file, "w") as f:
        f.write("")
        
    for line in track(lines, description=f"Processing {file}..."):
        if line.strip() and line not in unique_lines:
            unique_lines.append(line)
            with open(file, "a") as f:
                f.write(line)

    console.print(f"[bold yellow]Processed {len(unique_lines)} unique lines in {file}[/bold yellow]")


def main():
    parser = argparse.ArgumentParser(description="Process text files for unique lines.")
    parser.add_argument('-f', '--file', type=str, help='Specific file to process', required=False)

    args = parser.parse_args()

    default_files = [
        "advertisement.txt",
        "fingerprinting.txt",
        "forums.txt",
        "malware.txt",
        "porn.txt",
        "spam.txt",
        "suspicious.txt",
        "telemetry.txt",
        "to_monitor.txt",
        "tracking.txt",
        "zoophilia.txt"
    ]


    if args.file:
        process_file(args.file)
    else:
        for file in default_files:
            process_file(file)

    console.print("[bold yellow]Done![/bold yellow]")

if __name__ == "__main__":
    main()
