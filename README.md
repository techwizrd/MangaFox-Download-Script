# MangaFox Download Script

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/techwizrd/MangaFox-Download-Script/actions/workflows/ci.yml/badge.svg)](https://github.com/techwizrd/MangaFox-Download-Script/actions/workflows/ci.yml)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-46a2f1.svg)](https://docs.astral.sh/ruff/)
[![Type check: ty](https://img.shields.io/badge/type%20check-ty-0d9488.svg)](https://github.com/astral-sh/ty)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-0a9edc.svg)](https://docs.pytest.org/)
[![Pre-commit: prek](https://img.shields.io/badge/pre--commit-prek-fab040.svg)](https://github.com/j178/prek)

This project downloads manga chapter images and can optionally package each
chapter into a `.cbz` archive.

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
