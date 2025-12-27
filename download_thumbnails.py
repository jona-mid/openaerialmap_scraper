#!/usr/bin/env python3
"""
Server-ready script to download thumbnails from results_gee_filtered.csv
Uses the filename from the thumbnail URL (keeps original name).
Skips already downloaded thumbnails.
"""

import pandas as pd
import requests
import os
from pathlib import Path
import time
import argparse
import logging
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("thumbnail_download.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def download_thumbnail(url, folder="thumbnails"):
    """
    Download a PNG thumbnail from a URL and save it with the filename from the URL.
    
    Args:
        url (str): The URL of the thumbnail to download
        folder (str): The folder to save the thumbnail in
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    if not url or pd.isna(url):
        logger.warning(f"Empty URL provided")
        return False
    
    # Extract filename from URL
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    
    # If no filename in URL, create a generic one
    if not filename or '.' not in filename:
        filename = f"thumbnail_{int(time.time())}.png"
    
    # Ensure the file has a .png extension
    if not filename.endswith('.png'):
        filename += '.png'
    
    # Create folder if it doesn't exist
    Path(folder).mkdir(parents=True, exist_ok=True)
    
    filepath = os.path.join(folder, filename)
    
    # Skip if file already exists
    if os.path.exists(filepath):
        logger.info(f"File already exists, skipping: {filename}")
        return True
    
    try:
        # Download the image
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Downloaded: {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to download {url} as {filename}: {e}")
        return False

def load_existing_thumbnails(folder="thumbnails"):
    """
    Load the list of already downloaded thumbnails.
    
    Args:
        folder (str): The folder containing thumbnails
        
    Returns:
        set: Set of filenames that already exist
    """
    existing = set()
    if os.path.exists(folder):
        for file in os.listdir(folder):
            if file.endswith('.png'):
                existing.add(file)
    logger.info(f"Found {len(existing)} existing thumbnails")
    return existing

def main(csv_file, folder, skip_existing=True, delay=0.1):
    """
    Main function to download thumbnails from CSV.
    
    Args:
        csv_file (str): Path to the CSV file
        folder (str): Folder to save thumbnails
        skip_existing (bool): Whether to skip already downloaded thumbnails
        delay (float): Delay between downloads in seconds
    """
    try:
        df = pd.read_csv(csv_file)
        logger.info(f"Loaded {len(df)} rows from {csv_file}")
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return
    
    # Check if the required columns exist
    if 'property_thumbnail' not in df.columns:
        logger.error("Column 'property_thumbnail' not found in CSV")
        return
    
    # Load existing thumbnails
    existing_thumbnails = set()
    if skip_existing:
        existing_thumbnails = load_existing_thumbnails(folder)
    
    # Download all thumbnails
    downloaded_count = 0
    failed_count = 0
    skipped_count = 0
    
    for index, row in df.iterrows():
        thumbnail_url = row['property_thumbnail']
        
        # Skip if URL is empty
        if pd.isna(thumbnail_url) or not thumbnail_url.strip():
            logger.warning(f"Row {index}: Empty thumbnail URL")
            failed_count += 1
            continue
        
        # Extract filename from URL to check if already exists
        parsed_url = urlparse(thumbnail_url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            filename = f"thumbnail_{int(time.time())}.png"
        if not filename.endswith('.png'):
            filename += '.png'
        
        # Skip if already downloaded
        if skip_existing and filename in existing_thumbnails:
            skipped_count += 1
            logger.debug(f"Skipping already downloaded: {filename}")
            continue
        
        # Download the thumbnail
        success = download_thumbnail(thumbnail_url, folder)
        if success:
            downloaded_count += 1
        else:
            failed_count += 1
        
        # Add a small delay to be respectful to the server
        if delay > 0:
            time.sleep(delay)
    
    logger.info(f"\nDownload Summary:")
    logger.info(f"Successfully downloaded: {downloaded_count}")
    logger.info(f"Failed to download: {failed_count}")
    logger.info(f"Skipped (already existed): {skipped_count}")
    logger.info(f"Total processed: {downloaded_count + failed_count + skipped_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download thumbnails from CSV using filename from URL")
    parser.add_argument("--csv", default="results_gee_filtered.csv", help="CSV file path")
    parser.add_argument("--folder", default="thumbnails", help="Folder to save thumbnails")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip already downloaded thumbnails")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between downloads in seconds")
    
    args = parser.parse_args()
    
    main(args.csv, args.folder, not args.no_skip, args.delay)

