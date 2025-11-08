from nslookup import Nslookup
from rich.progress import track
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console
from rich.text import Text
import time
import os

class Lookup():
    def __init__(self):
        self.dns_query = Nslookup(dns_servers=["9.9.9.9", "194.242.2.2"], verbose=False, tcp=False) # uses Quad9 and mullvad dns
        self.default_files = [
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
        self.ip_files = self.get_ip_files()
        self.domain_list_file_content = []
        self.ip_list_file_content = []
        self.console = Console()
        
        
    def get_ip_files(self):
        ip_files = []
        for file_name in self.default_files:
            ip_files.append(file_name.replace(".txt", ".ip"))
        
        return ip_files
    
    def get_file_content(self, domain_list_file, ip_file):
        content_in_dir = os.listdir(os.getcwd())
        if domain_list_file not in content_in_dir:
            with open(domain_list_file, mode='a'): pass
        else:
            with open(domain_list_file, "r") as ftxt:
                self.domain_list_file_content = ftxt.readlines()
        
        if ip_file not in content_in_dir:
            with open(ip_file, mode='a'): pass
        else:
            with open(ip_file, "r") as fip:
                self.ip_list_file_content = fip.readlines()
    
    def dns_lookup(self, domain):
        ips_record = self.dns_query.dns_lookup(domain.strip())
        return ips_record.answer


    def run(self):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            
            file_task = progress.add_task("Processing files", total=len(self.default_files))
            
            for file_name in self.default_files:
                index = self.default_files.index(file_name)
                ip_file_name = self.ip_files[index]
                self.get_file_content(file_name, ip_file_name)
                domain_task = progress.add_task("", total=len(self.domain_list_file_content))

                progress.update(domain_task, description=f"Processing {file_name}", completed=0, total=len(self.domain_list_file_content))
                
                with open(ip_file_name, "a") as f:
                    for domain in self.domain_list_file_content:
                        if not domain.startswith("#") and not domain == "\n":
                            ips = self.dns_lookup(domain)
                            if len(ips) == 0:
                                self.console.print(f"[bold red][-] no IPs found for {domain.strip()}[/bold red]")
                                
                            else:
                                
                                count_ip_to_add = 0
                                for ip in ips:
                                    if f"{ip}\n" not in self.ip_list_file_content or f"{ip}" not in self.ip_list_file_content:
                                        count_ip_to_add += 1
                                
                                if count_ip_to_add > 0:
                                    f.write(f"\n# {domain}")
                                    self.ip_list_file_content.append(f"\n# {domain}")

                                    for ip in ips:
                                        # if ip == "3.251.41.252": # debug
                                        #     print("test")
                                        if f"{ip}\n" not in self.ip_list_file_content:
                                            self.ip_list_file_content.append(ip)
                                            f.write(f"{ip}\n")

                                            domain_print = f"[bold green]{domain.strip()}[/bold green]"
                                            self.console.print(f"[bold cyan][+][/bold cyan] {ip} for {domain_print} added to {ip_file_name}")
                                    
                                    ips.clear()
                                
                                else:
                                    
                                    self.console.print(f"[bold yellow][*] no new IPs for {domain.strip()}[/bold yellow]")
                        
                        time.sleep(0.0001)

                        progress.advance(domain_task)
                
                progress.advance(file_task)

                time.sleep(1)

lookup = Lookup()

lookup.run()