# master-guard

master-guard is a small open source file integrity monitoring tool for Linux systems.
It detects unauthorized file changes by storing SHA-256 hashes for selected files, then scanning for changes.


## What it does

- creates a trusted baseline snapshot of one or more paths
- detects file modifications by comparing SHA-256 hashes
- detects newly added files
- detects deleted files
- shows git-style unified diffs for text file changes
- stores every scan result and patch files on disk
- supports live monitoring and terminal notifications
- allows manual approval of expected changes


## How it works

1. run init to scan selected paths and write metadata and file hashes to a local JSON file
2. run scan to compare current file state with baseline
3. if expected changes happened, run approve to update the baseline


## Requirements

- Python 3.10+


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

When changes are detected, `scan` now:

- prints unified diff output (similar to `git diff`) for changed text files
- writes a timestamped report directory next to the baseline file:
	- `master-guard-reports/<timestamp>/summary.json`
	- `master-guard-reports/<timestamp>/combined.patch`
	- `master-guard-reports/<timestamp>/diffs/*.diff`

For binary, non-UTF-8, or large files, the report notes that a text diff is not available.

`baseline.json` and `master-guard-reports/` are automatically excluded from tracked results.

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

Interactive mode:

```bash
master-guard approve --baseline baseline.json
```

Non-interactive mode:

```bash
master-guard approve --baseline baseline.json --yes
```

### Live monitoring

Run a continuous scanner that detects changes as they happen:

```bash
master-guard monitor --baseline baseline.json --interval 2 --events-file live-events.jsonl
```

Live monitor behavior:

- prints change notifications in the terminal
- writes one JSON object per line to `live-events.jsonl`
- writes per-change diff report folders in `master-guard-reports/`


## Baseline file format

The baseline is a JSON document containing:

- version
- created_at timestamp
- scanned paths
- files mapping of absolute file path -> object with:
	- `sha256` hex digest
	- optional `text` snapshot for UTF-8 files up to a safety size limit


## Project structure

```text
src/master_guard/
	cli.py       # command-line commands
	hashing.py   # SHA-256 hashing helpers
	scanner.py   # snapshot build and compare logic
	storage.py   # baseline read/write
	models.py    # report model
```
