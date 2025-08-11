import requests
import subprocess
import os
import sys
import time
import argparse
from typing import Set, Tuple
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

"""
Tool to merge multiple blocklists into one with ping verification and git integration
Usage: python script.py lists_file.txt output_file.txt [--existing-domains existing.txt] [--max-new 1000] [--max-file-size 500000] [--skip-ping]
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

def load_existing_domains(input_file: str) -> tuple[Set[str], int]:
    """Load existing domains from input file and return count of new entries"""
    existing_domains = set()
    new_entries_count = 0
    
    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist. Starting with empty set.")
        return existing_domains, 0
    
    try:
        with open(input_file, "r") as f:
            for line in f:
                # Check for new entries count in header
                if line.startswith("# New domains added:"):
                    try:
                        new_entries_count = int(line.split(":")[1].strip().replace(",", ""))
                    except (IndexError, ValueError):
                        pass
                
                domain = clean_domain(line)
                if domain:
                    existing_domains.add(domain)
        
        print(f"Loaded {len(existing_domains):,} existing domains from {input_file}")
        if new_entries_count > 0:
            print(f"File contains {new_entries_count:,} new entries from previous runs")
    except Exception as e:
        print(f"Error reading input file {input_file}: {e}")
    
    return existing_domains, new_entries_count

def download_blocklists_parallel(urls: list, timeout: int, workers: int) -> tuple[Set[str], int, int]:
    """Download and parse multiple blocklists in parallel"""
    all_domains = set()
    total_lines = 0
    total_valid = 0
    
    # Thread-safe counters
    lock = threading.Lock()
    
    def download_single_url(url_info):
        url, index = url_info
        try:
            print(f"[{index+1}/{len(urls)}] Downloading: {url[:60]}...")
            domains, lines, valid = download_blocklist(url, timeout)
            
            with lock:
                nonlocal total_lines, total_valid
                domains_before = len(all_domains)
                all_domains.update(domains)
                domains_after = len(all_domains)
                
                new_unique = domains_after - domains_before
                duplicates = len(domains) - new_unique
                
                total_lines += lines
                total_valid += valid
                
                print(f"[{index+1}/{len(urls)}] Completed:")
                print(f"  Lines processed: {lines:,}")
                print(f"  Valid domains found: {valid:,}")
                print(f"  New unique domains: {new_unique:,}")
                if duplicates > 0:
                    print(f"  Duplicates skipped: {duplicates:,}")
                
            return domains, lines, valid
        except Exception as e:
            print(f"[{index+1}/{len(urls)}] Error downloading {url}: {e}")
            return set(), 0, 0
    
    print(f"Starting parallel download with {workers} workers...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all download tasks
        url_tasks = [(url, i) for i, url in enumerate(urls)]
        futures = {executor.submit(download_single_url, url_info): url_info for url_info in url_tasks}
        
        # Wait for completion
        for future in as_completed(futures):
            future.result()  # This will raise any exceptions that occurred
    
    return all_domains, total_lines, total_valid

def ping_domains_parallel(domains: set, workers: int) -> set:
    """Ping multiple domains in parallel"""
    verified_domains = set()
    domains_list = list(domains)
    
    # Thread-safe set and counters
    lock = threading.Lock()
    completed_count = [0]  # Use list for mutable reference
    
    def ping_single_domain(domain_info):
        domain, index = domain_info
        try:
            print(f"[{index+1}/{len(domains_list)}] Pinging {domain}...", end=" ")
            success = ping_domain(domain, verbose=False)
            
            status = "ONLINE" if success else "OFFLINE"
            print(status)
            
            with lock:
                completed_count[0] += 1
                if success:
                    verified_domains.add(domain)
                
            return success
        except Exception as e:
            print(f"ERROR: {e}")
            with lock:
                completed_count[0] += 1
            return False
    
    print(f"Starting parallel ping verification with {workers} workers...")
    print(f"Verifying {len(domains_list):,} domains...")
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all ping tasks
        domain_tasks = [(domain, i) for i, domain in enumerate(domains_list)]
        futures = {executor.submit(ping_single_domain, domain_info): domain_info for domain_info in domain_tasks}
        
        # Wait for completion
        for future in as_completed(futures):
            future.result()  # This will raise any exceptions that occurred
    
    return verified_domains
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

def generate_next_filename(base_filename: str) -> str:
    """Generate next filename in sequence (e.g., porn.txt -> porn_001.txt)"""
    base_path = os.path.dirname(base_filename)
    base_name = os.path.basename(base_filename)
    name_without_ext, ext = os.path.splitext(base_name)
    
    counter = 1
    while True:
        new_name = f"{name_without_ext}_{counter:03d}{ext}"
        new_path = os.path.join(base_path, new_name)
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def write_domains_to_files(domains: list, base_output_file: str, max_new_per_file: int, existing_new_count: int, urls_count: int) -> list[tuple[str, int]]:
    """Write domains to files, creating new files when max_new_per_file is reached"""
    files_written = []
    
    # Calculate how many new entries we can add to the current file
    remaining_capacity = max_new_per_file - existing_new_count
    
    if len(domains) <= remaining_capacity:
        # All domains fit in current file
        write_single_file(base_output_file, domains, existing_new_count + len(domains), urls_count, len(domains))
        files_written.append((base_output_file, len(domains)))
    else:
        # Need to split across multiple files
        domains_written = 0
        current_file = base_output_file
        
        while domains_written < len(domains):
            if current_file == base_output_file:
                # First file - use remaining capacity
                domains_to_write = min(remaining_capacity, len(domains) - domains_written)
                total_new_in_file = existing_new_count + domains_to_write
            else:
                # New files - use full capacity
                domains_to_write = min(max_new_per_file, len(domains) - domains_written)
                total_new_in_file = domains_to_write
            
            # Get domains for this file
            file_domains = domains[domains_written:domains_written + domains_to_write]
            
            # Write file
            write_single_file(current_file, file_domains, total_new_in_file, urls_count, domains_to_write, is_continuation=(current_file != base_output_file))
            files_written.append((current_file, domains_to_write))
            
            domains_written += domains_to_write
            
            # Generate next filename if more domains remain
            if domains_written < len(domains):
                current_file = generate_next_filename(base_output_file)
                print(f"Creating new file: {current_file}")
    
    return files_written

def write_single_file(filename: str, domains: list, total_new_count: int, urls_count: int, new_domains_added: int, is_continuation: bool = False):
    """Write domains to a single file with header"""
    with open(filename, "w") as f:
        if is_continuation:
            f.write("# Continuation blocklist - duplicates removed\n")
        else:
            f.write("# Merged blocklist - duplicates removed\n")
        f.write(f"# Generated from {urls_count} sources\n")
        f.write(f"# New domains added: {total_new_count:,}\n")
        f.write(f"# Domains in this file: {len(domains):,}\n")
        if new_domains_added != len(domains):
            f.write(f"# New domains added this run: {new_domains_added:,}\n")
        f.write("\n")
        
        for domain in tqdm(domains, desc=f"Writing to {os.path.basename(filename)}"):
            f.write(domain + "\n")
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
        parser.add_argument('--max-file-size', type=int, default=500000, help='Maximum new entries per file before creating new file')
        parser.add_argument('--workers', type=int, default=10, help='Number of worker threads for downloads and ping verification')
        parser.add_argument('--skip-ping', action='store_true', help='Skip ping verification for new domains')
        parser.add_argument('--no-git', action='store_true', help='Skip git operations')
        args = parser.parse_args()
        
        lists_file = args.lists_file
        output_file = args.output_file
        
        # Load existing domains if specified
        existing_domains = set()
        existing_new_count = 0
        if args.existing_domains:
            existing_domains, existing_new_count = load_existing_domains(args.existing_domains)
        elif os.path.exists(output_file):
            print(f"Loading existing domains from output file: {output_file}")
            existing_domains, existing_new_count = load_existing_domains(output_file)
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
        
        # Check if we need file rotation
        will_exceed_limit = existing_new_count + len(verified_new_domains) > args.max_file_size
        
        # Calculate and display statistics
        print(f"\n{'='*50}")
        print(f"PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Existing domains: {len(existing_domains):,}")
        print(f"Existing new entries in current file: {existing_new_count:,}")
        print(f"Max new entries per file: {args.max_file_size:,}")
        print(f"Total lines processed: {total_lines_processed:,}")
        print(f"Valid domains downloaded: {total_valid_domains:,}")
        print(f"New domains found: {len(new_domains):,}")
        if not args.skip_ping:
            print(f"New domains verified online: {len(verified_new_domains):,}")
        print(f"Final unique domains: {len(sorted_domains):,}")
        if will_exceed_limit:
            print(f"Will create new file(s) due to size limit")
        
        # Write to output file(s)
        if len(verified_new_domains) > 0:
            print(f"\nWriting {len(sorted_domains):,} unique domains to file(s)...")
            files_written = write_domains_to_files(
                sorted_domains, 
                output_file, 
                args.max_file_size, 
                existing_new_count, 
                len(urls)
            )
            
            total_files = len(files_written)
            total_new_added = sum(count for _, count in files_written)
            
            print(f"Successfully wrote to {total_files} file(s)")
            for filepath, count in files_written:
                print(f"  {os.path.basename(filepath)}: {count:,} new domains")
            print(f"Total new domains added: {total_new_added:,}")
            
            # Perform git operations unless disabled
            if not args.no_git:
                git_operations(files_written)
        else:
            print("No new domains to write.")
            
        if len(verified_new_domains) == 0:
            print("No new domains to commit.")
        
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        if 'existing_domains' in locals() and 'verified_new_domains' in locals():
            print("Saving partial results...")
            final_domains = existing_domains | verified_new_domains
            sorted_domains = sorted(final_domains)
            
            # Save to single file for interruption case
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