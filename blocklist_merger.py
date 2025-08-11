import requests
import subprocess
import os
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Tuple
from tqdm import tqdm

"""
Tool to merge multiple blocklists into one with Git integration and online domain filtering
Usage: python script.py input_lists.txt output_file.txt --check-online
"""

def run_git_command(command: list, description: str) -> bool:
    """Run a git command and return success status"""
    try:
        print(f"🔄 {description}...")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git {description.lower()} failed: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"❌ Error during git {description.lower()}: {e}")
        return False

def git_operations(output_file: str, list_num: int, total_lists: int, url: str, domain_count: int) -> bool:
    """Perform git add, commit, pull, and push operations"""
    
    # Add the output file
    if not run_git_command(["git", "add", output_file], "Adding file"):
        return False
    
    # Create commit message
    commit_msg = f"Update blocklist: processed {list_num}/{total_lists} sources ({domain_count:,} domains)\n\nProcessed: {url[:100]}"
    
    # Commit changes
    if not run_git_command(["git", "commit", "-m", commit_msg], "Committing changes"):
        # Check if there were no changes to commit
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not result.stdout.strip():
            print("   No changes to commit")
        else:
            return False
    
    # Pull updates from remote
    if not run_git_command(["git", "pull", "--rebase"], "Pulling updates"):
        print("⚠️  Pull failed, continuing anyway...")
    
    # Push changes
    if not run_git_command(["git", "push"], "Pushing changes"):
        return False
    
    print("✅ Git operations completed successfully\n")
    return True

def check_domain_online(domain: str, timeout: int = 5) -> bool:
    """Check if a domain is reachable via HTTP/HTTPS"""
    for protocol in ['https', 'http']:
        try:
            response = requests.head(f"{protocol}://{domain}", 
                                   timeout=timeout, 
                                   allow_redirects=True,
                                   headers={'User-Agent': 'Mozilla/5.0 (blocklist-checker)'})
            # Accept any response that isn't a server error
            if response.status_code < 500:
                return True
        except (requests.exceptions.RequestException, Exception):
            continue
    return False

def filter_online_domains(domains: Set[str], max_workers: int = 50, timeout: int = 5) -> Tuple[Set[str], Set[str]]:
    """Filter domains to only include those that are reachable"""
    online_domains = set()
    offline_domains = set()
    
    # Create thread pool for concurrent checking
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all domain checks
        future_to_domain = {
            executor.submit(check_domain_online, domain, timeout): domain 
            for domain in domains
        }
        
        # Process results with progress bar
        for future in tqdm(as_completed(future_to_domain), 
                          total=len(domains), 
                          desc="Checking domains",
                          unit="domains"):
            domain = future_to_domain[future]
            try:
                is_online = future.result()
                if is_online:
                    online_domains.add(domain)
                else:
                    offline_domains.add(domain)
            except Exception as e:
                # If check fails, consider domain offline
                offline_domains.add(domain)
                tqdm.write(f"Error checking {domain}: {e}")
    
    return online_domains, offline_domains
    """Run a git command and return success status"""
    try:
        print(f"🔄 {description}...")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git {description.lower()} failed: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"❌ Error during git {description.lower()}: {e}")
        return False

def git_operations(output_file: str, list_num: int, total_lists: int, url: str, domain_count: int) -> bool:
    """Perform git add, commit, pull, and push operations"""
    
    # Add the output file
    if not run_git_command(["git", "add", output_file], "Adding file"):
        return False
    
    # Create commit message
    commit_msg = f"Update blocklist: processed {list_num}/{total_lists} sources ({domain_count:,} domains)\n\nProcessed: {url[:100]}"
    
    # Commit changes
    if not run_git_command(["git", "commit", "-m", commit_msg], "Committing changes"):
        # Check if there were no changes to commit
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not result.stdout.strip():
            print("   No changes to commit")
        else:
            return False
    
    # Pull updates from remote
    if not run_git_command(["git", "pull", "--rebase"], "Pulling updates"):
        print("⚠️  Pull failed, continuing anyway...")
    
    # Push changes
    if not run_git_command(["git", "push"], "Pushing changes"):
        return False
    
    print("✅ Git operations completed successfully\n")
    return True

def write_blocklist_file(output_file: str, domains: Set[str], sources_count: int, 
                        total_lines: int, total_valid: int, list_num: int = None, total_lists: int = None,
                        offline_count: int = 0, online_check_enabled: bool = False):
    """Write domains to output file with metadata"""
    sorted_domains = sorted(domains)
    total_duplicates = total_valid - len(sorted_domains) - offline_count
    
    with open(output_file, "w") as f:
        if list_num and total_lists:
            f.write(f"# Merged blocklist - Progress: {list_num}/{total_lists} sources processed\n")
        else:
            f.write("# Merged blocklist - All sources processed\n")
        f.write(f"# Generated from {sources_count} sources\n")
        f.write(f"# Total lines processed: {total_lines:,}\n")
        f.write(f"# Valid domains found: {total_valid:,}\n")
        f.write(f"# Duplicates removed: {total_duplicates:,}\n")
        if online_check_enabled:
            f.write(f"# Online connectivity check: ENABLED\n")
            f.write(f"# Offline domains filtered: {offline_count:,}\n")
        f.write(f"# Final unique domains: {len(sorted_domains):,}\n")
        if total_duplicates > 0:
            f.write(f"# Deduplication rate: {(total_duplicates/total_valid*100):.1f}%\n")
        f.write("\n")
        
        for domain in sorted_domains:
            f.write(domain + "\n")
    
    return len(sorted_domains), total_duplicates

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

def main():
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(
            description='Merge multiple blocklists into one file with Git integration and online filtering',
            epilog="""
Examples:
  python script.py urls.txt blocklist.txt
  python script.py sources.txt output.txt --check-online
  python script.py lists.txt merged.txt --check-online --git
  python script.py input.txt result.txt --check-online --connection-timeout 3
  python script.py urls.txt final.txt --check-online --check-workers 100
  python script.py sources.txt output.txt --git --no-git
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument('input_file', help='Input file containing blocklist URLs (one per line)')
        parser.add_argument('output_file', help='Output file path for the merged blocklist')
        parser.add_argument('--timeout', type=int, default=20, help='Request timeout in seconds')
        parser.add_argument('--git', action='store_true', help='Enable Git operations after each list')
        parser.add_argument('--no-git', action='store_true', help='Disable Git operations (default if not in git repo)')
        
        # Online checking options
        parser.add_argument('--check-online', action='store_true', 
                          help='Check if domains are reachable via HTTP/HTTPS before including them')
        parser.add_argument('--connection-timeout', type=int, default=5, help='Connection timeout in seconds for online checking')
        parser.add_argument('--check-workers', type=int, default=50, help='Number of concurrent workers for online checking')
        parser.add_argument('--check-batch-size', type=int, default=1000, help='Process domains in batches for online checking')
        
        args = parser.parse_args()
        
        input_file = args.input_file
        output_file = args.output_file
        
        # Validate online checking
        if args.check_online:
            print("🌐 Online checking enabled - will verify domain connectivity via HTTP/HTTPS")
            print(f"   Workers: {args.check_workers}, Timeout: {args.connection_timeout}s")
        else:
            print("🌐 Online checking disabled - all domains will be included")
        
        # Check if we're in a git repository and determine git usage
        use_git = False
        if not args.no_git:
            try:
                subprocess.run(["git", "status"], capture_output=True, check=True)
                use_git = True
                print("📁 Git repository detected")
            except subprocess.CalledProcessError:
                if args.git:
                    print("❌ Git operations requested but not in a git repository")
                    return
                print("📁 Not in a git repository, skipping Git operations")
        
        if args.git and use_git:
            print("🔧 Git operations enabled - will commit after each list")
        elif use_git and not args.no_git:
            print("🔧 Git operations auto-detected - will commit after each list")
            print("    Use --no-git to disable")
        else:
            print("🔧 Git operations disabled")
        
        # Check for input file
        if not os.path.exists(input_file):
            print(f"❌ Input file '{input_file}' not found.")
            print(f"Create {input_file} and add blocklist URLs, one per line.")
            print("Example content:")
            print("# Add blocklist URLs here, one per line")
            print("https://somehost.com/blocklist.txt")
            print("https://example.com/ads.txt")
            return
        
        # Read blocklist URLs
        with open(input_file, "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
        
        if not urls:
            print(f"❌ No URLs found in {input_file}. Please add some blocklist URLs.")
            print("Lines starting with # are treated as comments and ignored.")
            return
        
        print(f"📋 Found {len(urls)} blocklist URLs in {input_file}:")
        for i, url in enumerate(urls, 1):
            print(f"  {i}. {url}")
        
        # Collect all domains with incremental Git operations
        all_domains = set()
        total_lines_processed = 0
        total_valid_domains = 0
        total_offline_domains = 0
        failed_git_operations = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing blocklist...")
            domains, lines_count, valid_count = download_blocklist(url, timeout=args.timeout)
            
            # Track statistics
            domains_before = len(all_domains)
            all_domains.update(domains)
            domains_after = len(all_domains)
            
            new_unique_domains = domains_after - domains_before
            duplicates_found = len(domains) - new_unique_domains
            
            total_lines_processed += lines_count
            total_valid_domains += valid_count
            
            print(f"  Lines processed: {lines_count:,}")
            print(f"  Valid domains found: {valid_count:,}")
            print(f"  New unique domains: {new_unique_domains:,}")
            if duplicates_found > 0:
                print(f"  Duplicates skipped: {duplicates_found:,}")
            
            # Perform online checking if enabled and we have enough domains for a batch
            current_online_domains = all_domains
            current_offline_count = 0
            
            if args.check_online and len(all_domains) >= args.check_batch_size:
                print(f"🔍 Checking {len(all_domains):,} domains for online status...")
                current_online_domains, offline_domains = filter_online_domains(
                    all_domains, args.check_workers, args.connection_timeout
                )
                current_offline_count = len(offline_domains)
                total_offline_domains = current_offline_count
                
                print(f"  ✅ Online domains: {len(current_online_domains):,}")
                print(f"  ❌ Offline domains: {current_offline_count:,}")
                print(f"  📊 Online rate: {(len(current_online_domains)/len(all_domains)*100):.1f}%")
            
            # Write updated file after each list
            current_domains, current_duplicates = write_blocklist_file(
                output_file, current_online_domains, len(urls), total_lines_processed, 
                total_valid_domains, i, len(urls), current_offline_count, args.check_online
            )
            
            print(f"📝 Updated {output_file} with {current_domains:,} total unique domains")
            
            # Perform Git operations if enabled
            if use_git:
                success = git_operations(output_file, i, len(urls), url, current_domains)
                if not success:
                    failed_git_operations += 1
                    print(f"⚠️  Git operations failed for list {i}/{len(urls)}")
                    
                    # Ask user if they want to continue
                    try:
                        response = input("Continue processing remaining lists? (y/n): ").lower().strip()
                        if response not in ['y', 'yes']:
                            print("❌ Processing stopped by user")
                            return
                    except KeyboardInterrupt:
                        print("\n❌ Processing interrupted")
                        return
            
            # Brief pause between downloads to be respectful
            if i < len(urls):
                print(f"⏳ Waiting 2 seconds before next download...")
                time.sleep(2)
        
        # Perform final online checking if enabled and we haven't done a recent check
        final_online_domains = all_domains
        final_offline_count = total_offline_domains
        
        if args.check_online:
            print(f"\n🔍 Performing final online check for {len(all_domains):,} total domains...")
            final_online_domains, final_offline_domains = filter_online_domains(
                all_domains, args.check_workers, args.connection_timeout
            )
            final_offline_count = len(final_offline_domains)
            
            print(f"✅ Final online domains: {len(final_online_domains):,}")
            print(f"❌ Final offline domains: {final_offline_count:,}")
            print(f"📊 Final online rate: {(len(final_online_domains)/len(all_domains)*100):.1f}%")
        
        # Final summary
        sorted_domains = sorted(final_online_domains)
        total_duplicates_removed = total_valid_domains - len(all_domains)  # Duplicates only
        
        print(f"\n{'='*60}")
        print(f"FINAL PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"Total blocklist sources: {len(urls)}")
        print(f"Total lines processed: {total_lines_processed:,}")
        print(f"Valid domains found: {total_valid_domains:,}")
        print(f"Duplicates removed: {total_duplicates_removed:,}")
        print(f"Unique domains after dedup: {len(all_domains):,}")
        
        if args.check_online:
            print(f"Online connectivity check: ENABLED")
            print(f"Offline domains filtered: {final_offline_count:,}")
            print(f"Online rate: {(len(final_online_domains)/len(all_domains)*100):.1f}%")
        
        print(f"Final unique online domains: {len(sorted_domains):,}")
        
        if total_valid_domains > 0:
            total_reduction = total_valid_domains - len(sorted_domains)
            reduction_rate = (total_reduction / total_valid_domains * 100)
            print(f"Total reduction: {total_reduction:,} domains ({reduction_rate:.1f}%)")
        
        if use_git:
            if failed_git_operations == 0:
                print(f"✅ All Git operations completed successfully")
            else:
                print(f"⚠️  Git operations failed for {failed_git_operations}/{len(urls)} lists")
        
        # Write final version of the file
        final_domains, final_duplicates = write_blocklist_file(
            output_file, final_online_domains, len(urls), total_lines_processed, 
            total_valid_domains, offline_count=final_offline_count, check_method=check_method
        )
        
        print(f"✅ Final blocklist written to {output_file}")
        print(f"   📊 {final_domains:,} unique online domains")
        print(f"   🗑️  {total_duplicates_removed:,} duplicates removed")
        if check_method != 'none':
            print(f"   🚫 {final_offline_count:,} offline domains filtered")
        print(f"   📋 Source: {input_file} ({len(urls)} URLs)")
        
        # Final git commit if enabled
        if use_git:
            print(f"\n🔄 Creating final commit...")
            commit_suffix = f" (online-only)" if check_method != 'none' else ""
            final_commit_msg = f"Final blocklist update: {final_domains:,} domains from {len(urls)} sources{commit_suffix}"
            if run_git_command(["git", "add", output_file], "Adding final file"):
                if run_git_command(["git", "commit", "-m", final_commit_msg], "Final commit"):
                    run_git_command(["git", "push"], "Final push")
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        if 'all_domains' in locals() and all_domains:
            print("💾 Saving partial results...")
            
            # If online checking was enabled, perform quick check on collected domains
            partial_online_domains = all_domains
            partial_offline_count = 0
            
            if locals().get('args', {}).get('check_online', False):
                print("🔍 Performing quick online check on partial results...")
                partial_online_domains, partial_offline_domains = filter_online_domains(
                    all_domains, min(20, locals().get('args', {}).get('check_workers', 20)), 
                    locals().get('args', {}).get('connection_timeout', 5)
                )
                partial_offline_count = len(partial_offline_domains)
                print(f"✅ Online: {len(partial_online_domains):,}, ❌ Offline: {partial_offline_count:,}")
            
            # Write partial results
            partial_domains, partial_duplicates = write_blocklist_file(
                output_file, partial_online_domains, 
                locals().get('i', 0),  # Number of lists processed so far
                locals().get('total_lines_processed', 0),
                locals().get('total_valid_domains', 0),
                offline_count=partial_offline_count,
                online_check_enabled=locals().get('args', {}).get('check_online', False)
            )
            
            print(f"💾 Saved {partial_domains:,} unique online domains to {output_file}")
            if partial_duplicates > 0:
                print(f"   🗑️  {partial_duplicates:,} duplicates were removed")
            if partial_offline_count > 0:
                print(f"   🚫 {partial_offline_count:,} offline domains filtered")
            print(f"   📋 Source: {locals().get('input_file', 'unknown')} (partial)")
            
            # Final git commit if enabled and we're in a git repo
            if locals().get('use_git', False):
                print("🔄 Creating final commit for partial results...")
                commit_msg = f"Partial blocklist update (interrupted): {partial_domains:,} domains"
                if run_git_command(["git", "add", output_file], "Adding partial file"):
                    if run_git_command(["git", "commit", "-m", commit_msg], "Partial commit"):
                        run_git_command(["git", "push"], "Partial push")
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()