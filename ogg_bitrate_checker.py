#!/usr/bin/env python3
import os
import sys
import argparse
import datetime
import glob
from tqdm import tqdm
from tinytag import TinyTag

def check_bitrate(file_path, target_bitrate):
    """Check if the given OGG file has the target bitrate."""
    if not file_path.lower().endswith('.ogg'):
        return None
    
    try:
        tag = TinyTag.get(file_path)
        actual_bitrate = tag.bitrate
        
        # Some files might report bitrate as None
        if actual_bitrate is None:
            return f"Unknown bitrate for {file_path}"
            
        # Round to nearest whole number for comparison
        actual_bitrate = round(actual_bitrate)
        
        matches = actual_bitrate == target_bitrate
        return {
            'file': file_path,
            'actual_bitrate': actual_bitrate,
            'target_bitrate': target_bitrate,
            'matches': matches
        }
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"

def process_path(path, target_bitrate):
    """Process a file or recursively process a directory using glob."""
    results = []

    if os.path.isfile(path):
        print(f"Error: {path} is not a valid directory")
        sys.exit(1)

    ogg_files = glob.glob(os.path.join(path, '**', '*.ogg'), recursive=True)
    print(f"Found {len(ogg_files)} .ogg files in {path}")
    for file_path in tqdm(ogg_files, desc="Processing files"):
            result = check_bitrate(file_path, target_bitrate)
            if result:
                results.append(result)
    
        
    return results

def main():
    parser = argparse.ArgumentParser(description='Check OGG files for specific bitrate')
    parser.add_argument('path', help='Path to an OGG file or directory containing OGG files')
    parser.add_argument('bitrate', type=int, help='Target bitrate to check for (e.g., 320)')
    parser.add_argument('--log-file', help='Path to log file (default: bitrate_check_YYYY-MM-DD_HH-MM-SS.log)')
    
    args = parser.parse_args()
    
    # Create log file name with timestamp if not provided
    if not args.log_file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = f"bitrate_check_{timestamp}.log"
    else:
        log_file = args.log_file
    
    results = process_path(args.path, args.bitrate)
    
    # Prepare results text
    output_lines = []
    output_lines.append(f"\nBitrate Check Results (Target: {args.bitrate} kbps):")
    output_lines.append("=" * 60)
    
    if not results:
        output_lines.append("No OGG files found!")
    else:
        # Separate results into matches, non-matches, and errors
        matching_files = []
        non_matching_files = []
        error_messages = []
        
        matches = 0
        non_matches = 0
        errors = 0
        
        for result in results:
            if isinstance(result, str):  # Error message
                error_messages.append(result)
                errors += 1
            else:
                file_path = result['file']
                actual = result['actual_bitrate']
                matches_target = result['matches']
                
                if matches_target:
                    matching_files.append(f"{file_path}: {actual} kbps")
                    matches += 1
                else:
                    non_matching_files.append(f"{file_path}: {actual} kbps")
                    non_matches += 1
        
        # Add matching files section
        if matching_files:
            output_lines.append(f"\n✓ MATCHING FILES ({matches}):")
            output_lines.append("-" * 60)
            output_lines.extend(matching_files)
        
        # Add non-matching files section
        if non_matching_files:
            output_lines.append(f"\n✗ NON-MATCHING FILES ({non_matches}):")
            output_lines.append("-" * 60)
            output_lines.extend(non_matching_files)
        
        # Add error section if any
        if error_messages:
            output_lines.append(f"\nERRORS ({errors}):")
            output_lines.append("-" * 60)
            output_lines.extend(error_messages)
        
        # Add summary
        output_lines.append("\n" + "=" * 60)
        output_lines.append(f"Summary: {matches} matches, {non_matches} non-matches, {errors} errors")
    
    # Print to console
    for line in output_lines:
        print(line)
    
    # Write to log file
    with open(log_file, 'w') as f:
        f.write(f"OGG Bitrate Check - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Path: {args.path}\n")
        f.write(f"Target Bitrate: {args.bitrate} kbps\n\n")
        for line in output_lines:
            f.write(line + '\n')
    
    print(f"\nResults saved to {log_file}")

if __name__ == "__main__":
    main() 