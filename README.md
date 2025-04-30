# OGG Bitrate Checker

A simple command-line utility to check if OGG audio files have a specific bitrate.

## Setup

### Virtual Environment
First, create and activate a virtual environment:

```
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate
```

### Installation

1. Ensure you have Python 3.6+ installed
2. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

```
python ogg_bitrate_checker.py PATH BITRATE [--log-file LOG_FILE]
```

Arguments:
- `PATH`: Path to an OGG file or directory containing OGG files
- `BITRATE`: Target bitrate to check for (e.g., 320)

Optional arguments:
- `--log-file LOG_FILE`: Custom path for the log file (default: bitrate_check_YYYY-MM-DD_HH-MM-SS.log)

## Examples

Check a single file:
```
python ogg_bitrate_checker.py music/song.ogg 320
```

Check all OGG files in a directory:
```
python ogg_bitrate_checker.py music/ 320
```

## Output

The script will output:
- A list of each file with its actual bitrate and whether it matches the target
- A summary of how many files matched, didn't match, or had errors
- All results are saved to a log file in the current directory