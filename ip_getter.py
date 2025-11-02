import subprocess
import re
import time
import sys

# Default files if no arguments provided
default_files = [
    "advertisement.txt",
    "csam.txt",
    "fingerprinting.txt",
    "forums.txt",
    "malware.txt",
    "porn.txt",
    "spam.txt",
    "suspicious.txt",
    "telemetry.txt",
    "to_monitor.txt",
    "tracking.txt"
]

ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
ipv6_pattern = r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b'

def is_private_ipv4(ip):
    """Check if an IPv4 address is private/local."""
    parts = ip.split('.')
    if len(parts) != 4:
        return True
    
    try:
        octets = [int(part) for part in parts]
    except ValueError:
        return True
    
    # Validate octets are in valid range
    if any(octet < 0 or octet > 255 for octet in octets):
        return True
    
    # Check private ranges
    if octets[0] == 10:  # 10.0.0.0/8
        return True
    if octets[0] == 172 and 16 <= octets[1] <= 31:  # 172.16.0.0/12
        return True
    if octets[0] == 192 and octets[1] == 168:  # 192.168.0.0/16
        return True
    if octets[0] == 127:  # 127.0.0.0/8 (loopback)
        return True
    if octets[0] == 169 and octets[1] == 254:  # 169.254.0.0/16 (link-local)
        return True
    if octets[0] == 0:  # 0.0.0.0/8
        return True
    if octets[0] >= 224:  # 224.0.0.0/4 (multicast) and 240.0.0.0/4 (reserved)
        return True
    if octets[0] == 100 and 64 <= octets[1] <= 127:  # 100.64.0.0/10 (shared address space)
        return True
    if octets[0] == 192 and octets[1] == 0 and octets[2] == 0:  # 192.0.0.0/24
        return True
    if octets[0] == 192 and octets[1] == 0 and octets[2] == 2:  # 192.0.2.0/24 (TEST-NET-1)
        return True
    if octets[0] == 198 and octets[1] == 18:  # 198.18.0.0/15 (benchmarking)
        return True
    if octets[0] == 198 and octets[1] == 19:  # 198.18.0.0/15 (benchmarking)
        return True
    if octets[0] == 198 and octets[1] == 51 and octets[2] == 100:  # 198.51.100.0/24 (TEST-NET-2)
        return True
    if octets[0] == 203 and octets[1] == 0 and octets[2] == 113:  # 203.0.113.0/24 (TEST-NET-3)
        return True
    if octets[0] == 255 and octets[1] == 255 and octets[2] == 255 and octets[3] == 255:  # 255.255.255.255 (broadcast)
        return True
    
    return False

def is_private_ipv6(ip):
    """Check if an IPv6 address is private/local."""
    ip_lower = ip.lower()
    
    # Loopback
    if ip_lower == '::1':
        return True
    
    # Link-local (fe80::/10)
    if ip_lower.startswith('fe80:'):
        return True
    
    # Unique local addresses (fc00::/7)
    if ip_lower.startswith('fc') or ip_lower.startswith('fd'):
        return True
    
    # Multicast (ff00::/8)
    if ip_lower.startswith('ff'):
        return True
    
    # Unspecified address
    if ip_lower == '::':
        return True
    
    # IPv4-mapped IPv6 addresses (::ffff:0:0/96)
    if '::ffff:' in ip_lower:
        # Extract the IPv4 part and check if it's private
        parts = ip_lower.split('::ffff:')
        if len(parts) == 2:
            ipv4_part = parts[1]
            # Check if it's in dot notation
            if '.' in ipv4_part:
                return is_private_ipv4(ipv4_part)
    
    return False

def extract_ips(text):
    """Extract public IP addresses from text."""
    all_ipv4 = re.findall(ipv4_pattern, text)
    ipv4_addresses = [ip for ip in all_ipv4 if not is_private_ipv4(ip)]
    
    all_ipv6 = re.findall(ipv6_pattern, text)
    ipv6_addresses = [ip for ip in all_ipv6 if not is_private_ipv6(ip)]
    
    return ipv4_addresses + ipv6_addresses

def load_existing_ips(filename):
    """Load existing IPs from a file."""
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# Use command-line arguments if provided, otherwise use default files
files = sys.argv[1:] if len(sys.argv) > 1 else default_files

if not files:
    print("No files to process")
    sys.exit(0)

for file in files:
    print(f"Processing: {file}")
    ip_file_name = file.replace(".txt", ".ip")
    
    # Load existing IPs
    existing_ips = load_existing_ips(ip_file_name)
    existing_ips_set = set(existing_ips)
    
    if existing_ips:
        print(f"  Found {len(existing_ips)} existing IPs in {ip_file_name}")
    
    all_ips = []
    
    try:
        with open(file, "r") as f:
            domains = f.readlines()
        
        for domain in domains:
            domain = domain.strip()
            
            # Skip empty lines
            if not domain or domain.startswith("#"):
                continue
            
            # Skip .onion domains
            if ".onion" in domain:
                print(f"  Skipping .onion domain: {domain}")
                continue
            
            try:
                result = subprocess.run(
                    ['nslookup', domain],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    ips = extract_ips(result.stdout)
                    if ips:
                        print(f"  {domain} -> {', '.join(ips)}")
                        all_ips.extend(ips)
                    else:
                        print(f"  {domain} -> No public IPs found")
                else:
                    print(f"  {domain} -> Lookup failed")
            
            except subprocess.TimeoutExpired:
                print(f"  Request to {domain} timed out")
            except Exception as e:
                print(f"  Error processing {domain}: {e}")
        
        # Process IPs
        if all_ips:
            # Remove duplicates from new IPs while preserving order
            unique_new_ips = list(dict.fromkeys(all_ips))
            
            # Find truly new IPs (not in existing file)
            new_ips_to_add = [ip for ip in unique_new_ips if ip not in existing_ips_set]
            
            if new_ips_to_add:
                # Append new IPs to existing file
                with open(ip_file_name, "a") as f:
                    if existing_ips and not existing_ips[-1].endswith('\n'):
                        f.write('\n')
                    f.write("\n".join(new_ips_to_add) + "\n")
                print(f"  Added {len(new_ips_to_add)} new IPs to {ip_file_name}")
            else:
                print(f"  No new IPs to add (all {len(unique_new_ips)} IPs already exist)")
            
            total_ips = len(existing_ips) + len(new_ips_to_add)
            print(f"  Total IPs in {ip_file_name}: {total_ips}\n")
        else:
            if not existing_ips:
                print(f"  No IPs found for {file}\n")
            else:
                print(f"  No new IPs found, keeping existing {len(existing_ips)} IPs\n")
        
        #time.sleep(0.5)
    
    except FileNotFoundError:
        print(f"  File not found: {file}\n")
    except Exception as e:
        print(f"  Error reading {file}: {e}\n")