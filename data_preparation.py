import pandas as pd
import datetime as dt
import os
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_volunteer_data(file_path):
    """Load volunteer data from Excel file"""
    try:
        df = pd.read_excel(file_path)
        logger.info(f"✅ Loaded {len(df)} rows from {file_path}")
        logger.info(f"Columns: {list(df.columns)}")
        return df
    except Exception as e:
        logger.error(f"❌ Error loading file: {e}")
        return None

def clean_volunteer_data(df):
    """🧹 Step 2: Prepare the Data - Remove 0 hours and clean data"""
    logger.info("\n🧹 Step 2: Preparing the Data...")
    
    # Show initial stats
    initial_count = len(df)
    logger.info(f"Initial rows: {initial_count}")
    
    # Find the hours column (case insensitive)
    hours_col = None
    for col in df.columns:
        if 'hour' in col.lower():
            hours_col = col
            break
    
    if hours_col is None:
        logger.error("❌ No 'Hours' column found. Available columns:")
        logger.error(df.columns.tolist())
        return df
    
    logger.info(f"Using Hours column: '{hours_col}'")
    
    # Show hours distribution
    logger.info(f"\nHours distribution:")
    hours_dist = df[hours_col].value_counts().sort_index()
    for hours, count in hours_dist.items():
        logger.info(f"  {hours} hours: {count} records")
    
    # Remove rows where Hours = 0
    df_cleaned = df[df[hours_col] != 0].copy()
    removed_count = initial_count - len(df_cleaned)
    
    logger.info(f"\n📊 Data Cleaning Results:")
    logger.info(f"  • Removed {removed_count} rows with 0 hours")
    logger.info(f"  • Remaining rows: {len(df_cleaned)}")
    logger.info(f"  • Volunteers with 0 hours only registered but did not complete the activity")
    
    return df_cleaned

def save_raw_data(df, output_dir="processed_data"):
    """Save cleaned data as 'Raw Data' file for multiple deduplication/pivot steps"""
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Raw_Data_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)
    
    # Save to Excel
    df.to_excel(filepath, index=False)
    logger.info(f"✅ Saved Raw Data: {filepath}")
    
    return filepath

def deduplicate_data(df, method="activity"):
    """Deduplicate data based on different methods"""
    logger.info(f"\n🔄 Deduplication by {method}...")
    
    initial_count = len(df)
    
    if method == "activity":
        # Remove duplicate activities (same person, same activity, same date)
        # This counts each unique activity completion
        df_dedup = df.drop_duplicates(subset=['volunteerDate', 'assignment'], keep='first')
        logger.info("  • Counting by activity: Each unique activity completion")
        
    elif method == "person":
        # Remove duplicate people (keep first occurrence)
        # This counts unique volunteers
        df_dedup = df.drop_duplicates(subset=['volunteerDate'], keep='first')
        logger.info("  • Counting by person: Each unique volunteer")
        
    elif method == "location":
        # Remove duplicate locations (same person, same location, same date)
        # This counts by branch/location
        location_col = None
        for col in df.columns:
            if 'location' in col.lower() or 'branch' in col.lower():
                location_col = col
                break
        
        if location_col:
            df_dedup = df.drop_duplicates(subset=['volunteerDate', location_col], keep='first')
            logger.info(f"  • Counting by location: Using column '{location_col}'")
        else:
            logger.warning("  • No location/branch column found, using activity method")
            df_dedup = df.drop_duplicates(subset=['volunteerDate', 'assignment'], keep='first')
            
    else:
        logger.error("❌ Invalid deduplication method. Use: 'activity', 'person', or 'location'")
        return df
    
    removed_count = initial_count - len(df_dedup)
    logger.info(f"  • Removed {removed_count} duplicate rows")
    logger.info(f"  • Remaining rows: {len(df_dedup)}")
    
    return df_dedup

def create_summary_report(df, output_dir="processed_data"):
    """Create summary report for monthly review"""
    logger.info("\n📝 Creating Summary Report...")
    
    # Generate summary statistics
    summary = {
        'Total Records': len(df),
        'Date Range': f"{df['volunteerDate'].min()} to {df['volunteerDate'].max()}" if 'volunteerDate' in df.columns else "N/A"
    }
    
    # Add hours summary if available
    hours_col = None
    for col in df.columns:
        if 'hour' in col.lower():
            hours_col = col
            break
    
    if hours_col:
        summary['Total Hours'] = df[hours_col].sum()
        summary['Average Hours per Record'] = round(df[hours_col].mean(), 2)
        summary['Min Hours'] = df[hours_col].min()
        summary['Max Hours'] = df[hours_col].max()
    
    # Count unique assignments if available
    if 'assignment' in df.columns:
        summary['Unique Activities'] = df['assignment'].nunique()
        summary['Most Common Activity'] = df['assignment'].value_counts().index[0] if len(df) > 0 else "N/A"
    
    # Save summary
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = os.path.join(output_dir, f"Summary_Report_{timestamp}.txt")
    
    with open(summary_file, 'w') as f:
        f.write("YMCA Volunteer Data Summary Report\n")
        f.write("=" * 50 + "\n")
        f.write(f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for key, value in summary.items():
            f.write(f"{key}: {value}\n")
        
        f.write("\n📋 Notes for Monthly Review:\n")
        f.write("• Check for reporting errors before pulling data\n")
        f.write("• Verify branch credit calculations\n")
        f.write("• Review manual adjustments for special programs (swim, etc.)\n")
        f.write("• Each data set requires its own deduplication logic\n")
        f.write("• Numbers vary depending on counting method (activity, person, location)\n")
    
    logger.info(f"✅ Summary report saved: {summary_file}")
    return summary_file

def main():
    """Main processing function"""
    logger.info("🏊‍♂️ YMCA Volunteer Data Preparation - Step 2")
    logger.info("=" * 60)
    
    # Find the most recent volunteer history file
    excel_files = list(Path(".").glob("VolunteerHistory_*.xlsx"))
    if not excel_files:
        logger.error("❌ No VolunteerHistory_*.xlsx files found")
        return
    
    # Use the most recent file
    latest_file = max(excel_files, key=os.path.getctime)
    logger.info(f"📁 Using file: {latest_file}")
    
    # Load data
    df = load_volunteer_data(latest_file)
    if df is None:
        return
    
    # Step 2: Clean data (remove 0 hours)
    df_cleaned = clean_volunteer_data(df)
    
    # Save raw data
    raw_data_file = save_raw_data(df_cleaned)
    
    # Create summary report
    summary_file = create_summary_report(df_cleaned)
    
    # Show deduplication options
    logger.info("\n🎯 Deduplication Options Available:")
    logger.info("1. By Activity: df.drop_duplicates(subset=['volunteerDate', 'assignment'])")
    logger.info("2. By Person: df.drop_duplicates(subset=['volunteerDate'])")
    logger.info("3. By Location: df.drop_duplicates(subset=['volunteerDate', 'branch'])")
    
    logger.info("\n📋 Next Steps:")
    logger.info("1. Review the Raw Data file for accuracy")
    logger.info("2. Apply specific deduplication logic as needed")
    logger.info("3. Check monthly for reporting errors")
    logger.info("4. Apply manual adjustments for special programs")
    
    return df_cleaned

if __name__ == "__main__":
    df = main()
