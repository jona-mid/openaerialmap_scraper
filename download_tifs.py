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

def extract_author(row):
    """
    Extract author name from CSV row.
    Priority: contact (name part only) -> provider -> "openaerialmap.org"
    """
    # Try contact first (extract name part before comma)
    if 'contact' in row and pd.notna(row['contact']) and str(row['contact']).strip():
        contact_str = str(row['contact']).strip()
        if ',' in contact_str:
            # Extract name part (before comma)
            name_part = contact_str.split(',')[0].strip()
            if name_part:
                return name_part
        else:
            # No comma, use whole string
            return contact_str
    
    # Fallback to provider
    if 'provider' in row and pd.notna(row['provider']) and str(row['provider']).strip():
        return str(row['provider']).strip()
    
    # Default fallback
    return "openaerialmap.org"

def is_long_campaign(row):
    """
    Check if acquisition duration is longer than 7 days.
    Returns True if duration > 7 days, False otherwise.
    """
    try:
        if 'acquisition_start' not in row or 'acquisition_end' not in row:
            return False
        
        start_str = row['acquisition_start']
        end_str = row['acquisition_end']
        
        if pd.isna(start_str) or pd.isna(end_str):
            return False
        
        start_date = pd.to_datetime(start_str, errors='coerce')
        end_date = pd.to_datetime(end_str, errors='coerce')
        
        if pd.isna(start_date) or pd.isna(end_date):
            return False
        
        duration = end_date - start_date
        
        # Check if duration > 7 days
        return duration > pd.Timedelta(days=7)
    except Exception as e:
        logger.warning(f"Error calculating long campaign flag: {e}")
        return False

def main(csv_file, thumbnails_dir, output_dir, delay=0.5, metadata_output=None):
    """
    Main function to download TIF files based on thumbnail filenames.
    
    Args:
        csv_file: Path to CSV file with uuid column
        thumbnails_dir: Directory containing thumbnail PNG files
        output_dir: Directory to save TIF files
        delay: Delay between downloads in seconds
        metadata_output: Path to output metadata CSV file (default: {output_dir}/tif_metadata.csv)
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
    
    # Set default metadata output path
    if metadata_output is None:
        metadata_output = os.path.join(output_dir, "tif_metadata.csv")
    
    # Load existing metadata CSV if it exists
    existing_metadata = {}
    existing_filenames = set()
    if os.path.exists(metadata_output):
        try:
            existing_df = pd.read_csv(metadata_output)
            if 'filename' in existing_df.columns:
                for _, existing_row in existing_df.iterrows():
                    filename = existing_row['filename']
                    existing_metadata[filename] = existing_row.to_dict()
                    existing_filenames.add(filename)
                logger.info(f"Loaded {len(existing_filenames)} existing metadata entries from {metadata_output}")
        except Exception as e:
            logger.warning(f"Could not load existing metadata CSV: {e}")
    
    # Initialize metadata list for all TIF files in directory
    metadata_list = []
    
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
        
        # Helper function to create metadata entry
        def create_metadata_entry(row, filename):
            """Create metadata entry from CSV row and filename."""
            authors = extract_author(row)
            
            # Extract and format capture_date as YYYY-MM-DD only
            capture_date = ''
            if 'acquisition_start' in row and pd.notna(row.get('acquisition_start')):
                try:
                    date_obj = pd.to_datetime(row['acquisition_start'], errors='coerce')
                    if pd.notna(date_obj):
                        capture_date = date_obj.strftime('%Y-%m-%d')
                except Exception:
                    capture_date = ''
            
            platform = row.get('platform', '') if pd.notna(row.get('platform')) else ''
            long_campaign = is_long_campaign(row)
            
            metadata_entry = {
                'filename': filename,
                'authors': authors,
                'capture_date': capture_date,
                'platform': platform,
                'is_long_campaign': long_campaign
            }
            
            # Add all original CSV columns
            for col in df.columns:
                if col not in metadata_entry:  # Don't overwrite our custom fields
                    value = row.get(col, '')
                    # Handle NaN values
                    if pd.isna(value):
                        metadata_entry[col] = ''
                    else:
                        metadata_entry[col] = value
            
            return metadata_entry
        
        # Check if file already exists
        file_exists = os.path.exists(output_path)
        
        if file_exists:
            logger.info(f"File already exists, skipping download: {tif_filename}")
            skipped_count += 1
            
            # Add metadata if not already in existing metadata
            if tif_filename not in existing_filenames:
                metadata_entry = create_metadata_entry(row, tif_filename)
                metadata_list.append(metadata_entry)
        else:
            # Download TIF
            logger.info(f"Downloading {tif_filename}...")
            if download_tif(tif_url, output_path):
                downloaded_count += 1
                
                # Add metadata for newly downloaded file
                metadata_entry = create_metadata_entry(row, tif_filename)
                metadata_list.append(metadata_entry)
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
    
    # Merge existing and new metadata
    try:
        # Add all existing metadata entries
        for filename, existing_entry in existing_metadata.items():
            metadata_list.append(existing_entry)
        
        if metadata_list:
            # Create DataFrame and remove duplicates (keep last occurrence, which would be newly added/updated)
            metadata_df = pd.DataFrame(metadata_list)
            # Remove duplicates based on filename, keeping the last occurrence
            metadata_df = metadata_df.drop_duplicates(subset='filename', keep='last')
            # Sort by filename for consistency
            metadata_df = metadata_df.sort_values('filename').reset_index(drop=True)
            
            metadata_df.to_csv(metadata_output, index=False)
            logger.info(f"\nMetadata CSV saved: {metadata_output}")
            logger.info(f"Total metadata entries: {len(metadata_df)}")
            if len(metadata_list) > len(existing_filenames):
                new_entries = len(metadata_list) - len(existing_filenames)
                logger.info(f"Added {new_entries} new metadata entries")
        else:
            logger.info("\nNo metadata to save")
    except Exception as e:
        logger.error(f"Failed to save metadata CSV: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download TIF files based on thumbnail filenames")
    parser.add_argument("--csv", default="results_gee_filtered.csv", help="CSV file path")
    parser.add_argument("--thumbnails-dir", default="thumbnails", help="Directory containing thumbnails")
    parser.add_argument("--output-dir", default="tifs", help="Output directory for TIF files")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between downloads in seconds")
    parser.add_argument("--metadata-output", default=None, help="Output path for metadata CSV (default: {output_dir}/tif_metadata.csv)")
    
    args = parser.parse_args()
    
    main(args.csv, args.thumbnails_dir, args.output_dir, args.delay, args.metadata_output)

