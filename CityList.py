import pandas as pd
import sqlite3
import re
import os

def clean_book_locations(df, publication_col='publication', imprint_col='imprint'):
    """
    Clean book location data by extracting Chinese characters before colons
    from publication and imprint columns.
    
    Args:
        df: DataFrame containing book data
        publication_col: name of publication column
        imprint_col: name of imprint column
    
    Returns:
        DataFrame with added 'location' column
    """
    
    def extract_location(text):
        """Extract Chinese characters before the first colon"""
        if pd.isna(text) or str(text).lower().strip() == 'missing':
            return None
        
        # Convert to string and find the first colon
        text_str = str(text).strip()
        colon_pos = text_str.find('：')  # Chinese colon
        if colon_pos == -1:
            colon_pos = text_str.find(':')  # Regular colon
        
        if colon_pos > 0:
            # Extract everything before the colon
            location = text_str[:colon_pos].strip()
            # Check if location contains Chinese characters
            if re.search(r'[\u4e00-\u9fff]', location):
                return location
        
        return None
    
    # Create a copy of the dataframe
    df_cleaned = df.copy()
    
    # Extract locations from both columns
    publication_locations = df_cleaned[publication_col].apply(extract_location)
    imprint_locations = df_cleaned[imprint_col].apply(extract_location)
    
    # Create location column: use publication first, then imprint if publication is missing
    df_cleaned['location'] = publication_locations.fillna(imprint_locations)
    
    return df_cleaned

def export_unique_locations(df, output_file='../scraped_data/unique_locations.csv'):
    """
    Export unique locations to CSV file
    
    Args:
        df: DataFrame with 'location' column
        output_file: name of output CSV file
    """
    # Get unique locations (excluding None/NaN)
    unique_locations = df['location'].dropna().unique()
    
    # Create DataFrame with unique locations
    unique_df = pd.DataFrame({'location': sorted(unique_locations)})
    
    # Export to CSV
    unique_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"Exported {len(unique_locations)} unique locations to {output_file}")
    return unique_locations

def load_data_from_database(db_path='../scraped_data/ncl_subject_books_details.db'):
    """
    Load book data from the SQLite database created by the scraping program.
    
    Args:
        db_path: Path to the SQLite database file
    
    Returns:
        pandas.DataFrame: DataFrame containing the book data
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        
        # Load the books table into a DataFrame
        df = pd.read_sql_query("SELECT * FROM books", conn)
        
        # Close the connection
        conn.close()
        
        print(f"Loaded {len(df)} books from database: {db_path}")
        print(f"Columns available: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"Error loading data from database: {str(e)}")
        return None

def process_scraped_book_data(db_path='../scraped_data/ncl_subject_books_details.db'):
    """
    Complete processing pipeline for the scraped book location data.
    
    Args:
        db_path: Path to the SQLite database file from the scraper
    """
    try:
        # Load data from the database
        print("Loading data from scraper database...")
        df = load_data_from_database(db_path)
        
        if df is None:
            print("Failed to load data from database. Exiting.")
            return None, None
        
        print(f"Loaded {len(df)} records from scraper database")
        
        # Clean locations using the imprint and publication fields from scraper
        print("Extracting locations...")
        df_cleaned = clean_book_locations(df, 'publication', 'imprint')
        
        # Show statistics
        total_locations = df_cleaned['location'].notna().sum()
        print(f"Successfully extracted {total_locations} locations out of {len(df)} records")
        
        # Create the scraped_data directory if it doesn't exist
        os.makedirs('../scraped_data', exist_ok=True)
        
        # Export unique locations to the scraped_data directory
        unique_locations = export_unique_locations(df_cleaned)
        
        # Save cleaned data to the scraped_data directory
        output_file = '../scraped_data/cleaned_book_data_with_locations.csv'
        df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Saved cleaned data with locations to {output_file}")
        
        # Display sample of results
        print("\nSample of extracted locations:")
        sample_locations = df_cleaned[df_cleaned['location'].notna()]['location'].head(10)
        for i, loc in enumerate(sample_locations, 1):
            print(f"{i}. {loc}")
        
        print(f"\nTotal unique locations found: {len(unique_locations)}")
        print("First 10 unique locations:")
        for i, loc in enumerate(sorted(unique_locations)[:10], 1):
            print(f"{i}. {loc}")
        
        if len(unique_locations) > 10:
            print(f"... and {len(unique_locations) - 10} more unique locations")
        
        return df_cleaned, unique_locations
        
    except Exception as e:
        print(f"Error processing scraped data: {str(e)}")
        return None, None

def process_book_data(input_file, publication_col='publication', imprint_col='imprint'):
    """
    Complete processing pipeline for book location data
    
    Args:
        input_file: path to input CSV file
        publication_col: name of publication column
        imprint_col: name of imprint column
    """
    try:
        # Load data
        print(f"Loading data from {input_file}...")
        df = pd.read_csv(input_file, encoding='utf-8')
        
        print(f"Loaded {len(df)} records")
        print(f"Columns: {list(df.columns)}")
        
        # Clean locations
        print("Extracting locations...")
        df_cleaned = clean_book_locations(df, publication_col, imprint_col)
        
        # Show statistics
        total_locations = df_cleaned['location'].notna().sum()
        print(f"Successfully extracted {total_locations} locations out of {len(df)} records")
        
        # Export unique locations
        unique_locations = export_unique_locations(df_cleaned)
        
        # Save cleaned data
        output_file = '../scraped_data/cleaned_book_data.csv'
        df_cleaned.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Saved cleaned data to {output_file}")
        
        # Display sample of results
        print("\nSample of extracted locations:")
        sample_locations = df_cleaned[df_cleaned['location'].notna()]['location'].head(10)
        for i, loc in enumerate(sample_locations, 1):
            print(f"{i}. {loc}")
        
        print(f"\nUnique locations found: {list(unique_locations)}")
        
        return df_cleaned, unique_locations
        
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return None, None

# Example usage
if __name__ == "__main__":
    print("Book Location Data Cleaner")
    print("=" * 50)
    print("This program extracts publishing locations from the scraped book data.\n")
    
    # Main processing function for scraped data
    print("Processing data from scraper database...")
    df_cleaned, unique_locations = process_scraped_book_data()
    
    if df_cleaned is not None:
        print(f"\nProcessing completed successfully!")
        print(f"- Total books processed: {len(df_cleaned)}")
        print(f"- Books with location data: {df_cleaned['location'].notna().sum()}")
        print(f"- Unique locations found: {len(unique_locations) if unique_locations is not None else 0}")
        print(f"- Output files saved in '../scraped_data/' directory")
    else:
        print("Processing failed. Please check the database path and try again.")
    
    print("\n" + "=" * 50)
    
    # Example with sample data (for testing purposes)
    print("Sample data demonstration:")
    sample_data = {
        'subject': ['會計學', '農業', '建築', '工程', '科技'],
        'title_cleaned': ['Book 1', 'Book 2', 'Book 3', 'Book 4', 'Book 5'],
        'publication': ['上海：上海人民出版社', '北京：中华书局', 'missing', '广州：广东人民出版社', '上海：复旦大学出版社'],
        'imprint': ['missing', 'missing', '北京：商务印书馆', 'missing', 'missing']
    }
    
    df_sample = pd.DataFrame(sample_data)
    
    print("\nOriginal sample data:")
    print(df_sample[['subject', 'title_cleaned', 'publication', 'imprint']])
    
    # Clean the sample data
    df_cleaned_sample = clean_book_locations(df_sample)
    print("\nCleaned sample data:")
    print(df_cleaned_sample[['subject', 'title_cleaned', 'publication', 'imprint', 'location']])
    
    # Show unique locations from sample
    sample_unique = df_cleaned_sample['location'].dropna().unique()
    print(f"\nSample unique locations: {list(sample_unique)}")
    
    # To process a different CSV file (alternative usage), uncomment and modify:
    # process_book_data('path/to/your/file.csv', 'publication', 'imprint')