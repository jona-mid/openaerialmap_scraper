#!/usr/bin/env python3
"""
Download TIF files based on thumbnail filenames.
Matches thumbnail base names to CSV uuid column and downloads TIF files.
"""

import pandas as pd
import requests
import os
import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tif_download.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def download_tif(url, output_path):
    """Download TIF file from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=60, headers=headers, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False

def main(csv_file, thumbnails_dir, output_dir, delay=0.5):
    """
    Main function to download TIF files based on thumbnail filenames.
    
    Args:
        csv_file: Path to CSV file with uuid column
        thumbnails_dir: Directory containing thumbnail PNG files
        output_dir: Directory to save TIF files
        delay: Delay between downloads in seconds
    """
    # Load CSV
    try:
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded {len(df)} rows from {csv_file}")
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return
    
    if 'uuid' not in df.columns:
        logger.error("Column 'uuid' not found in CSV")
        return
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get list of thumbnail files
    if not os.path.exists(thumbnails_dir):
        logger.error(f"Thumbnails directory not found: {thumbnails_dir}")
        return
    
    thumbnail_files = [f for f in os.listdir(thumbnails_dir) if f.endswith('.png')]
    logger.info(f"Found {len(thumbnail_files)} thumbnail files")
    
    # Extract base names from thumbnails (remove .png extension)
    thumbnail_bases = {f[:-4]: f for f in thumbnail_files}
    
    # Match thumbnails to CSV rows and download TIFs
    downloaded_count = 0
    failed_count = 0
    skipped_count = 0
    not_found_count = 0
    
    for base_name, thumbnail_file in thumbnail_bases.items():
        # Find matching row in CSV where uuid contains the base name
        matching_rows = df[df['uuid'].str.contains(base_name, na=False)]
        
        if len(matching_rows) == 0:
            logger.warning(f"No matching CSV row for thumbnail: {thumbnail_file}")
            not_found_count += 1
            continue
        
        # Use first match
        row = matching_rows.iloc[0]
        tif_url = row['uuid']
        
        # Extract filename from URL
        parsed_url = urlparse(tif_url)
        tif_filename = os.path.basename(parsed_url.path)
        
        if not tif_filename.endswith('.tif'):
            tif_filename += '.tif'
        
        output_path = os.path.join(output_dir, tif_filename)
        
        # Skip if already exists
        if os.path.exists(output_path):
            logger.info(f"File already exists, skipping: {tif_filename}")
            skipped_count += 1
            continue
        
        # Download TIF
        logger.info(f"Downloading {tif_filename}...")
        if download_tif(tif_url, output_path):
            downloaded_count += 1
        else:
            failed_count += 1
        
        # Delay between downloads
        if delay > 0:
            time.sleep(delay)
    
    logger.info(f"\nDownload Summary:")
    logger.info(f"Successfully downloaded: {downloaded_count}")
    logger.info(f"Failed to download: {failed_count}")
    logger.info(f"Skipped (already existed): {skipped_count}")
    logger.info(f"Not found in CSV: {not_found_count}")
    logger.info(f"Total processed: {downloaded_count + failed_count + skipped_count + not_found_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download TIF files based on thumbnail filenames")
    parser.add_argument("--csv", default="results_gee_filtered.csv", help="CSV file path")
    parser.add_argument("--thumbnails-dir", default="thumbnails", help="Directory containing thumbnails")
    parser.add_argument("--output-dir", default="tifs", help="Output directory for TIF files")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between downloads in seconds")
    
    args = parser.parse_args()
    
    main(args.csv, args.thumbnails_dir, args.output_dir, args.delay)

