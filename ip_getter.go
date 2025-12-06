package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"net"
	"os"
	"strings"
	"time"

	"github.com/schollz/progressbar/v3"
)

type Lookup struct {
	defaultFiles          []string
	ipFiles               []string
	domainListFileContent []string
	ipListFileContent     []string
	resolver              *net.Resolver
}

func NewLookup(file string) *Lookup {
	var defaultFiles []string

	if file == "None" {
		defaultFiles = []string{
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
			"tracking.txt",
			"zoophilia.txt",
		}
	} else {
		defaultFiles = []string{file}
	}

	return &Lookup{
		defaultFiles: defaultFiles,
			ipFiles:      buildIPFiles(defaultFiles),
			resolver: &net.Resolver{
				PreferGo: true,
				Dial: func(ctx context.Context, network, address string) (net.Conn, error) {
					dns := []string{"9.9.9.9:443", "9.9.9.10:53", "194.242.2.2:443"}
					d := net.Dialer{}
					return d.DialContext(ctx, "udp", dns[time.Now().UnixNano()%3])
				},
			},
	}
}

func buildIPFiles(files []string) []string {
	var res []string
	for _, f := range files {
		res = append(res, strings.TrimSuffix(f, ".txt")+".ip")
	}
	return res
}

func (l *Lookup) loadFileContent(domainFile, ipFile string) error {
	// Ensure files exist
	touch := func(path string) {
		if _, err := os.Stat(path); os.IsNotExist(err) {
			os.WriteFile(path, []byte{}, 0644)
		}
	}

	touch(domainFile)
	touch(ipFile)

	// Load domain file
	domainData, err := os.ReadFile(domainFile)
	if err != nil {
		return err
	}
	l.domainListFileContent = strings.Split(string(domainData), "\n")

	// Load IP file
	ipData, err := os.ReadFile(ipFile)
	if err != nil {
		return err
	}
	l.ipListFileContent = strings.Split(string(ipData), "\n")

	return nil
}

func (l *Lookup) dnsLookup(domain string) ([]string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	ips, err := l.resolver.LookupHost(ctx, domain)
	if err != nil {
		return []string{}, nil // treat errors as no-IP (like Python)
	}

	return ips, nil
}

func contains(list []string, item string) bool {
	for _, x := range list {
		if strings.TrimSpace(x) == strings.TrimSpace(item) {
			return true
		}
	}
	return false
}

func (l *Lookup) run() {
	fileBar := progressbar.NewOptions(len(l.defaultFiles),
					  progressbar.OptionSetDescription("Processing files"),
					  progressbar.OptionSetPredictTime(false),
					  progressbar.OptionShowCount(),
	)

	for i, fileName := range l.defaultFiles {
		fmt.Printf("\n[ Processing %s ]\n", fileName)

		ipFile := l.ipFiles[i]
		l.loadFileContent(fileName, ipFile)

		domainBar := progressbar.NewOptions(len(l.domainListFileContent),
						    progressbar.OptionSetDescription(fmt.Sprintf("Processing %s", fileName)),
						    progressbar.OptionSetPredictTime(false),
						    progressbar.OptionShowCount(),
		)

		f, err := os.OpenFile(ipFile, os.O_APPEND|os.O_WRONLY, 0644)
		if err != nil {
			fmt.Println("Error creating ip file:", err)
			continue
		}
		writer := bufio.NewWriter(f)

		for _, domain := range l.domainListFileContent {
			domain = strings.TrimSpace(domain)
			if domain == "" || strings.HasPrefix(domain, "#") {
				domainBar.Add(1)
				continue
			}

			ips, _ := l.dnsLookup(domain)

			if len(ips) == 0 {
				fmt.Printf("[ - ] No IPs found for %s\n", domain)
			} else {
				newIPs := 0
				for _, ip := range ips {
					if !contains(l.ipListFileContent, ip) {
						newIPs++
					}
				}

				if newIPs > 0 {
					writer.WriteString("\n# " + domain + "\n")
					l.ipListFileContent = append(l.ipListFileContent, "# "+domain)

					for _, ip := range ips {
						if !contains(l.ipListFileContent, ip) {
							writer.WriteString(ip + "\n")
							l.ipListFileContent = append(l.ipListFileContent, ip)
							fmt.Printf("[ + ] %s for %s added to %s\n", ip, domain, ipFile)
						}
					}

				} else {
					fmt.Printf("[ * ] No new IPs for %s\n", domain)
				}
			}

			writer.Flush()
			domainBar.Add(1)
			time.Sleep(100 * time.Microsecond)
		}

		f.Close()
		fileBar.Add(1)
		time.Sleep(1 * time.Second)
	}
}

func main() {
	filePtr := flag.String("f", "None", "Name of the file to process")
	flag.Parse()

	lookup := NewLookup(*filePtr)
	lookup.run()
}
