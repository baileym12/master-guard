# master-guard

master-guard is a small open source file integrity monitoring tool for Linux systems.
It detects unauthorized file changes by storing SHA-256 hashes for selected files, then scanning for changes.


## What it does

- creates a trusted baseline snapshot of one or more paths
- detects file modifications by comparing SHA-256 hashes
- detects newly added files
- detects deleted files
- allows manual approval of expected changes
- runs a continuous live monitoring loop
- serves a web dashboard to visualize live events


## How it works

1. run init to scan selected paths and write metadata and file hashes to a local JSON file
2. run scan to compare current file state with baseline
3. if expected changes happened, run approve to update the baseline
4. alternatively, run monitor to continuously check for changes in real-time
5. run dashboard to view a visualization of the monitored events


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


### Initialize a baseline

Create a baseline snapshot of directories or files to be monitored:

```bash
master-guard init --paths /etc /usr/bin --baseline baseline.json
```

**Flags:**
- `--paths`: (Required) One or more paths to scan.
- `--baseline`: Path to save the baseline JSON file (default: `baseline.json`).

### Run an integrity scan

Run a one-off comparison of the current file state against the baseline:

```bash
master-guard scan --baseline baseline.json
```

**Flags:**
- `--baseline`: Path to the baseline JSON file (default: `baseline.json`).

### Schedule scans with cron

>Example crontab entry to run every 15 minutes and append output to a log file:

```cron
*/15 * * * * /bin/bash -lc 'source /<path-to-project>/master-guard/.venv/bin/activate && master-guard scan --baseline <path-to-baseline> >> /var/log/master-guard-scan.log 2>&1'
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

Update the baseline after authorized file changes have been made.

Interactive mode:

```bash
master-guard approve --baseline baseline.json
```

Non-interactive mode (auto-yes):

```bash
master-guard approve --baseline baseline.json --yes
```

**Flags:**
- `--baseline`: Path to the baseline JSON file (default: `baseline.json`).
- `--yes`: Approve all changes without prompting.


### Monitor live changes

Run a continuous monitoring loop to detect changes in real-time and log them to a file:

```bash
master-guard monitor --baseline baseline.json --interval 2.0 --events-file live-events.jsonl
```

**Flags:**
- `--baseline`: Path to the baseline JSON file (default: `baseline.json`).
- `--interval`: Polling interval in seconds (default: `2.0`).
- `--events-file`: Path to live event log file (default: `live-events.jsonl`).


### View the dashboard

Launch the web dashboard to visualize live monitoring events:

```bash
master-guard dashboard --host 127.0.0.1 --port 8080 --root . --events-file live-events.jsonl
```

**Flags:**
- `--host`: Host IP to bind the dashboard to (default: `127.0.0.1`).
- `--port`: Port to run the dashboard on (default: `8080`).
- `--root`: Directory to serve (default: `.`).
- `--events-file`: Path to live event log file (default: `live-events.jsonl`).

## Baseline file format

The baseline is a JSON document containing:

- version
- created_at timestamp
- scanned paths
- files mapping of absolute file path -> sha256 hex digest


## Project structure

```text
src/master_guard/
	cli.py       # command-line commands
	dashboard.py # web dashboard server
	hashing.py   # SHA-256 hashing helpers
	models.py    # report model
	monitor.py   # live monitoring loop
	scanner.py   # snapshot build and compare logic
	storage.py   # baseline read/write
```
