#!/usr/bin/env python3
"""
Script to find quest stamps that a player has NOT completed yet.
Compares completed stamps from a text file with the complete list from a CSV file.
"""

import argparse
import csv
import os
import sys


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Find quest stamps that a player has NOT completed yet.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default file paths
  python find_missing_stamps.py
  
  # Specify custom input files
  python find_missing_stamps.py -c my_completed.txt -w all_stamps.csv
  
  # Specify all files including output
  python find_missing_stamps.py -c completed.txt -w stamps.csv -o missing.csv
        """
    )
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser.add_argument(
        '-c', '--completed',
        type=str,
        default=os.path.join(script_dir, 'qbexport.txt'),
        help='Path to the file containing completed quest stamps (default: qbexport.txt in script directory)'
    )
    
    parser.add_argument(
        '-w', '--wiki-csv',
        type=str,
        default=os.path.join(script_dir, 'master_list.csv'),
        help='Path to the CSV file containing all quest stamps (default: master_list.csv in script directory)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=os.path.join(script_dir, 'missing_stamps.csv'),
        help='Path to the output CSV file (default: missing_stamps.csv in script directory)'
    )
    
    return parser.parse_args()

def read_completed_stamps(file_path):
    """Read completed stamps from a text file."""
    completed_stamps = set()
    
    if not os.path.exists(file_path):
        print(f"Error: Completed stamps file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reading completed stamps from: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        # Find the separator line (starts with dashes) and start reading after it
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('---'):
                start_idx = i + 1
                break
        
        # If no separator found, skip first 6 lines (header format)
        if start_idx == 0:
            start_idx = 6
        
        # Process from start_idx until we hit the summary line or end of file
        for line in lines[start_idx:]:
            line = line.strip()
            # Stop if we hit the summary line
            if line.startswith('[UB]'):
                break
            # Add non-empty lines as stamps
            if line:
                completed_stamps.add(line)
    
    print(f"Found {len(completed_stamps)} completed stamps")
    return completed_stamps


def read_all_stamps(file_path):
    """Read all stamps from CSV file."""
    all_stamps_data = []
    
    if not os.path.exists(file_path):
        print(f"Error: Wiki stamps CSV file not found: {file_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reading complete stamp list from: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stamp_name = row.get('stamp_name', '').strip()
            if stamp_name:
                all_stamps_data.append(row)
    
    print(f"Found {len(all_stamps_data)} total stamp entries in CSV")
    return all_stamps_data


def find_missing_stamps(completed_stamps, all_stamps_data):
    """Find stamps that are not in the completed list."""
    missing_stamps = []
    
    for row in all_stamps_data:
        stamp_name = row.get('stamp_name', '').strip()
        if stamp_name and stamp_name not in completed_stamps:
            missing_stamps.append(row)
    
    # Sort by stamp name
    missing_stamps.sort(key=lambda x: x.get('stamp_name', ''))
    
    return missing_stamps


def write_output_csv(missing_stamps, output_path):
    """Write missing stamps to CSV file."""
    print(f"Writing results to: {output_path}")
    
    if not missing_stamps:
        print("Warning: No missing stamps found. Creating empty CSV file.")
        # Create empty CSV with headers from the first row of all_stamps_data if available
        return
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    fieldnames = list(missing_stamps[0].keys())
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(missing_stamps)
    
    print(f"Done! Results saved to {output_path}")
    print(f"Total missing stamps: {len(missing_stamps)}")


def main():
    """Main function."""
    args = parse_arguments()
    
    # Read completed stamps
    completed_stamps = read_completed_stamps(args.completed)
    
    # Read all stamps from CSV
    all_stamps_data = read_all_stamps(args.wiki_csv)
    
    # Find missing stamps
    missing_stamps = find_missing_stamps(completed_stamps, all_stamps_data)
    
    print(f"Found {len(missing_stamps)} missing stamps")
    
    # Write output
    write_output_csv(missing_stamps, args.output)


if __name__ == '__main__':
    main()
