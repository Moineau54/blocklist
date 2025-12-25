package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"strings"
	"sync"

	"github.com/miekg/dns"
	"github.com/schollz/progressbar/v3"
)

type Lookup struct {
	defaultFiles          []string
	ipFiles               []string
	domainListFileContent []string
	ipListFileContent     []string
}

func NewLookup(files []string) *Lookup {
	return &Lookup{
		defaultFiles: files,
			ipFiles:      buildIPFiles(files),
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
	touch := func(path string) {
		if _, err := os.Stat(path); os.IsNotExist(err) {
			os.WriteFile(path, []byte{}, 0644)
		}
	}
	touch(domainFile)
	touch(ipFile)
	domainData, err := os.ReadFile(domainFile)
	if err != nil {
		return err
	}
	l.domainListFileContent = strings.Split(string(domainData), "\n")
	ipData, err := os.ReadFile(ipFile)
	if err != nil {
		return err
	}
	l.ipListFileContent = strings.Split(string(ipData), "\n")
	return nil
}

func dnsLookup(domain string, dnsServers []string) ([]string, error) {
	var ips []string
	c := new(dns.Client)
	for _, server := range dnsServers {
		m := new(dns.Msg)
		m.SetQuestion(dns.Fqdn(domain), dns.TypeA)
		r, _, err := c.Exchange(m, server+":53")
		if err != nil {
			continue
		}
		if r.Rcode != dns.RcodeSuccess {
			continue
		}
		for _, ans := range r.Answer {
			if a, ok := ans.(*dns.A); ok {
				ips = append(ips, a.A.String())
			}
		}
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

func (l *Lookup) run(workers int) {
	fileBar := progressbar.NewOptions(len(l.defaultFiles),
					  progressbar.OptionSetDescription("Processing files"),
					  progressbar.OptionSetPredictTime(false),
					  progressbar.OptionShowCount(),
	)
	dnsServers := []string{"9.9.9.9", "9.9.9.10", "194.242.2.2"}
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
		var wg sync.WaitGroup
		sem := make(chan struct{}, workers)
		var mu sync.Mutex
		for _, domain := range l.domainListFileContent {
			domain = strings.TrimSpace(domain)
			if domain == "" || strings.HasPrefix(domain, "#") {
				domainBar.Add(1)
				continue
			}
			if idx := strings.Index(domain, "#"); idx != -1 {
				domain = strings.TrimSpace(domain[:idx])
			}
			if domain == "" {
				domainBar.Add(1)
				continue
			}
			wg.Add(1)
			go func(domain string) {
				defer wg.Done()
				sem <- struct{}{}
				defer func() { <-sem }()
				ips, _ := dnsLookup(domain, dnsServers)
				if len(ips) == 0 {
					fmt.Printf("[ - ] No IPs found for %s\n", domain)
					domainBar.Add(1)
					return
				}
				mu.Lock()
				defer mu.Unlock()
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
				domainBar.Add(1)
			}(domain)
		}
		wg.Wait()
		writer.Flush()
		f.Close()
		fileBar.Add(1)
	}
}

func main() {
	filePtr := flag.String("f", "None", "Name of the file(s) to process (space-separated, or 'None' for default list)")
	workersPtr := flag.Int("w", 20, "Number of workers (goroutines) to use")
	flag.Parse()

	var files []string
	if *filePtr == "None" {
		files = []string{
			"advertisement.txt",
			"fingerprinting.txt",
			"forums.txt",
			"malware.txt",
			"spam.txt",
			"suspicious.txt",
			"telemetry.txt",
			"to_monitor.txt",
			"tracking.txt",
			"zoophilia.txt",
			"porn.txt",
		}
	} else {
		files = strings.Fields(*filePtr)
	}

	lookup := NewLookup(files)
	lookup.run(*workersPtr)
}
