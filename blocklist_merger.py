import requests
import subprocess
import os
import sys
import time
import argparse
from typing import Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

print("DEBUG: Starting script...")

# Rich console imports
try:
    from rich.console import Console
    from rich.text import Text
    from rich.progress import (
        Progress, 
        SpinnerColumn, 
        TextColumn, 
        BarColumn, 
        TaskProgressColumn,
        TimeRemainingColumn,
        MofNCompleteColumn
    )
    print("DEBUG: Rich imports successful")
except ImportError as e:
    print(f"DEBUG: Rich import failed: {e}")
    sys.exit(1)

"""
Tool to merge multiple blocklists into one with ping verification and git integration
Usage: python script.py lists_file.txt output_file.txt [--existing-domains existing.txt] [--max-new 1000] [--max-file-size 500000] [--workers 10] [--skip-ping] [--skip-git]
"""

# Initialize Rich console
console = Console()
print("DEBUG: Console initialized")

def main():
    print("DEBUG: Entering main function")
    
    try:
        parser = argparse.ArgumentParser(description='tests domains on blocklists to make a new blocklist')
        
        # Required arguments
        parser.add_argument('input_file', help='File containing URLs of blocklists to merge')
        parser.add_argument('output_file', help='Output file for the merged blocklist')
        
        # Optional arguments
        parser.add_argument('--workers', '-w', type=int, default=10,
                           help='Number of worker threads (default: 10)')
        parser.add_argument('--timeout', '-t', type=float, default=5.0,
                           help='Timeout in seconds for domain checks (default: 5.0)')
        parser.add_argument('--existing-domains', help='File with existing domains to exclude')
        parser.add_argument('--max-new', type=int, default=1000,
                           help='Maximum number of new domains to add (default: 1000)')
        parser.add_argument('--max-file-size', type=int, default=500000,
                           help='Maximum file size in bytes (default: 500000)')
        parser.add_argument('--skip-ping', action='store_true',
                           help='Skip ping verification of domains')
        parser.add_argument('--skip-git', action='store_true',
                           help='Skip git operations')
        
        print("DEBUG: Parsing arguments...")
        args = parser.parse_args()
        print(f"DEBUG: Arguments parsed successfully: {args}")
        
        # Check if input file exists
        if not os.path.exists(args.input_file):
            print(f"ERROR: Input file does not exist: {args.input_file}")
            sys.exit(1)
        print(f"DEBUG: Input file exists: {args.input_file}")
        
        # Read existing domains from output file if it exists
        print("DEBUG: Loading existing domains...")
        existing_domains = load_existing_domains(args.output_file)
        console.print(f"📚 Loaded {len(existing_domains)} existing domains from {args.output_file}", style="bold blue")
        
        # Read additional existing domains if provided
        if args.existing_domains:
            print("DEBUG: Loading additional existing domains...")
            additional_existing = load_existing_domains(args.existing_domains)
            existing_domains.update(additional_existing)
            console.print(f"📚 Loaded {len(additional_existing)} additional existing domains", style="bold blue")
        
        # Read blocklist URLs from input file
        print("DEBUG: Loading blocklist URLs...")
        blocklist_urls = load_blocklist_urls(args.input_file)
        print(f"DEBUG: Found {len(blocklist_urls)} URLs")
        
        # Fetch and process all blocklists
        print("DEBUG: Fetching domains from blocklists...")
        all_domains = fetch_and_clean_domains(blocklist_urls, args.workers, args.timeout)
        console.print(f"🌐 Fetched {len(all_domains)} total domains from blocklists", style="bold blue")
        
        # Remove duplicates and existing domains
        print("DEBUG: Removing duplicates...")
        new_domains = all_domains - existing_domains
        console.print(f"🔍 Found {len(new_domains)} new unique domains after removing duplicates and existing domains", style="bold blue")
        
        # Limit to max new domains
        if len(new_domains) > args.max_new:
            new_domains = set(list(new_domains)[:args.max_new])
            console.print(f"⚖️ Limited to {args.max_new} domains", style="bold blue")
        
        # Ping domains to verify they're online (unless skipped)
        if not args.skip_ping:
            print("DEBUG: Starting ping verification...")
            verified_domains = verify_domains_online_with_git(new_domains, args.workers, args.timeout, 
                                                             args.output_file, args.skip_git, existing_domains)
        else:
            print("DEBUG: Skipping ping verification...")
            verified_domains = new_domains
            # Write all at once if skipping ping
            write_domains_to_file(verified_domains, args.output_file)
            if not args.skip_git:
                git_commit_push(f"Added {len(verified_domains)} domains (ping skipped)")
        
        console.print(f"🎉 Added {len(verified_domains)} verified domains to {args.output_file}", style="bold green")
        print("DEBUG: Script completed successfully")
        
    except Exception as e:
        print(f"ERROR in main(): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def git_commit_push(commit_message: str):
    """Perform git add, commit, pull, and push operations"""
    try:
        # Git add
        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
        console.print("✅ Git add completed", style="bold green")
        
        # Git commit
        subprocess.run(['git', 'commit', '-m', commit_message], check=True, capture_output=True)
        console.print(f"✅ Git commit completed: {commit_message}", style="bold green")
        
        # Git pull
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"⚠️ Git pull warning: {result.stderr}", style="red")
        else:
            console.print("✅ Git pull completed", style="bold green")
        
        # Git push
        subprocess.run(['git', 'push'], check=True, capture_output=True)
        console.print("✅ Git push completed", style="bold green")
        
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Git operation failed: {e}", style="red")
    except Exception as e:
        console.print(f"❌ Git error: {e}", style="red")


def verify_domains_online_with_git(domains: set[str], workers: int, timeout: float, 
                                 output_file: str, skip_git: bool, existing_domains: set[str]) -> set[str]:
    """Ping domains to verify they're online with git commits every 20%, avoiding duplicates"""
    verified_domains = set()
    written_domains = existing_domains.copy()  # Track all domains written to avoid dupes
    lock = threading.Lock()
    
    domains_list = list(domains)
    total_domains = len(domains_list)
    
    # Calculate 20% intervals - NOTE: Now based on responding domains
    checkpoint_interval = max(1, total_domains // 5)  # Every 20%
    next_checkpoint = checkpoint_interval
    processed_count = 0  # Now only counts domains that respond
    
    # Create Rich progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False
    ) as progress:
        
        task = progress.add_task("Verifying responding domains", total=total_domains)
        
        def ping_domain(domain):
            nonlocal processed_count, next_checkpoint
            
            try:
                # Simple ping using subprocess
                result = subprocess.run(['ping', '-c', '1', '-W', str(int(timeout * 1000)), domain], 
                                      capture_output=True, timeout=timeout + 1)
                
                with lock:
                    # Only increment counter if domain responds
                    if result.returncode == 0:
                        processed_count += 1
                        progress.update(task, advance=1)
                        
                        # Double-check domain isn't already written (thread safety)
                        if domain not in written_domains:
                            verified_domains.add(domain)
                            written_domains.add(domain)
                            # Write domain immediately to file
                            write_single_domain_to_file(domain, output_file)
                            progress.console.print(f"✅ Added verified domain: {domain}", style="bold green")
                        else:
                            progress.console.print(f"⚠️ Skipped duplicate domain: {domain}", style="bold blue")
                        
                        # Check if we've reached a checkpoint (20% interval) - based on responding domains
                        if not skip_git and processed_count >= next_checkpoint:
                            verified_count = len(verified_domains)
                            commit_msg = f"Progress: {processed_count} domains responded and processed, {verified_count} verified"
                            progress.console.print(f"\n🔄 Reached {processed_count} responding domains - performing git operations...", style="bold blue")
                            git_commit_push(commit_msg)
                            next_checkpoint += checkpoint_interval
                    else:
                        # Domain didn't respond - just log it but don't increment counter
                        progress.console.print(f"❌ Domain did not respond: {domain}", style="red")
                
                return result.returncode == 0
                
            except Exception as e:
                with lock:
                    # Don't increment counter for exceptions either
                    progress.console.print(f"❌ Error pinging {domain}: {e}", style="red")
                return False
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(ping_domain, domain) for domain in domains_list]
            
            for future in as_completed(futures):
                future.result()
    
    # Final git commit if not skipped
    if not skip_git:
        console.print("\n🔄 Final git commit...", style="bold blue")
        git_commit_push(f"Completed: {len(verified_domains)} new domains verified and added")
    
    return verified_domains


def write_single_domain_to_file(domain: str, filename: str):
    """Append a single domain to output file"""
    with open(filename, 'a') as f:
        f.write(f"{domain}\n")


def load_existing_domains(filename: str) -> set[str]:
    """Load existing domains from file, create file if it doesn't exist"""
    if not os.path.exists(filename):
        # Create empty file
        with open(filename, 'w') as f:
            pass
        return set()
    
    domains = set()
    with open(filename, 'r') as f:
        for line in f:
            domain = line.strip()
            if domain and not domain.startswith('#'):
                # Clean domain to ensure consistent comparison
                clean_domain_name = clean_domain(domain)
                if clean_domain_name:
                    domains.add(clean_domain_name)
    return domains


def load_blocklist_urls(filename: str) -> list:
    """Load blocklist URLs from input file"""
    urls = []
    with open(filename, 'r') as f:
        for line in f:
            url = line.strip()
            if url and not url.startswith('#'):
                urls.append(url)
    return urls


def clean_domain(line: str) -> str:
    """Clean domain line by removing prefixes like 0.0.0.0, 127.0.0.1, ||, and unwanted characters like ^"""
    line = line.strip()
    
    # Skip comments
    if line.startswith('#'):
        return ''
    
    # Remove common prefixes
    prefixes = ['0.0.0.0 ', '127.0.0.1 ', '||', '|']
    for prefix in prefixes:
        if line.startswith(prefix):
            line = line[len(prefix):]
    
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


def fetch_and_clean_domains(urls: list, workers: int, timeout: float) -> set[str]:
    """Fetch domains from all blocklist URLs and clean them"""
    all_domains = set()
    
    def fetch_blocklist(url):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            domains = set()
            for line in response.text.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    cleaned = clean_domain(line)
                    if cleaned and '.' in cleaned and len(cleaned) > 3:  # Basic domain validation
                        domains.add(cleaned)
            return domains
        except Exception as e:
            console.print(f"❌ Error fetching {url}: {e}", style="red")
            return set()
    
    # Create Rich progress bar for fetching
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False
    ) as progress:
        
        task = progress.add_task("Fetching blocklists", total=len(urls))
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_url = {executor.submit(fetch_blocklist, url): url for url in urls}
            
            for future in as_completed(future_to_url):
                domains = future.result()
                all_domains.update(domains)
                progress.update(task, advance=1)
    
    return all_domains


def write_domains_to_file(domains: set[str], filename: str):
    """Append new domains to output file"""
    with open(filename, 'a') as f:
        for domain in sorted(domains):
            f.write(f"{domain}\n")


if __name__ == "__main__":
    print("DEBUG: Script starting...")
    main()