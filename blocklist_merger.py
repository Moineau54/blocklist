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
Usage: python script.py lists_file.txt output_file.txt [--existing-domains existing.txt] [--max-new 1000] [--max-file-size 500000] [--workers 10] [--skip-ping] [--skip-git]
"""

def main():
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
    
    args = parser.parse_args()
    
    # Read existing domains from output file if it exists
    existing_domains = load_existing_domains(args.output_file)
    
    # Read additional existing domains if provided
    if args.existing_domains:
        existing_domains.update(load_existing_domains(args.existing_domains))
    
    # Read blocklist URLs from input file
    blocklist_urls = load_blocklist_urls(args.input_file)
    
    # Fetch and process all blocklists
    all_domains = fetch_and_clean_domains(blocklist_urls, args.workers, args.timeout)
    
    # Remove duplicates and existing domains
    new_domains = all_domains - existing_domains
    
    print(f"Found {len(new_domains)} new domains to verify")
    
    # Limit to max new domains
    if len(new_domains) > args.max_new:
        new_domains = set(list(new_domains)[:args.max_new])
        print(f"Limited to {args.max_new} domains")
    
    # Ping domains to verify they're online (unless skipped)
    if not args.skip_ping:
        verified_domains = verify_domains_online_with_git(new_domains, args.workers, args.timeout, 
                                                         args.output_file, args.skip_git)
    else:
        verified_domains = new_domains
        # Write all at once if skipping ping
        write_domains_to_file(verified_domains, args.output_file)
        if not args.skip_git:
            git_commit_push(f"Added {len(verified_domains)} domains (ping skipped)")
    
    print(f"Added {len(verified_domains)} verified domains to {args.output_file}")


def git_commit_push(commit_message: str):
    """Perform git add, commit, pull, and push operations"""
    try:
        # Git add
        subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
        print("Git add completed")
        
        # Git commit
        subprocess.run(['git', 'commit', '-m', commit_message], check=True, capture_output=True)
        print(f"Git commit completed: {commit_message}")
        
        # Git pull
        result = subprocess.run(['git', 'pull'], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Git pull warning: {result.stderr}")
        else:
            print("Git pull completed")
        
        # Git push
        subprocess.run(['git', 'push'], check=True, capture_output=True)
        print("Git push completed")
        
    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
    except Exception as e:
        print(f"Git error: {e}")


def verify_domains_online_with_git(domains: Set[str], workers: int, timeout: float, 
                                 output_file: str, skip_git: bool) -> Set[str]:
    """Ping domains to verify they're online with git commits every 20%"""
    verified_domains = set()
    lock = threading.Lock()
    
    domains_list = list(domains)
    total_domains = len(domains_list)
    
    # Calculate 20% intervals
    checkpoint_interval = max(1, total_domains // 5)  # Every 20%
    next_checkpoint = checkpoint_interval
    processed_count = 0
    
    def ping_domain(domain):
        nonlocal processed_count, next_checkpoint
        
        try:
            # Simple ping using subprocess
            result = subprocess.run(['ping', '-c', '1', '-W', str(int(timeout * 1000)), domain], 
                                  capture_output=True, timeout=timeout + 1)
            
            with lock:
                nonlocal processed_count
                processed_count += 1
                
                if result.returncode == 0:
                    verified_domains.add(domain)
                    # Write domain immediately to file
                    write_single_domain_to_file(domain, output_file)
                
                # Check if we've reached a checkpoint (20% interval)
                if not skip_git and processed_count >= next_checkpoint and processed_count < total_domains:
                    percentage = (processed_count / total_domains) * 100
                    commit_msg = f"Progress: {processed_count}/{total_domains} domains verified ({percentage:.1f}%)"
                    print(f"\nReached {percentage:.1f}% - performing git operations...")
                    git_commit_push(commit_msg)
                    next_checkpoint += checkpoint_interval
                
            return result.returncode == 0
            
        except Exception:
            with lock:
                processed_count += 1
            return False
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(ping_domain, domain) for domain in domains_list]
        
        for future in tqdm(as_completed(futures), total=len(domains_list), desc="Verifying domains"):
            future.result()
    
    # Final git commit if not skipped
    if not skip_git:
        print("\nFinal git commit...")
        git_commit_push(f"Completed: {len(verified_domains)} domains verified and added")
    
    return verified_domains


def write_single_domain_to_file(domain: str, filename: str):
    """Append a single domain to output file"""
    with open(filename, 'a') as f:
        f.write(f"{domain}\n")


def load_existing_domains(filename: str) -> Set[str]:
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
                domains.add(domain)
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


def fetch_and_clean_domains(urls: list, workers: int, timeout: float) -> Set[str]:
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
                    if cleaned and '.' in cleaned:  # Basic domain validation
                        domains.add(cleaned)
            return domains
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return set()
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {executor.submit(fetch_blocklist, url): url for url in urls}
        
        for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Fetching blocklists"):
            domains = future.result()
            all_domains.update(domains)
    
    return all_domains


def write_domains_to_file(domains: Set[str], filename: str):
    """Append new domains to output file"""
    with open(filename, 'a') as f:
        for domain in sorted(domains):
            f.write(f"{domain}\n")


if __name__ == "__main__":
    main()