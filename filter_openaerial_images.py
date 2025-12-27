import pandas as pd
from esa_worldcover import parse_bbox_string, calculate_forest_percentage, init_earthengine

def filter_openaerial_data(df, max_gsd_cm=10, uploaded_after_date='2000-01-01', platform_type='uav'):
    """
    Filters the OpenAerialMap DataFrame based on specified criteria.

    Args:
        df (pd.DataFrame): The DataFrame containing OpenAerialMap metadata.
        max_gsd_cm (float): Maximum allowed Ground Sample Distance (GSD) in centimeters.
                            Images with GSD smaller than this value are kept.
        uploaded_after_date (str): Filters for images uploaded to OpenAerialMap after this date (format 'YYYY-MM-DD').
        platform_type (str or list): Platform type(s) to filter (e.g., 'uav' or ['uav', 'aircraft']). Case-insensitive.

    Returns:
        pd.DataFrame: The filtered DataFrame.
    """
    initial_records = len(df)
    print(f"\nStarting filtering with {initial_records} records.")
    filtered_df = df.copy()

    # 1. Filter by resolution (< max_gsd_cm)
    if 'gsd' in filtered_df.columns:
        # Convert to numeric, coercing errors to NaN
        filtered_df['gsd_numeric'] = pd.to_numeric(filtered_df['gsd'], errors='coerce')
        original_count = len(filtered_df)
        filtered_df = filtered_df[
            (filtered_df['gsd_numeric'].notna()) &
            (filtered_df['gsd_numeric'] < max_gsd_cm / 100.0)
        ]
        print(f"  - After GSD filter (< {max_gsd_cm}cm): {len(filtered_df)} records ({(original_count - len(filtered_df))} removed).")
        filtered_df = filtered_df.drop(columns=['gsd_numeric']) # Clean up temporary column
    else:
        print("  - Warning: 'gsd' column not found for resolution filtering. Skipping.")

    # 2. Filter by uploaded_at date (> uploaded_after_date)
    # Assuming 'uploaded_at' exists as a string timestamp.
    if 'uploaded_at' in filtered_df.columns:
        original_count = len(filtered_df)
        # Convert 'uploaded_at' to datetime and compare
        target_date = pd.to_datetime(uploaded_after_date, utc=True) # Add utc=True here
        filtered_df['uploaded_datetime'] = pd.to_datetime(filtered_df['uploaded_at'], errors='coerce')
        filtered_df = filtered_df[
            (filtered_df['uploaded_datetime'].notna()) &
            (filtered_df['uploaded_datetime'] > target_date)
        ]
        print(f"  - After uploaded date filter (> {uploaded_after_date}): {len(filtered_df)} records ({(original_count - len(filtered_df))} removed).")
        filtered_df = filtered_df.drop(columns=['uploaded_datetime']) # Drop the temporary column
    else:
        print("  - Warning: 'uploaded_at' column not found for uploaded date filtering. Skipping.")

    # 3. Filter by platform (e.g., 'uav' or ['uav', 'aircraft'])
    # Assuming 'platform' column exists. Perform case-insensitive comparison.
    if 'platform' in filtered_df.columns:
        original_count = len(filtered_df)
        # Handle both string and list inputs
        if isinstance(platform_type, str):
            platform_types = [platform_type.lower()]
        else:
            platform_types = [p.lower() if isinstance(p, str) else str(p).lower() for p in platform_type]
        
        filtered_df = filtered_df[
            (filtered_df['platform'].notna()) &
            (filtered_df['platform'].str.lower().isin(platform_types))
        ]
        platform_str = platform_type if isinstance(platform_type, str) else ', '.join(platform_type)
        print(f"  - After platform filter ('{platform_str}'): {len(filtered_df)} records ({(original_count - len(filtered_df))} removed).")
    else:
        print("  - Warning: 'platform' column not found for platform filtering. Skipping.")

    print(f"\nFiltering complete. {len(filtered_df)} records remaining out of {initial_records} initial records.")
    return filtered_df

def main():
    # Define input and output file names
    input_csv_file = "openaerial_data.csv"
    output_csv_file = "openaerial_data_filtered.csv"

    print(f"Loading data from {input_csv_file}...")
    try:
        df = pd.read_csv(input_csv_file)
        print(f"Successfully loaded {len(df)} records.")
    except FileNotFoundError:
        print(f"Error: {input_csv_file} not found. Please run scrape.py first to generate the data.")
        return
    except Exception as e:
        print(f"Error loading data from {input_csv_file}: {e}")
        return

    # Print dataset info BEFORE filtering
    print("\nDataset Summary (before filtering):")
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    if 'platform' in df.columns:
        print("\nPlatform distribution (before filtering):")
        print(df['platform'].value_counts())

    # Apply filters for relevant images
    filtered_df = filter_openaerial_data(
        df,
        max_gsd_cm=10,                      # Resolution < 10 cm
        uploaded_after_date='2024-04-01',   # Added to openaerialmap.org after April 2024
        platform_type=['uav', 'aircraft']  # Platform is 'uav' or 'aircraft' (case-insensitive)
    )

    # Print dataset info AFTER filtering
    print("\nDataset Summary (after filtering):")
    print(f"Total rows: {len(filtered_df)}")
    print(f"Total columns: {len(filtered_df.columns)}")
    print("\nPlatform distribution (after filtering):")
    if 'platform' in filtered_df.columns:
        print(filtered_df['platform'].value_counts())

    # Save filtered data
    print(f"\nSaving filtered dataset to {output_csv_file}...")
    filtered_df.to_csv(output_csv_file, index=False)
    print(f"Saved filtered CSV version to {output_csv_file}")

    # Initialize Earth Engine (non-interactive). If not initialized, skip percentage calculation.
    ee_ready = init_earthengine(authenticate_if_needed=False)
    if not ee_ready:
        print("Earth Engine not initialized. Call init_earthengine(authenticate_if_needed=True) or run ee.Authenticate() interactively.")
        filtered_df['forest_percentage_gee'] = None
    else:
        # Apply the function to each row of the FILTERED DataFrame to get the forest percentage
        print("\nCalculating forest percentages for filtered records...")
        from tqdm import tqdm
        tqdm.pandas(desc="Calculating forest percentages")
        filtered_df['forest_percentage_gee'] = filtered_df['bbox'].progress_apply(lambda x: calculate_forest_percentage(parse_bbox_string(x)))
        
        # Debug: show statistics
        non_null_count = filtered_df['forest_percentage_gee'].notna().sum()
        print(f"Calculated forest percentages: {non_null_count} non-null values out of {len(filtered_df)}")
        if non_null_count > 0:
            print(f"Forest percentage range: {filtered_df['forest_percentage_gee'].min():.2f}% - {filtered_df['forest_percentage_gee'].max():.2f}%")
            print(f"Mean forest percentage: {filtered_df['forest_percentage_gee'].mean():.2f}%")

    # Convert uploaded_at to datetime if it exists
    if 'uploaded_at' in filtered_df.columns:
        filtered_df['uploaded_at'] = pd.to_datetime(filtered_df['uploaded_at'], utc=True)

    # Apply date-based forest filtering (from earth_engine.py)
    april_2025 = pd.Timestamp('2025-04-01', tz='UTC')
    
    # Filter based on upload_date and forest_percentage_gee
    if 'uploaded_at' in filtered_df.columns and 'forest_percentage_gee' in filtered_df.columns:
        original_count = len(filtered_df)
        # Handle None values - only filter where forest_percentage_gee is not None
        mask = filtered_df['forest_percentage_gee'].notna()
        filtered_mask = mask & (
            (
                # Before April 2025: forest_percentage_gee between > 0 and <= 30%
                ((filtered_df['uploaded_at'] < april_2025) & (filtered_df['forest_percentage_gee'] > 0) & (filtered_df['forest_percentage_gee'] <= 30)) |
                # After April 2025: forest_percentage_gee > 0%
                ((filtered_df['uploaded_at'] >= april_2025) & (filtered_df['forest_percentage_gee'] > 0))
            )
        )
        filtered_df = filtered_df[filtered_mask].copy()
        print(f"\nAfter forest-based filtering: {len(filtered_df)} records ({(original_count - len(filtered_df))} removed).")

    # Save final filtered results
    final_output_file = "results_gee_filtered.csv"
    filtered_df.to_csv(final_output_file, index=False)
    print(f"Processing complete. Final results saved to {final_output_file}.")

if __name__ == "__main__":
    main()