# Master Guard

Master Guard is a small open source file integrity monitoring tool for Linux systems.
It helps detect unauthorized file changes by storing trusted SHA-256 hashes for selected files, then scanning for changes.

## What it does

- creates a trusted baseline snapshot of one or more paths
- detects file modifications by comparing SHA-256 hashes
- detects newly added files
- detects deleted files
- allows manual approval of expected changes

## How it works

1. run init to scan selected paths and write metadata and file hashes to a local JSON file
2. run scan to compare current file state with baseline
3. if expected changes happened, run approve to update the baseline

## Requirements

- python 3.10+

## Installation

from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### Create a baseline

```bash
master-guard init --paths /etc /usr/bin --baseline baseline.json
```

### Run an integrity scan

```bash
master-guard scan --baseline baseline.json
```

### Schedule scans with cron

>Example crontab entry to run every 15 minutes and append output to a log file:

```cron
*/15 * * * * /bin/bash -lc 'source /<path-to-project>/master-guard/.venv/bin/activate && master-guard scan --baseline <path-to-basline> >> /var/log/master-guard-scan.log 2>&1'
```

notes:
- create the baseline first with `master-guard init ...`
- make sure the user running cron has read access to scanned paths and write access to the log file
- use `crontab -e` to add the job and `crontab -l` to verify it

### Exit codes:

- 0 = no file changes detected
- 1 = changes detected (added, modified, or deleted)
- 2 = error

### Approve expected changes

interactive mode:

```bash
master-guard approve --baseline baseline.json
```

non-interactive mode:

```bash
master-guard approve --baseline baseline.json --yes
```

## Baseline file format

the baseline is a JSON document containing:

- version
- created_at timestamp
- scanned paths
- files mapping of absolute file path -> sha256 hex digest

## Project structure

```text
src/master_guard/
	cli.py       # command-line commands
	hashing.py   # SHA-256 hashing helpers
	scanner.py   # snapshot build and compare logic
	storage.py   # baseline read/write
	models.py    # report model
```