#!/usr/bin/env python3
"""
Find exact duplicate thumbnails by comparing file content.
"""

import os
import hashlib
from collections import defaultdict
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def calculate_file_hash(filepath):
    """Calculate MD5 hash of file content."""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
        return None

def find_duplicates(thumbnails_dir):
    """
    Find exact duplicate thumbnails.
    
    Returns:
        dict: {hash: [list of filepaths with same hash]}
    """
    if not os.path.exists(thumbnails_dir):
        logger.error(f"Directory not found: {thumbnails_dir}")
        return {}
    
    # Get all PNG files
    png_files = [f for f in os.listdir(thumbnails_dir) if f.endswith('.png')]
    logger.info(f"Found {len(png_files)} PNG files")
    
    # Calculate hashes
    hash_to_files = defaultdict(list)
    
    for filename in png_files:
        filepath = os.path.join(thumbnails_dir, filename)
        file_hash = calculate_file_hash(filepath)
        if file_hash:
            hash_to_files[file_hash].append(filepath)
    
    # Find duplicates (hashes with more than one file)
    duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
    
    return duplicates

def main(thumbnails_dir, remove=False, output_file=None):
    """
    Main function to find and optionally remove duplicate thumbnails.
    
    Args:
        thumbnails_dir: Directory containing thumbnails
        remove: If True, remove duplicate files (keep first one)
        output_file: Optional file to save list of duplicates
    """
    duplicates = find_duplicates(thumbnails_dir)
    
    if not duplicates:
        logger.info("No exact duplicates found!")
        return
    
    total_duplicates = sum(len(files) - 1 for files in duplicates.values())
    logger.info(f"\nFound {len(duplicates)} sets of duplicates ({total_duplicates} duplicate files)")
    
    # Print duplicates
    duplicate_list = []
    for file_hash, files in duplicates.items():
        logger.info(f"\nDuplicate set (hash: {file_hash[:8]}...):")
        for i, filepath in enumerate(files):
            filename = os.path.basename(filepath)
            if i == 0:
                logger.info(f"  KEEP: {filename}")
                duplicate_list.append(f"KEEP: {filename}")
            else:
                logger.info(f"  DUPLICATE: {filename}")
                duplicate_list.append(f"DUPLICATE: {filename}")
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write("Duplicate Thumbnails\n")
            f.write("=" * 50 + "\n\n")
            for file_hash, files in duplicates.items():
                f.write(f"Hash: {file_hash}\n")
                for i, filepath in enumerate(files):
                    filename = os.path.basename(filepath)
                    status = "KEEP" if i == 0 else "DUPLICATE"
                    f.write(f"  {status}: {filename}\n")
                f.write("\n")
        logger.info(f"\nDuplicate list saved to {output_file}")
    
    # Remove duplicates if requested
    if remove:
        removed_count = 0
        for file_hash, files in duplicates.items():
            # Keep first file, remove rest
            for filepath in files[1:]:
                try:
                    os.remove(filepath)
                    logger.info(f"Removed: {os.path.basename(filepath)}")
                    removed_count += 1
                except Exception as e:
                    logger.error(f"Error removing {filepath}: {e}")
        logger.info(f"\nRemoved {removed_count} duplicate files")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find exact duplicate thumbnails")
    parser.add_argument("--thumbnails-dir", default="thumbnails", help="Directory containing thumbnails")
    parser.add_argument("--remove", action="store_true", help="Remove duplicate files (keeps first one)")
    parser.add_argument("--output", help="Output file to save duplicate list")
    
    args = parser.parse_args()
    
    main(args.thumbnails_dir, args.remove, args.output)

