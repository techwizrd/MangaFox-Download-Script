# MangaFox Download Script

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/techwizrd/MangaFox-Download-Script/actions/workflows/ci.yml/badge.svg)](https://github.com/techwizrd/MangaFox-Download-Script/actions/workflows/ci.yml)

This project downloads manga chapter images and can optionally package each
chapter into a `.cbz` archive.

This script is intended for archival/offline reading use cases (for example,
downloading chapters before a flight). Users are responsible for complying
with Fanfox [Terms of Service](https://fanfox.net/teams/).

The script is now maintained as a Python 3.11+ project with linting, type
checking, tests, and pre-commit hooks.

## Runtime requirements

- Python 3.11+
- `beautifulsoup4`

## Usage

Mandatory argument:

- `-m`, `--manga <Manga Name>`

Optional arguments:

- `-s`, `--start <chapter>` start chapter (float supported)
- `-e`, `--end <chapter>` end chapter (float supported)
- `-c`, `--cbz` create CBZ archive after download
- `-r`, `--remove` remove image files after CBZ creation
- `-f`, `--force` redownload chapters even when matching `.cbz` files already exist
- `-l`, `--list` list chapter numbers and exit
- `-d`, `--debug` show HTTP request debug output
- `--profile <safe|balanced|aggressive>` performance profile (default: `safe`)
- `--workers <count>` concurrent image downloads (overrides profile)
- `--delay <seconds>` average delay between retry attempts (overrides profile)
- `--max-retries <count>` max retries per image download (overrides profile)

Examples:

```bash
python3 mfdl.py -m "The World God Only Knows"
python3 mfdl.py -m "The World God Only Knows" -s 222.5 -e 222.5
python3 mfdl.py -m "The World God Only Knows" -s 190 -e 205 -c -r
python3 mfdl.py -m "One Piece" -c -r --force
python3 mfdl.py -m "The World God Only Knows" --list
python3 mfdl.py -m "One Piece" --profile balanced -c -r
```

## Development setup

Install dev dependencies:

```bash
uv sync --extra dev
```

Run quality checks directly:

```bash
uv run ruff check .
uv run ruff format .
uv run prek run markdownlint --all-files
uv run ty check mfdl.py tests
uv run pytest -q
```

## Pre-commit (`prek`)

This repository uses `.pre-commit-config.yaml` and is intended to be executed
with `prek`.

```bash
uv run prek install
uv run prek run --all-files
```

`pytest` is configured on the `pre-push` stage to keep normal commits fast.
