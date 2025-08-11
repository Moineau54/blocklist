import requests
import subprocess
import os
import sys
import time
import argparse
from typing import Set, Tuple
from tqdm import tqdm

"""
Tool to merge multiple blocklists into one with Git integration
Usage: python script.py output_file.txt
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

def write_blocklist_file(output_file: str, domains: Set[str], sources_count: int, 
                        total_lines: int, total_valid: int, list_num: int = None, total_lists: int = None):
    """Write domains to output file with metadata"""
    sorted_domains = sorted(domains)
    total_duplicates = total_valid - len(sorted_domains)
    
    with open(output_file, "w") as f:
        if list_num and total_lists:
            f.write(f"# Merged blocklist - Progress: {list_num}/{total_lists} sources processed\n")
        else:
            f.write("# Merged blocklist - All sources processed\n")
        f.write(f"# Generated from {sources_count} sources\n")
        f.write(f"# Total lines processed: {total_lines:,}\n")
        f.write(f"# Valid domains found: {total_valid:,}\n")
        f.write(f"# Duplicates removed: {total_duplicates:,}\n")
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
        parser = argparse.ArgumentParser(description='Merge multiple blocklists into one file with Git integration')
        parser.add_argument('output_file', help='Output file path for the merged blocklist')
        parser.add_argument('--timeout', type=int, default=20, help='Request timeout in seconds')
        parser.add_argument('--git', action='store_true', help='Enable Git operations after each list')
        parser.add_argument('--no-git', action='store_true', help='Disable Git operations (default if not in git repo)')
        args = parser.parse_args()
        
        output_file = args.output_file
        
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
        
        # Check for lists.txt
        lists_file = "lists.txt"
        if not os.path.exists(lists_file):
            # Create empty lists.txt
            with open(lists_file, "w") as f:
                f.write("# Add blocklist URLs here, one per line\n")
            print(f"Created {lists_file}. Please add blocklist URLs to this file, one per line.")
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
        
        # Collect all domains with incremental Git operations
        all_domains = set()
        total_lines_processed = 0
        total_valid_domains = 0
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
            
            # Write updated file after each list
            current_domains, current_duplicates = write_blocklist_file(
                output_file, all_domains, len(urls), total_lines_processed, 
                total_valid_domains, i, len(urls)
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
        
        # Final summary
        sorted_domains = sorted(all_domains)
        total_duplicates_removed = total_valid_domains - len(sorted_domains)
        
        print(f"\n{'='*60}")
        print(f"FINAL PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"Total blocklist sources: {len(urls)}")
        print(f"Total lines processed: {total_lines_processed:,}")
        print(f"Valid domains found: {total_valid_domains:,}")
        print(f"Duplicates removed: {total_duplicates_removed:,}")
        print(f"Final unique domains: {len(sorted_domains):,}")
        print(f"Deduplication rate: {(total_duplicates_removed/total_valid_domains*100):.1f}%" if total_valid_domains > 0 else "0%")
        
        if use_git:
            if failed_git_operations == 0:
                print(f"✅ All Git operations completed successfully")
            else:
                print(f"⚠️  Git operations failed for {failed_git_operations}/{len(urls)} lists")
        
        # Write final version of the file
        final_domains, final_duplicates = write_blocklist_file(
            output_file, all_domains, len(urls), total_lines_processed, total_valid_domains
        )
        
        print(f"\n✅ Final blocklist written to {output_file}")
        print(f"   📊 {final_domains:,} unique domains")
        print(f"   🗑️  {final_duplicates:,} duplicates removed")
        
        # Final git commit if enabled
        if use_git:
            print(f"\n🔄 Creating final commit...")
            final_commit_msg = f"Final blocklist update: {final_domains:,} domains from {len(urls)} sources"
            if run_git_command(["git", "add", output_file], "Adding final file"):
                if run_git_command(["git", "commit", "-m", final_commit_msg], "Final commit"):
                    run_git_command(["git", "push"], "Final push")
        
    except KeyboardInterrupt:
        print("\n⚠️  Operation interrupted by user")
        if 'all_domains' in locals() and all_domains:
            print("💾 Saving partial results...")
            sorted_domains = sorted(all_domains)
            duplicates_removed = locals().get('total_valid_domains', 0) - len(sorted_domains)
            
            # Write partial results
            partial_domains, partial_duplicates = write_blocklist_file(
                output_file, all_domains, 
                locals().get('i', 0),  # Number of lists processed so far
                locals().get('total_lines_processed', 0),
                locals().get('total_valid_domains', 0)
            )
            
            print(f"💾 Saved {partial_domains:,} unique domains to {output_file}")
            if partial_duplicates > 0:
                print(f"   🗑️  {partial_duplicates:,} duplicates were removed")
            
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