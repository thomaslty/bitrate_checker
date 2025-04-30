#!/usr/bin/env python3
import os
import sys
import argparse
import datetime
import glob
from tqdm import tqdm
from tinytag import TinyTag
import concurrent.futures
import subprocess

def check_file_corruption_ffmpeg(file_path):
    """
    Check if an audio file is corrupted using FFmpeg's thorough validation.
    This will attempt to transcode the file, which is a stronger validation
    than just checking metadata.
    
    Returns: (is_corrupt, error_message)
    """
    try:
        # Use ffmpeg with aggressive error detection and null output
        cmd = [
            'ffmpeg', 
            '-v', 'error',           # Only show errors
            '-i', file_path,         # Input file
            '-f', 'null',            # Output to null
            '-err_detect', 'aggressive',  # Use aggressive error detection
            '-'                      # Pipe to stdout (which is discarded)
        ]
        
        # Run ffmpeg and capture any error output
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # If any error output exists, the file is corrupt
        if result.stderr.strip():
            return True, result.stderr.strip()
        
        return False, ""
        
    except Exception as e:
        # If ffmpeg couldn't even run, mark as corrupt
        return True, str(e)

def check_bitrate(file_path, target_bitrate):
    """Check if the given OGG file has the target bitrate."""
    if not file_path.lower().endswith('.ogg'):
        return None
    
    try:
        # Check file size (flag if less than 1MB)
        file_size = os.path.getsize(file_path)
        is_defective_size = file_size < 1048576  # 1MB in bytes
        
        tag = TinyTag.get(file_path)
        actual_bitrate = tag.bitrate
        
        # Check for corruption using FFmpeg
        is_corrupt, corruption_error = check_file_corruption_ffmpeg(file_path)
        
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
            'matches': matches,
            'file_size': file_size,
            'is_defective_size': is_defective_size,
            'is_corrupt': is_corrupt,
            'corruption_error': corruption_error if is_corrupt else ""
        }
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"

def process_path(path, target_bitrate, max_threads=None):
    """Process a file or recursively process a directory using glob."""
    results = []

    if os.path.isfile(path):
        print(f"Error: {path} is not a valid directory")
        sys.exit(1)

    ogg_files = glob.glob(os.path.join(path, '**', '*.ogg'), recursive=True)
    print(f"Found {len(ogg_files)} .ogg files in {path}")
    
    # Use ThreadPoolExecutor for concurrent processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        # Submit all tasks and create a future-to-filename mapping
        future_to_file = {executor.submit(check_bitrate, file_path, target_bitrate): file_path 
                         for file_path in ogg_files}
        
        # Process results as they complete with progress bar
        for future in tqdm(concurrent.futures.as_completed(future_to_file), 
                           total=len(ogg_files), desc="Processing files"):
            result = future.result()
            if result:
                results.append(result)
    
    return results

def main():
    
    parser = argparse.ArgumentParser(description='Check OGG files for specific bitrate')
    parser.add_argument('path', help='Path to an OGG file or directory containing OGG files')
    parser.add_argument('bitrate', type=int, help='Target bitrate to check for (e.g., 320)')
    parser.add_argument('--log-file', help='Path to log file (default: bitrate_check_YYYY-MM-DD_HH-MM-SS.log)')
    parser.add_argument('--delete', action='store_true', 
                       help='Delete files that do not match the target bitrate, files under 1MB, or corrupted files')
    parser.add_argument('--threads', type=int, default=None,
                       help=f'Number of threads to use for processing (default: CPU count * 5')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not delete files, just report what would be deleted')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    # Create log file name with timestamp if not provided
    if not args.log_file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = f"bitrate_check_{timestamp}.log"
    else:
        log_file = args.log_file
    
    results = process_path(args.path, args.bitrate, args.threads)
    
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
        deleted_files = []
        defective_size_files = []
        corrupt_files = []
        
        for result in results:
            if isinstance(result, str):  # Error message
                error_messages.append(result)
            else:
                file_path = result['file']
                actual = result['actual_bitrate']
                matches_target = result['matches']
                should_delete = False
                delete_reason = ""
                
                # Check for defective size
                if result.get('is_defective_size', False):
                    size_mb = result['file_size'] / 1048576
                    defective_size_files.append(f"{file_path}: {size_mb:.2f} MB")
                    # Mark for deletion if flag is set
                    if args.delete:
                        should_delete = True
                        delete_reason = "Defective size (<1MB)"

                # Check for corruption
                if result.get('is_corrupt', False):
                    corrupt_files.append(f"{file_path}")
                    # Mark for deletion if flag is set
                    if args.delete:
                        should_delete = True
                        delete_reason = "Corrupted, error: " + result.get('corruption_error', "")
                
                if matches_target:
                    matching_files.append(f"{file_path}: {actual} kbps")
                else:
                    non_matching_files.append(f"{file_path}: {actual} kbps")
                    # Mark for deletion if flag is set
                    if args.delete:
                        should_delete = True
                        delete_reason = "Non-matching bitrate, current bitrate: " + str(actual) + " kbps"

                # Dry run
                if args.dry_run and should_delete:
                    if args.verbose:
                        deleted_files.append(f"{file_path}\nReason: {delete_reason}")
                    else:
                        deleted_files.append(f"{file_path}")
                    continue
                
                # Delete file if needed
                if should_delete and args.delete and not args.dry_run:
                    try:
                        os.remove(file_path)
                        if args.verbose:
                            deleted_files.append(f"{file_path}\nReason: {delete_reason}")
                        else:
                            deleted_files.append(f"{file_path}")
                    except Exception as e:
                        error_messages.append(f"Failed to delete {file_path}: {str(e)}")
        
        # Add matching files section
        if matching_files and args.verbose:
            output_lines.append(f"\n✓ MATCHING FILES ({len(matching_files)}):")
            output_lines.append("-" * 60)
            output_lines.extend(matching_files)
        
        # Add non-matching files section
        if non_matching_files:
            output_lines.append(f"\n✗ NON-MATCHING FILES ({len(non_matching_files)}):")
            output_lines.append("-" * 60)
            output_lines.extend(non_matching_files)
        
        # Add defective size files section
        if defective_size_files:
            output_lines.append(f"\n⚠ DEFECTIVE SIZE FILES (<1MB) ({len(defective_size_files)}):")
            output_lines.append("-" * 60)
            output_lines.extend(defective_size_files)
        
        # Add corrupt files section
        if corrupt_files:
            output_lines.append(f"\n⚠ POTENTIALLY CORRUPTED FILES ({len(corrupt_files)}):")
            output_lines.append("-" * 60)
            output_lines.extend(corrupt_files)

        # Add deleted files section
        if deleted_files:
            output_lines.append(f"\nDELETED FILES ({len(deleted_files)}):")
            output_lines.append("-" * 60)
            output_lines.extend(deleted_files)
        
        # Add error section if any
        if error_messages:
            output_lines.append(f"\nERRORS ({len(error_messages)}):")
            output_lines.append("-" * 60)
            output_lines.extend(error_messages)
        
        # Add summary
        output_lines.append("\n" + "=" * 60)
        summary = f"Summary: {len(matching_files)} matches, {len(non_matching_files)} non-matches"
        if len(defective_size_files) > 0:
            summary += f", {len(defective_size_files)} defective size"
        if len(corrupt_files) > 0:
            summary += f", {len(corrupt_files)} potentially corrupted"
        if args.delete:
            summary += f", {len(deleted_files)} deleted"
        summary += f", {len(error_messages)} errors"
        output_lines.append(summary)
    
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