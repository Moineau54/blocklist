from rich.progress import track

import argparse
import os.path
import os
import sys

files = [
    "advertisement.txt",
    "csam.txt",
    "fingerprinting.txt",
    "forums.txt",
    "malware.txt",
    "phishing.txt",
    "porn.txt",
    "spam.txt",
    "suspicious.txt",
    "telemetry.txt",
    "to_monitor.txt",
    "tracking.txt",
    "zoophilia.txt",
]


version = "version 1.0.5"

parser = argparse.ArgumentParser(description="domain_remover")
parser.add_argument(
    "--verbose", "-v", action="store_true", help="Enable verbose output."
)
parser.add_argument(
    "--file_path",
    # action="store_true",
    help="path to file containing domains to remove.",
)

parser.add_argument(
    "--domain",
    help="domain to remove"
)
parser.add_argument("--version", help="shows version number", action="store_true")
parser.set_defaults(file_path=None, verbose=False, domain=None)
args = parser.parse_args()

domains_to_remove = set()
if not args.domain == None or not args.file_path == None:
    if not args.file_path == None:
        for file in files:
            if args.file_path == f"{os.getcwd()}/{file}" or args.file_path == f"{os.getcwd()}/{file.replace(".txt", "_ublock.txt")}":
                print("cannot use one of the lists as source of domains to remove")
                sys.exit()
        file_path = args.file_path
        if file_path:
            with open(file_path, "r") as f:
                lines = f.readlines()

                for line in lines:
                    if line.strip() not in domains_to_remove:
                        domains_to_remove.add(line.strip())
    domains_to_remove.add(str(args.domain).strip())
    for file in files:
        domains_from_file = []
        seen = set()
        with open(file, "r") as f:
            lines = f.readlines()

            for line in track(lines, description=f"filtering domains in {file}"):
                if line != "" and line != "\n":
                    if line.strip() not in domains_to_remove:
                        if line.strip() not in seen:
                            seen.add(line.strip())
                            domains_from_file.append(line.strip())
                    else:
                        print(f"removed {line.strip()} from {file}")


        written = set()
        with open(file, "w") as f:
            for line in track(domains_from_file, description=f"writing {file}"):
                if line.startswith("#") and not line.__contains__("##"):
                    if line not in written:
                        written.add(line)
                        f.write(f"\n\n{line}")
                else:
                    if line not in written:
                        written.add(line)
                        f.write(f"\n{line}")

        del domains_from_file
        del seen
elif args.domain == None and args.file_path == None:
    parser.print_help()
