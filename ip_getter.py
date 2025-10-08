import subprocess
import re
import time

files = [
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

def is_private_ip(ip):
    """Check if an IPv4 address is private/local."""
    parts = ip.split('.')
    if len(parts) != 4:
        return True
    
    try:
        octets = [int(part) for part in parts]
    except ValueError:
        return True
    
    # Check private ranges
    if octets[0] == 10:
        return True
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return True
    if octets[0] == 192 and octets[1] == 168:
        return True
    if octets[0] == 127:
        return True
    if octets[0] == 169 and octets[1] == 254:
        return True
    if octets[0] == 0:
        return True
    
    return False

def extract_ips(text):
    """Extract public IP addresses from text."""
    all_ipv4 = re.findall(ipv4_pattern, text)
    ipv4_addresses = [ip for ip in all_ipv4 if not is_private_ip(ip)]
    
    all_ipv6 = re.findall(ipv6_pattern, text)
    ipv6_addresses = [ip for ip in all_ipv6 if not ip.startswith('fe80:') and ip != '::1']
    
    return ipv4_addresses + ipv6_addresses

for file in files:
    print(f"Processing: {file}")
    ip_file_name = file.replace(".txt", ".ip")
    
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
        
        # Write all IPs to file
        if all_ips:
            # Remove duplicates while preserving order
            unique_ips = list(dict.fromkeys(all_ips))
            with open(ip_file_name, "w") as f:
                f.write("\n".join(unique_ips))
            print(f"  Wrote {len(unique_ips)} unique IPs to {ip_file_name}\n")
        else:
            print(f"  No IPs found for {file}\n")
        
        time.sleep(1)
    except FileNotFoundError:
        print(f"  File not found: {file}\n")
    except Exception as e:
        print(f"  Error reading {file}: {e}\n")