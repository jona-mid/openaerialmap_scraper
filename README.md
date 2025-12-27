# OpenAerialMap Scraper Pipeline

Minimal pipeline to scrape, filter, and download OpenAerialMap imagery with forest cover analysis.

## Pipeline Overview

1. **Scrape metadata** from OpenAerialMap API
2. **Filter** by resolution, date, platform, and forest cover (using ESA WorldCover via Google Earth Engine)
3. **Download thumbnails** for manual review
4. **Download TIF files** based on selected thumbnails

## Installation

```bash
pip install -r requirements.txt
```

For Google Earth Engine, authenticate first:
```bash
python -c "import ee; ee.Authenticate()"
```

## Usage

### Step 1: Scrape Metadata

```bash
python scrape.py
```

Output: `openaerial_data.csv`

### Step 2: Filter Images

```bash
python filter_openaerial_images.py
```

Filters by:
- Resolution: < 10 cm GSD
- Date: Uploaded after YYYY-MM-DD
- Platform: UAV or aircraft
- Forest cover: Calculated using ESA WorldCover via Google Earth Engine
  - Default:
    - Before April 2025: 0% < forest ≤ 30%
    - After April 2025: forest > 0%

Output: `results_gee_filtered.csv`

### Step 3: Download Thumbnails

```bash
python download_thumbnails.py
```

Downloads thumbnails from `results_gee_filtered.csv` using the filename from the URL (keeps original name).

**Features:**
- Uses filename from thumbnail URL (preserves original name)
- Skips already downloaded thumbnails automatically
- Resumable - can be stopped and restarted
- Server-friendly with logging and error handling

**Options:**
- `--csv`: CSV file path (default: `results_gee_filtered.csv`)
- `--folder`: Output folder (default: `thumbnails/`)
- `--no-skip`: Re-download existing files
- `--delay`: Delay between downloads in seconds (default: 0.1)

**How it works:**
1. Reads CSV and identifies `property_thumbnail` column
2. Extracts filename from each thumbnail URL
3. Checks target folder for existing thumbnails
4. Downloads only missing thumbnails with original filenames
5. Adds delay between downloads to avoid overwhelming the server
6. Logs all actions to `thumbnail_download.log`

**Output:** Thumbnails saved to `thumbnails/` folder with original filenames, log file `thumbnail_download.log`

### Step 4: Manual Review

Review thumbnails in `thumbnails/` folder and keep only desired images.

**Find and remove exact duplicate thumbnails:**

```bash
python find_duplicate_thumbnails.py
```

Finds exact duplicate thumbnails by comparing file content (MD5 hash).

Options:
- `--thumbnails-dir`: Thumbnails directory (default: `thumbnails/`)
- `--remove`: Remove duplicate files (keeps first one)
- `--output`: Save duplicate list to file

Example:
```bash
# Just find duplicates
python find_duplicate_thumbnails.py

# Find and remove duplicates
python find_duplicate_thumbnails.py --remove

# Save duplicate list to file
python find_duplicate_thumbnails.py --output duplicates.txt
```

### Step 5: Download TIF Files

```bash
python download_tifs.py
```

Matches thumbnail filenames to CSV `uuid` column and downloads TIF files.

Options:
- `--csv`: CSV file path (default: `results_gee_filtered.csv`)
- `--thumbnails-dir`: Thumbnails directory (default: `thumbnails/`)
- `--output-dir`: Output directory for TIFs (default: `tifs/`)
- `--delay`: Delay between downloads in seconds (default: 0.5)

## Server Usage

For long-running downloads, run scripts on a Linux server:

```bash
ssh js1619@10.9.7.15
cd /path/to/project
python download_thumbnails.py
python download_tifs.py --output-dir /path/to/large/storage
```

## File Structure

```
openaerialmap_scraper/
├── scrape.py                    # Step 1: Scrape metadata
├── filter_openaerial_images.py  # Step 2: Filter by criteria
├── download_thumbnails.py       # Step 3: Download thumbnails
├── find_duplicate_thumbnails.py # Step 4: Find duplicate thumbnails
├── download_tifs.py             # Step 5: Download TIF files
├── esa_worldcover.py            # ESA WorldCover utilities
├── requirements.txt             # Dependencies
└── README.md                    # This file
```

## Output Files

- `openaerial_data.csv` - Raw scraped metadata
- `openaerial_data_filtered.csv` - After initial filtering (GSD/date/platform)
- `results_gee_filtered.csv` - Final filtered results with forest percentages
- `thumbnails/*.png` - Thumbnail images (original filename from URL)
- `tifs/*.tif` - Downloaded TIF files

## Requirements

- Python 3.x
- pandas
- requests
- earthengine-api
- tqdm

See `requirements.txt` for exact versions.

