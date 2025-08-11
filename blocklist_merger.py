import requests
import subprocess
import os
import sys
import time
import argparse
from typing import Set, Tuple
from tqdm import tqdm

"""
Tool to merge multiple blocklists into one with ping verification and git integration
Usage: python script.py lists_file.txt output_file.txt [--existing-domains existing.txt] [--max-new 1000] [--skip-ping]
"""

def clean_domain(line: str) -> str:
    """Clean and extract domain from various blocklist formats"""
    domain = line.strip()
    
    # Skip comments and empty lines
    if not domain or domain.startswith("#") or domain.startswith("!"):
        return ""
    
    # Handle different prefixes
    prefixes_to_remove = ["0.0.0.0 ", "127.0.0.1 ", "||"]
    for prefix in prefixes_to_remove:
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
            break
    
    # Remove suffixes
    if "^" in domain:
        domain = domain.split("^")[0]
    
    # Take only the first part if there are spaces
    if " " in domain:
        domain = domain.split(" ")[0]
    
    # Basic domain validation
    domain = domain.strip()
    if domain and "." in domain and not domain.startswith("."):
        return domain.lower()  # Normalize to lowercase
    
    return ""

def ping_domain(domain: str, verbose: bool = True) -> bool:
    """Check if domain is online using ping"""
    try:
        # Use ping -c 1 (Linux/Mac) or ping -n 1 (Windows)
        cmd = ["ping", "-c", "1", domain] if os.name != 'nt' else ["ping", "-n", "1", domain]
        
        if verbose:
            print(f"Pinging {domain}...", end=" ")
        
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        success = result.returncode == 0
        
        if verbose:
            print("ONLINE" if success else "OFFLINE")
            
        return success
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        if verbose:
            print("TIMEOUT")
        return False

def load_existing_domains(input_file: str) -> Set[str]:
    """Load existing domains from input file"""
    existing_domains = set()
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist. Starting with empty set.")
        return existing_domains
    
    try:
        with open(input_file, "r") as f:
            for line in f:
                domain = clean_domain(line)
                if domain:
                    existing_domains.add(domain)
        
        print(f"Loaded {len(existing_domains):,} existing domains from {input_file}")
    except Exception as e:
        print(f"Error reading input file {input_file}: {e}")
    
    return existing_domains

def download_blocklist(url: str, timeout: int = 20) -> tuple[Set[str], int, int]:
    """Download and parse a blocklist from URL"""
    domains = set()
    total_lines = 0
    valid_domains = 0
    
    try:
        print(f"Downloading: {url[:60]}...")
        response = requests.get(url, timeout=timeout)
        
        if response.status_code == 200:
            lines = response.text.split("\n")
            total_lines = len(lines)
            
            for line in tqdm(lines, desc="Processing lines", leave=False):
                domain = clean_domain(line)
                if domain:
                    domains.add(domain)  # set automatically handles duplicates
                    valid_domains += 1
        else:
            print(f"Failed to download {url}: HTTP {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
    except Exception as e:
        print(f"Unexpected error processing {url}: {e}")
    
    return domains, total_lines, valid_domains

def git_operations(output_file: str, new_domains_count: int):
    """Perform git operations: add, commit, pull, push"""
    try:
        print(f"\n{'='*50}")
        print("PERFORMING GIT OPERATIONS")
        print(f"{'='*50}")
        
        # Git add
        print("Adding output file to git...")
        subprocess.run(["git", "add", output_file], check=True)
        
        # Git commit
        commit_message = f"Update blocklist: added {new_domains_count:,} new domains"
        print(f"Committing changes: {commit_message}")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # Git pull
        print("Pulling latest changes...")
        subprocess.run(["git", "pull"], check=True)
        
        # Git push
        print("Pushing changes...")
        subprocess.run(["git", "push"], check=True)
        
        print("Git operations completed successfully")
        
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        print("You may need to resolve conflicts manually or check git status")
    except FileNotFoundError:
        print("Git command not found. Make sure git is installed and in PATH")

def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Merge multiple blocklists with ping verification and git integration')
        parser.add_argument('lists_file', help='File containing blocklist URLs to download from')
        parser.add_argument('output_file', help='Output file path for the merged blocklist')
        parser.add_argument('--existing-domains', help='File with existing domains to merge with (optional)')
        parser.add_argument('--timeout', type=int, default=20, help='Request timeout in seconds')
        parser.add_argument('--max-new', type=int, default=1000, help='Maximum number of new domains to add')
        parser.add_argument('--skip-ping', action='store_true', help='Skip ping verification for new domains')
        parser.add_argument('--no-git', action='store_true', help='Skip git operations')
        args = parser.parse_args()
        
        lists_file = args.lists_file
        output_file = args.output_file
        
        # Load existing domains if specified
        existing_domains = set()
        if args.existing_domains:
            existing_domains = load_existing_domains(args.existing_domains)
        elif os.path.exists(output_file):
            print(f"Loading existing domains from output file: {output_file}")
            existing_domains = load_existing_domains(output_file)
        else:
            print("No existing domains file specified, starting fresh")
        
        # Check for lists file
        if not os.path.exists(lists_file):
            print(f"Lists file {lists_file} does not exist!")
            return
        
        # Read blocklist URLs
        with open(lists_file, "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        
        if not urls:
            print(f"No URLs found in {lists_file}. Please add some blocklist URLs.")
            return
        
        print(f"Found {len(urls)} blocklist URLs:")
        for url in urls:
            print(f"  - {url}")
        
        # Collect all domains
        all_downloaded_domains = set()
        total_lines_processed = 0
        total_valid_domains = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing blocklist...")
            domains, lines_count, valid_count = download_blocklist(url, timeout=args.timeout)
            
            all_downloaded_domains.update(domains)
            total_lines_processed += lines_count
            total_valid_domains += valid_count
            
            print(f"  Lines processed: {lines_count:,}")
            print(f"  Valid domains found: {valid_count:,}")
            
            # Brief pause between downloads to be respectful
            if i < len(urls):
                time.sleep(1)
        
        # Find new domains
        new_domains = all_downloaded_domains - existing_domains
        print(f"\nFound {len(new_domains):,} new domains (not in existing set)")
        
        # Limit new domains if specified
        if len(new_domains) > args.max_new:
            print(f"Limiting to {args.max_new:,} new domains as specified")
            new_domains = set(list(new_domains)[:args.max_new])
        
        # Ping verification for new domains
        verified_new_domains = set()
        if not args.skip_ping and new_domains:
            print(f"\nVerifying {len(new_domains):,} new domains with ping...")
            
            for i, domain in enumerate(new_domains, 1):
                print(f"[{i}/{len(new_domains)}] ", end="")
                if ping_domain(domain, verbose=True):
                    verified_new_domains.add(domain)
                # Small delay to avoid overwhelming the network
                time.sleep(0.1)
            
            print(f"\n{len(verified_new_domains):,} domains responded to ping")
            print(f"{len(new_domains) - len(verified_new_domains):,} domains did not respond")
        else:
            if args.skip_ping:
                print("Skipping ping verification as requested")
            verified_new_domains = new_domains
        
        # Combine existing and new verified domains
        final_domains = existing_domains | verified_new_domains
        sorted_domains = sorted(final_domains)
        
        # Calculate and display statistics
        print(f"\n{'='*50}")
        print(f"PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Existing domains: {len(existing_domains):,}")
        print(f"Total lines processed: {total_lines_processed:,}")
        print(f"Valid domains downloaded: {total_valid_domains:,}")
        print(f"New domains found: {len(new_domains):,}")
        if not args.skip_ping:
            print(f"New domains verified online: {len(verified_new_domains):,}")
        print(f"Final unique domains: {len(sorted_domains):,}")
        
        # Write to output file
        print(f"\nWriting {len(sorted_domains):,} unique domains to {output_file}...")
        with open(output_file, "w") as f:
            f.write("# Merged blocklist - duplicates removed\n")
            f.write(f"# Generated from {len(urls)} sources\n")
            f.write(f"# Existing domains: {len(existing_domains):,}\n")
            f.write(f"# New domains added: {len(verified_new_domains):,}\n")
            f.write(f"# Total unique domains: {len(sorted_domains):,}\n")
            if not args.skip_ping:
                f.write(f"# New domains verified online: {len(verified_new_domains):,}\n")
            f.write("\n")
            
            for domain in tqdm(sorted_domains, desc="Writing domains"):
                f.write(domain + "\n")
        
        print(f"Successfully wrote {len(sorted_domains):,} unique domains to {output_file}")
        print(f"   Added {len(verified_new_domains):,} new verified domains")
        
        # Perform git operations unless disabled
        if not args.no_git and len(verified_new_domains) > 0:
            git_operations(output_file, len(verified_new_domains))
        elif len(verified_new_domains) == 0:
            print("No new domains to commit.")
        
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        if 'existing_domains' in locals() and 'verified_new_domains' in locals():
            print("Saving partial results...")
            final_domains = existing_domains | verified_new_domains
            sorted_domains = sorted(final_domains)
            
            with open(output_file, "w") as f:
                f.write("# Partial merged blocklist (interrupted)\n")
                f.write(f"# Existing domains: {len(existing_domains):,}\n")
                f.write(f"# New domains added before interruption: {len(verified_new_domains):,}\n")
                f.write(f"# Total domains: {len(sorted_domains):,}\n")
                f.write("\n")
                for domain in sorted_domains:
                    f.write(domain + "\n")
            
            print(f"Saved {len(sorted_domains):,} unique domains to {output_file}")
            print(f"   ({len(verified_new_domains):,} new domains were added)")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()