# Quest Stamp Tracker

A Python script to find quest stamps that a player has **not completed yet** by comparing their completed stamps against a complete list of all available quest stamps.

## Overview

This tool helps Asheron's Call players track their quest completion progress by:
- Reading a list of completed quest stamps from a text file
- Comparing against a complete list of all quest stamps from a CSV file
- Generating a CSV report of all missing stamps with quest details

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## File Structure

All files are located in the `stamp-tracker` folder:
- `find_missing_stamps.py` - The main script
- `qbexport.txt` - Your completed quest stamps (input)
- `master_list.csv` - Complete list of all quest stamps (input)
- `missing_stamps.csv` - Generated output file with missing stamps
- `README.md` - This file
- `community_stamp_info.csv` - (Optional) community metadata keyed by `stamp_name`
- `extract_willow_to_csv.py` - Maintainer script to generate `community_stamp_info.csv` from the Willow workbook

## Usage

### Basic Usage (Default Files)

Navigate to the `stamp-tracker` folder and run:

```bash
python find_missing_stamps.py
```

This will automatically use files in the same directory:
- Read completed stamps from: `qbexport.txt`
- Read all stamps from: `master_list.csv`
- Output results to: `missing_stamps.csv`

### Custom File Paths

You can specify custom input and output files using command-line flags:

```bash
python find_missing_stamps.py -c completed_stamps.txt -w all_stamps.csv -o missing.csv
```

### Command-Line Options

| Flag | Long Form | Description | Default |
|------|-----------|-------------|---------|
| `-c` | `--completed` | Path to file containing completed quest stamps | `qbexport.txt` (in script directory) |
| `-w` | `--wiki-csv` | Path to CSV file with all quest stamps | `master_list.csv` (in script directory) |
| `-o` | `--output` | Path to output CSV file | `missing_stamps.csv` (in script directory) |
| `-h` | `--help` | Show help message and exit | - |

### Examples

**Example 1: Use default files (from stamp-tracker directory)**
```bash
cd stamp-tracker
python find_missing_stamps.py
```

**Example 2: Custom input files**
```bash
python find_missing_stamps.py -c my_completed.txt -w all_stamps.csv
```

**Example 3: Specify all files including output**
```bash
python find_missing_stamps.py -c completed.txt -w stamps.csv -o missing.csv
```

**Example 4: Use files from different directories**
```bash
python find_missing_stamps.py -c ../other_folder/completed.txt -w ../other_folder/stamps.csv -o results.csv
```

**Example 4: Get help**
```bash
python find_missing_stamps.py --help
```

## Input File Formats

### Completed Stamps File (Text Format)

The completed stamps file should be a text file with one stamp name per line. The script automatically:
- Skips the first 2 lines (header messages)
- Stops reading when it encounters a line starting with `[UB]` or an empty line

Example format:
```
Copying chat to LyncherQB.txt.  Run command again with no arguments to turn off logging.
Your completed quest bonus list:
2_9_25Event1
2024LeaftideChristmasGift
2025LeaftideChristmasGift
2HGauntsGiven
30MinAttributes
...
[UB] Quest bonus data updated. Found 4652 quest bonus flags.
```

### Complete Stamps CSV File

The complete stamps CSV file should have the following columns:
- `stamp_name` - The quest stamp identifier (required)
- `quest_name` - The name of the quest
- `quest_url` - URL to quest information
- `source` - Source of the stamp data
- `num_accounts` - Number of accounts (optional)
- `in_csv` - Whether the stamp is in CSV (optional)

Example format:
```csv
stamp_name,quest_name,quest_url,source,num_accounts,in_csv
ProdigalHarby_Completed,Aerbax's Prodigal Harbinger,https://leaftidewiki.com/...,wiki,,True
ColoR1Completed,Colosseum Arena,https://leaftidewiki.com/...,wiki,,True
```

## Output Format

The script generates a CSV file containing all missing stamps with the same columns as the input CSV file. The stamps are sorted alphabetically by stamp name.

Output columns:
- `stamp_name` - The quest stamp identifier
- `quest_name` - The name of the quest
- `quest_url` - URL to quest information
- `source` - Source of the stamp data
- `num_accounts` - Number of accounts (if present in input)
- `in_csv` - Whether the stamp is in CSV (if present in input)

## How It Works

1. **Read Completed Stamps**: Parses the text file to extract all completed stamp names
2. **Read All Stamps**: Loads the complete list of stamps from the CSV file
3. **Compare**: Finds stamps that exist in the complete list but not in the completed list
4. **Generate Report**: Creates a CSV file with all missing stamps and their details

## Error Handling

The script will exit with an error message if:
- The completed stamps file cannot be found
- The wiki CSV file cannot be found
- The output directory cannot be created (if needed)

## Tips

- The output CSV can be opened in Excel, Google Sheets, or any spreadsheet application
- You can filter and sort the results by any column to prioritize which quests to complete
- Use the `quest_url` column to quickly access quest information
- The script preserves all columns from the input CSV, so you can add custom columns if needed

## Troubleshooting

**Problem**: Script says file not found
- **Solution**: Check that the file paths are correct. Use absolute paths if relative paths don't work.

**Problem**: No missing stamps found
- **Solution**: This is normal if you've completed all quests! The script will still create an empty CSV file.

**Problem**: Encoding errors
- **Solution**: The script uses UTF-8 encoding. If your files use a different encoding, convert them to UTF-8 first.

## License

This script is provided as-is for personal use.
