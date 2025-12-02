import requests
import subprocess
import os
import sys
import argparse
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

print("DEBUG: Starting script...")

# Rich console imports
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
    print("DEBUG: Rich imports successful")
except ImportError as e:
    print(f"DEBUG: Rich import failed: {e}")
    sys.exit(1)

# Initialize Rich console
console = Console()
print("DEBUG: Console initialized")

def main():
    print("DEBUG: Entering main function")
    
    try:
        parser = argparse.ArgumentParser(description='Merge blocklists into a single output file.')
        
        # Required arguments
        parser.add_argument('input_file', help='File containing URLs of blocklists to merge')
        parser.add_argument('output_file', help='Output file for the merged blocklist')
        
        # Optional arguments
        parser.add_argument('--workers', '-w', type=int, default=10,
                           help='Number of worker threads (default: 10)')
        parser.add_argument('--timeout', '-t', type=float, default=5.0,
                           help='Timeout for domain fetch (default: 5.0)')
        
        print("DEBUG: Parsing arguments...")
        args = parser.parse_args()
        print(f"DEBUG: Arguments parsed successfully: {args}")
        
        # Check if input file exists
        if not os.path.exists(args.input_file):
            print(f"ERROR: Input file does not exist: {args.input_file}")
            sys.exit(1)
        print(f"DEBUG: Input file exists: {args.input_file}")

        # Read blocklist URLs from input file
        print("DEBUG: Loading blocklist URLs...")
        blocklist_urls = load_blocklist_urls(args.input_file)
        print(f"DEBUG: Found {len(blocklist_urls)} URLs")

        # Fetch and merge domains from blocklists
        print("DEBUG: Fetching and merging domains from blocklists...")
        all_domains = fetch_domains(blocklist_urls, args.workers, args.timeout)
        
        # Write merged domains to the output file
        write_domains_to_file(all_domains, args.output_file)
        console.print(f"🎉 Merged {len(all_domains)} domains into {args.output_file}", style="bold green")
        print("DEBUG: Script completed successfully")
        
    except Exception as e:
        print(f"ERROR in main(): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def fetch_domains(urls: List[str], workers: int, timeout: float) -> set[str]:
    """Fetch domains from all blocklist URLs and return a set of unique domains."""
    all_domains = set()  # Use a set to filter duplicates
    
    def fetch_blocklist(url):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            # Extract domains from the response
            domains = {
                clean_domain(line)
                for line in response.text.splitlines()
                if clean_domain(line)  # Ensure only valid cleaned domains are added
            }
            return domains
        except Exception as e:
            console.print(f"❌ Error fetching {url}: {e}", style="red")
            return set()
    
    # Create progress bar for fetching
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        transient=False
    ) as progress:
        
        task = progress.add_task("Fetching blocklists", total=len(urls))
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_url = {executor.submit(fetch_blocklist, url): url for url in urls}
            
            for future in as_completed(future_to_url):
                domains = future.result()
                all_domains.update(domains)  # Use set to keep it unique
                progress.update(task, advance=1)
                
    return all_domains


def load_blocklist_urls(filename: str) -> List[str]:
    """Load blocklist URLs from input file"""
    urls = []
    with open(filename, 'r') as f:
        for line in f:
            url = line.strip()
            if url and not url.startswith('#'):
                urls.append(url)
    return urls


def clean_domain(line: str) -> str:
    """Clean domain line by removing unwanted characters and specific patterns."""
    line = line.strip()

    # Skip comments
    if line.startswith('#'):
        return ''
    
    # Remove unwanted prefixes and characters
    prefixes = ['0.0.0.0 ', '127.0.0.1 ', '||', '|', '.', '*.']
    for prefix in prefixes:
        if line.startswith(prefix):
            line = line[len(prefix):].strip()
    
    # Remove " CNAME ." if present
    line = line.replace(" CNAME .", "")
    
    # Remove trailing characters and suffixes
    line = line.split('^')[0]  # Remove uBlock origin suffix
    line = line.split(' ')[0]  # Remove comments
    line = line.split('\t')[0]  # Remove tabs
    line = line.split('#')[0]  # Remove inline comments
    
    # Remove any remaining unwanted characters
    unwanted_chars = ['^', '$', '*', '/', '?']
    for char in unwanted_chars:
        line = line.replace(char, '')
    
    return line.strip()


def write_domains_to_file(domains: set[str], filename: str):
    """Append new domains to output file."""
    with open(filename, 'a') as f:
        for domain in sorted(domains):  # Sort domains for consistent output
            f.write(f"{domain}\n")


if __name__ == "__main__":
    print("DEBUG: Script starting...")
    main()
