# Blocklist

## Index

- [Blocklist](#blocklist)
  - [Index](#index)
  - [Description](#description)
  - [List of blocklists](#list-of-blocklists)
  - [To add to Pi-hole or ublock](#to-add-to-pi-hole-or-ublock)
  - [To anyone wanting to contribute](#to-anyone-wanting-to-contribute)
    - [How to add a domain in malware.txt, tracking.txt or advertisement.txt](#how-to-add-a-domain-in-malwaretxt-trackingtxt-or-advertisementtxt)
      - [malware.txt](#malwaretxt)
      - [tracking.txt and advertisement.txt](#trackingtxt-and-advertisementtxt)

## Description

This is a blocklist repo for tools like [Pi-hole](https://docs.pi-hole.net/) and others.

## List of blocklists

| List name | Description |
|---|---|
| [advertisement.txt](advertisment.txt) | contains ads domains. |
| [malware.txt](malware.txt) | contains domains flagged for having malware. |
| [tracking.txt](tracking.txt) | contains tracking domains. |
| [spam.txt](spam.txt) | contains spam domains |
| [phishing.txt](phishing.txt) | contains phishing domains |
| [fingerprinting.txt](fingerprinting.txt) | contains fingerprinting domains |

## To add to Pi-hole or ublock

```shell
https://github.com/Moineau54/blocklist/raw/refs/heads/main/advertisement.txt
https://github.com/Moineau54/blocklist/raw/refs/heads/main/malware.txt
https://github.com/Moineau54/blocklist/raw/refs/heads/main/phishing.txt
https://github.com/Moineau54/blocklist/raw/refs/heads/main/spam.txt
https://github.com/Moineau54/blocklist/raw/refs/heads/main/tracking.txt
```

## To anyone wanting to contribute

Feel free to do so. Just use the **dev** branch to push stuff as the **main** branch will only be for the releases.

### How to add a domain in malware.txt, tracking.txt or advertisement.txt

#### malware.txt

```shell
# Virus / malware name
domain (no https://)
```

#### tracking.txt and advertisement.txt

```shell
# Company owning the domain
domain (no https://)
```
