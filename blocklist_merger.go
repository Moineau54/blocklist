package main

import (
	"bufio"
	"context"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	"golang.org/x/sync/semaphore"
	"github.com/schollz/progressbar/v3"
	"github.com/urfave/cli/v2"
)

var (
	allDomains = make(map[string]struct{})
	domainMu   sync.Mutex
)

func main() {
	fmt.Println("DEBUG: Starting script...")

	app := &cli.App{
		Name:  "Blocklist Merger",
		Usage: "Merge blocklists into a single output file.",
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:     "input_file",
				Usage:    "File containing URLs of blocklists to merge",
				Required: true,
			},
			&cli.StringFlag{
				Name:     "output_file",
				Usage:    "Output file for the merged blocklist",
				Required: true,
			},
			&cli.IntFlag{
				Name:  "workers",
				Value: 10,
				Usage: "Number of worker threads (default: 10)",
			},
			&cli.Float64Flag{
				Name:  "timeout",
				Value: 5.0,
				Usage: "Timeout for domain fetch (default: 5.0)",
			},
		},
		Action: func(c *cli.Context) error {
			return run(
				c.String("input_file"),
				   c.String("output_file"),
				   c.Int("workers"),
				   c.Float64("timeout"),
			)
		},
	}

	if err := app.Run(os.Args); err != nil {
		fmt.Printf("ERROR in main(): %s\n", err)
		os.Exit(1)
	}
}

func run(inputFile, outputFile string, workers int, timeout float64) error {
	fmt.Println("DEBUG: Entering main function")

	if _, err := os.Stat(inputFile); os.IsNotExist(err) {
		return fmt.Errorf("input file does not exist: %s", inputFile)
	}
	fmt.Printf("DEBUG: Input file exists: %s\n", inputFile)

	blocklistURLs, err := loadBlocklistURLs(inputFile)
	if err != nil {
		return err
	}
	fmt.Printf("DEBUG: Found %d URLs\n", len(blocklistURLs))

	if err := fetchDomains(blocklistURLs, workers, timeout); err != nil {
		return err
	}

	if err := writeDomainsToFile(outputFile); err != nil {
		return err
	}

	fmt.Printf("🎉 Merged %d domains into %s\n", len(allDomains), outputFile)
	fmt.Println("DEBUG: Script completed successfully")
	return nil
}

func fetchDomains(urls []string, workers int, timeout float64) error {
	sem := semaphore.NewWeighted(int64(workers))
	bar := progressbar.NewOptions(len(urls), progressbar.OptionShowCount(), progressbar.OptionSetWidth(40))
	var wg sync.WaitGroup

	for _, url := range urls {
		wg.Add(1)

		go func(url string) {
			defer wg.Done()

			if err := sem.Acquire(context.Background(), 1); err != nil {
				fmt.Printf("Semaphore error for %s: %s\n", url, err)
				return
			}
			defer sem.Release(1)

			client := &http.Client{
				Timeout: time.Duration(timeout) * time.Second,
			}

			response, err := client.Get(url)
			if err != nil {
				fmt.Printf("❌ Error fetching %s: %s\n", url, err)
				return
			}
			defer response.Body.Close()

			if response.StatusCode != 200 {
				fmt.Printf("❌ Non-200 response for %s: %d\n", url, response.StatusCode)
				return
			}

			body, err := ioutil.ReadAll(response.Body)
			if err != nil {
				fmt.Printf("❌ Error reading response body from %s: %s\n", url, err)
				return
			}

			domains := extractDomains(string(body))

			domainMu.Lock()
			for _, d := range domains {
				allDomains[d] = struct{}{}
			}
			domainMu.Unlock()

			bar.Add(1)
		}(url)
	}

	wg.Wait()
	return nil
}

func loadBlocklistURLs(filename string) ([]string, error) {
	var urls []string

	file, err := os.Open(filename)
	if err != nil {
		return urls, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" && !strings.HasPrefix(line, "#") {
			urls = append(urls, line)
		}
	}

	return urls, scanner.Err()
}

func extractDomains(data string) []string {
	lines := strings.Split(data, "\n")
	var domains []string

	for _, line := range lines {
		line = cleanDomain(line)
		if line != "" {
			domains = append(domains, line)
		}
	}

	return domains
}

func cleanDomain(line string) string {
	line = strings.TrimSpace(line)

	// Ensure that the line doesn't start with a dot
	if len(line) > 0 && line[0] == '.' {
		return ""
	}

	// Remove prefixes but DO NOT remove "." entirely
	prefixes := []string{"0.0.0.0 ", "127.0.0.1 ", "||", "|", "*. ", "local=/", "."}
	for _, p := range prefixes {
		if strings.HasPrefix(line, p) {
			line = strings.TrimPrefix(line, p)
		}
	}

	line = strings.ReplaceAll(line, " CNAME .", "")

	// Strip comments and filters
	parts := strings.Split(line, "#")
	line = parts[0]

	// Clean up various unwanted characters
	line = strings.SplitN(line, "^", 2)[0]
	line = strings.SplitN(line, " ", 2)[0]
	line = strings.SplitN(line, "\t", 2)[0]
	line = strings.SplitN(line, "/", 2)[0]

	// Remove invalid characters but *not dots*
	unwanted := []string{"^", "$", "*", "/", "?"}
	for _, c := range unwanted {
		line = strings.ReplaceAll(line, c, "")
	}

	return strings.TrimSpace(line)
}



func writeDomainsToFile(filename string) error {
	// Open the file in append mode, create it if it doesn't exist
	f, err := os.OpenFile(filename, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer f.Close()

	domainList := make([]string, 0, len(allDomains))

	for d := range allDomains {
		// Check for leading dot and special characters
		if d != "" && !strings.HasPrefix(d, ".") && !containsSpecialChars(d) {
			domainList = append(domainList, d)
		}
	}

	sort.Strings(domainList)

	for _, domain := range domainList {
		// Write each valid domain followed by a newline
		if _, err := f.WriteString(domain + "\n"); err != nil {
			return err
		}
	}

	return nil
}


// Helper function to check for special characters
func containsSpecialChars(domain string) bool {
	return strings.Contains(domain, "#") || strings.Contains(domain, "!")
}

