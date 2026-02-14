package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"strings"
)

const (
	Green  = "\033[1;32m"
	Yellow = "\033[1;33m"
	Reset  = "\033[0m"
)

func processFile(filename string) error {
	file, err := os.Open(filename)
	if err != nil {
		return err
	}
	defer file.Close()

	var lines []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		// Preserve newline like Python readlines()
		lines = append(lines, scanner.Text()+"\n")
	}
	if err := scanner.Err(); err != nil {
		return err
	}

	fmt.Printf("%s%s %d lines to process%s\n", Green, filename, len(lines), Reset)

	// Clear file
	if err := os.WriteFile(filename, []byte(""), 0644); err != nil {
		return err
	}

	outFile, err := os.OpenFile(filename, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	defer outFile.Close()

	writer := bufio.NewWriter(outFile)
	defer writer.Flush()

	seen := make(map[string]bool)
	uniqueCount := 0

	for i, line := range lines {
		// Empty or whitespace-only lines are always written
		if strings.TrimSpace(line) == "" {
			_, _ = writer.WriteString(line)
		} else if !seen[line] {
			seen[line] = true
			uniqueCount++
			_, _ = writer.WriteString(line)
		}

		fmt.Printf("\rProcessing %s... %d/%d", filename, i+1, len(lines))
	}

	fmt.Println()
	fmt.Printf("%sProcessed %d unique lines in %s%s\n",
		Yellow, uniqueCount, filename, Reset)

	return nil
}

func main() {
	fileFlag := flag.String("f", "", "Specific file to process")
	flag.Parse()

	defaultFiles := []string{
		"advertisement.txt",
		"all_lists.txt",
		"csam.txt",
		"fingerprinting.txt",
		"forums.txt",
		"malware.txt",
		"porn.txt",
		"phishing.txt",
		"socials.txt",
		"spam.txt",
		"suspicious.txt",
		"telemetry.txt",
		"to_monitor.txt",
		"tracking.txt",
		"zoophilia.txt",
	}

	if *fileFlag != "" {
		if err := processFile(*fileFlag); err != nil {
			fmt.Println("Error:", err)
			os.Exit(1)
		}
	} else {
		for _, file := range defaultFiles {
			if err := processFile(file); err != nil {
				fmt.Println("Error:", err)
			}
		}
	}

	fmt.Printf("%sDone!%s\n", Yellow, Reset)
}
