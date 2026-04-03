# master-guard

master-guard is a small open source file integrity monitoring tool for Linux systems.
It helps detect unauthorized file changes by storing trusted SHA-256 hashes for selected files, then scanning for drift.

## what it does

- creates a trusted baseline snapshot of one or more paths
- detects file modifications by comparing SHA-256 hashes
- detects newly added files
- detects deleted files
- allows manual approval of expected changes and baseline refresh

## how it works

1. run init to scan selected paths and write baseline metadata + file hashes to a local JSON file
2. run scan to compare current file state with baseline
3. if expected changes happened, run approve to update the baseline

this is useful for detecting suspicious changes in directories like:

- /etc
- /usr/bin
- any custom directory you choose

## requirements

- linux (developed for ubuntu-style environments)
- python 3.10+

## installation

from the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## usage

### create a baseline

```bash
master-guard init --paths /etc /usr/bin --baseline baseline.json
```

### run an integrity scan

```bash
master-guard scan --baseline baseline.json
```

exit code behavior:

- 0 = no file changes detected
- 1 = changes detected (added, modified, or deleted)
- 2 = usage or baseline errors

### approve expected changes

interactive mode:

```bash
master-guard approve --baseline baseline.json
```

non-interactive mode:

```bash
master-guard approve --baseline baseline.json --yes
```

## baseline file format

the baseline is a JSON document containing:

- version
- created_at timestamp
- scanned paths
- files mapping of absolute file path -> sha256 hex digest

## project structure

```text
src/master_guard/
	cli.py       # command-line commands
	hashing.py   # SHA-256 hashing helpers
	scanner.py   # snapshot build and compare logic
	storage.py   # baseline read/write
	models.py    # report model
```

## security notes

- run with least privilege where possible
- protect baseline files with strict permissions
- treat baseline updates as a controlled event
- scan errors (for example permissions) are shown so you can investigate coverage gaps

## license

MIT
