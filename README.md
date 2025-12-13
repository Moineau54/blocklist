# Blocklist

[![Convert to uBlock Origin Format](https://github.com/Moineau54/blocklist/actions/workflows/convert-ublock.yml/badge.svg)](https://github.com/Moineau54/blocklist/actions/workflows/convert-ublock.yml)

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
| [suspicious.txt](suspicious.txt) | contains suspicious domains |
| [telemetry.txt](telemetry.txt) | contains domains used for telemetry |
| [porn.txt](porn.txt) | contains porn website domains |
| [forums.txt](forums.txt) | contains the domains of forums harmful to children |
| [csam.txt](csam.txt) | sites that may contain (no checked) or do contain csam and have been reported to the police (for example: the french police on their online plattform) |
| [zoophilia.txt](zoophilia.txt) | sites that contain zoophilic content and have been reported |

## To add to Pi-hole

```shell
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/advertisement.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/malware.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/phishing.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/spam.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/tracking.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/fingerprinting.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/suspicious.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/telemetry.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/csam.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/zoophilia.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/porn.txt
```

## To add to Ublock Origins

```shell
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/advertisement_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/malware_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/phishing_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/spam_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/tracking_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/fingerprinting_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/suspicious_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/telemetry_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/csam_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/zoophilia_ublock.txt
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/porn_ublock.txt
```

### Others:

#### Forums:

##### Pi-hole:
```shell
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/forums.txt
```

##### Ublock Origins:
```shell
https://raw.githubusercontent.com/Moineau54/blocklist/refs/heads/main/forums_ublock.txt
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

## For false positives
In case of a false positive, feel free to contact me or create an issue.

## Is it okay to implement content from other blocklists
Yes it is, as long as you follow their licences. I made, with the help of ai, scripts to merge remote blocklists to any any of the lists in this repo. Just verify that the scripts can handle properly the content in the remote blocklists.
