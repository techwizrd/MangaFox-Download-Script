# MangaFox Download Script

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
- `--delay <seconds>` average delay between image requests
- `--max-retries <count>` max retries per image download

Examples:

```bash
python3 mfdl.py -m "The World God Only Knows"
python3 mfdl.py -m "The World God Only Knows" -s 222.5 -e 222.5
python3 mfdl.py -m "The World God Only Knows" -s 190 -e 205 -c -r
python3 mfdl.py -m "The World God Only Knows" --list
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
