#!/usr/bin/env python3
"""
Library Database Deduplication and CSV Export Tool

This program processes the scraped library database to:
1. Remove duplicate books based on title and author
2. Export all unique books to a CSV file
3. Export books with specific call number prefixes to a separate CSV file
"""

import sqlite3
import pandas as pd
import os
import sys
from pathlib import Path
import re

class LibraryDatabaseProcessor:
    """Class to handle database processing and CSV generation"""
    
    def __init__(self, db_path):
        """
        Initialize the processor with database path
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.df = None
        
    def load_database(self):
        """
        Load the database into a pandas DataFrame
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if database file exists
            if not os.path.exists(self.db_path):
                print(f"Error: Database file '{self.db_path}' does not exist.")
                return False
            
            # Connect to the database and load data
            conn = sqlite3.connect(self.db_path)
            
            # Load all data from the books table
            query = "SELECT * FROM books"
            self.df = pd.read_sql_query(query, conn)
            conn.close()
            
            print(f"Successfully loaded {len(self.df)} records from database")
            return True
            
        except Exception as e:
            print(f"Error loading database: {e}")
            return False
    
    def clean_text_for_comparison(self, text):
        """
        Clean text for better duplicate detection
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text
        """
        if pd.isna(text) or text is None:
            return ""
        
        # Convert to string and strip whitespace
        text = str(text).strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Convert to lowercase for comparison
        text = text.lower()
        
        return text
    
    def remove_duplicates(self):
        """
        Remove duplicate books based on title and author
        
        Returns:
            tuple: (original_count, deduplicated_count, duplicates_removed)
        """
        if self.df is None:
            print("Error: No data loaded. Please load database first.")
            return None, None, None
        
        original_count = len(self.df)
        
        # Create cleaned versions of title and author for comparison
        self.df['title_clean'] = self.df['title'].apply(self.clean_text_for_comparison)
        self.df['author_clean'] = self.df['author'].apply(self.clean_text_for_comparison)
        
        # Find duplicates based on cleaned title and author
        print("Identifying duplicates based on title and author...")
        
        # Keep track of duplicates for reporting
        duplicate_mask = self.df.duplicated(subset=['title_clean', 'author_clean'], keep='first')
        duplicates_count = duplicate_mask.sum()
        
        if duplicates_count > 0:
            print(f"Found {duplicates_count} duplicate records")
            
            # Show some examples of duplicates being removed
            duplicates_df = self.df[duplicate_mask].head(5)
            if not duplicates_df.empty:
                print("\nExamples of duplicates being removed:")
                for idx, row in duplicates_df.iterrows():
                    print(f"  - '{row['title']}' by '{row['author']}'")
        
        # Remove duplicates (keep first occurrence)
        self.df = self.df.drop_duplicates(subset=['title_clean', 'author_clean'], keep='first')
        
        # Drop the temporary cleaning columns
        self.df = self.df.drop(['title_clean', 'author_clean'], axis=1)
        
        # Reset index
        self.df = self.df.reset_index(drop=True)
        
        deduplicated_count = len(self.df)
        duplicates_removed = original_count - deduplicated_count
        
        print(f"Deduplication complete:")
        print(f"  - Original records: {original_count}")
        print(f"  - After deduplication: {deduplicated_count}")
        print(f"  - Duplicates removed: {duplicates_removed}")
        
        return original_count, deduplicated_count, duplicates_removed
    
    def filter_call_numbers(self):
        """
        Filter books with call numbers starting with 4, 5, 線4, or 線5
        
        Returns:
            pd.DataFrame: Filtered DataFrame
        """
        if self.df is None:
            print("Error: No data loaded. Please load database first.")
            return None
        
        # Create a copy for filtering
        filtered_df = self.df.copy()
        
        # Handle null/NaN values in call_number
        filtered_df['call_number'] = filtered_df['call_number'].fillna('')
        
        # Define the patterns to match
        patterns = [
            r'^4',      # Starts with 4
            r'^5',      # Starts with 5
            r'^線\s*4', # Starts with 線4 (with optional space)
            r'^線\s*5', # Starts with 線5 (with optional space)
        ]
        
        # Create a combined pattern
        combined_pattern = '|'.join(patterns)
        
        # Filter the DataFrame
        mask = filtered_df['call_number'].str.match(combined_pattern, na=False)
        filtered_df = filtered_df[mask]
        
        print(f"Filtered {len(filtered_df)} books with call numbers starting with 4, 5, 線4, or 線5")
        
        if len(filtered_df) > 0:
            print("\nExamples of filtered call numbers:")
            sample_call_numbers = filtered_df['call_number'].dropna().head(10).tolist()
            for call_num in sample_call_numbers:
                print(f"  - {call_num}")
        
        return filtered_df
    
    def export_to_csv(self, df, filename, description=""):
        """
        Export DataFrame to CSV file
        
        Args:
            df (pd.DataFrame): DataFrame to export
            filename (str): Output filename
            description (str): Description for logging
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(filename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Export to CSV
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            print(f"Successfully exported {len(df)} records to '{filename}'{description}")
            
            # Show column information
            print(f"  Columns: {', '.join(df.columns.tolist())}")
            
            return True
            
        except Exception as e:
            print(f"Error exporting to CSV '{filename}': {e}")
            return False
    
    def generate_summary_report(self, original_count, deduplicated_count, filtered_count):
        """
        Generate a summary report
        
        Args:
            original_count (int): Original number of records
            deduplicated_count (int): Number after deduplication
            filtered_count (int): Number in filtered dataset
        """
        print("\n" + "="*60)
        print("PROCESSING SUMMARY REPORT")
        print("="*60)
        print(f"Original records in database:     {original_count:,}")
        print(f"After removing duplicates:        {deduplicated_count:,}")
        print(f"Duplicates removed:               {original_count - deduplicated_count:,}")
        print(f"Books with special call numbers:  {filtered_count:,}")
        print(f"Percentage with special calls:    {(filtered_count/deduplicated_count)*100:.1f}%")
        
        # Show subject distribution
        if self.df is not None and 'subject' in self.df.columns:
            print("\nSubject distribution in deduplicated data:")
            subject_counts = self.df['subject'].value_counts().head(10)
            for subject, count in subject_counts.items():
                print(f"  {subject}: {count:,} books")
        
        print("="*60)
    
    def process_database(self, output_dir="../processed_data"):
        """
        Main processing function that handles the entire workflow
        
        Args:
            output_dir (str): Directory to save output files
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("Starting library database processing...")
        print(f"Database: {self.db_path}")
        print(f"Output directory: {output_dir}")
        print("-" * 50)
        
        # Step 1: Load database
        if not self.load_database():
            return False
        
        # Step 2: Remove duplicates
        original_count, deduplicated_count, duplicates_removed = self.remove_duplicates()
        if original_count is None:
            return False
        
        # Step 3: Export all deduplicated books
        all_books_file = os.path.join(output_dir, "all_books_deduplicated.csv")
        if not self.export_to_csv(self.df, all_books_file, " (all deduplicated books)"):
            return False
        
        # Step 4: Filter and export books with specific call numbers
        filtered_df = self.filter_call_numbers()
        if filtered_df is None:
            return False
        
        filtered_books_file = os.path.join(output_dir, "filtered_books_call_numbers.csv")
        if not self.export_to_csv(filtered_df, filtered_books_file, " (call numbers: 4, 5, 線4, 線5)"):
            return False
        
        # Step 5: Generate summary report
        self.generate_summary_report(original_count, deduplicated_count, len(filtered_df))
        
        print(f"\nProcessing completed successfully!")
        print(f"Output files saved to: {os.path.abspath(output_dir)}")
        
        return True

def main():
    """Main function to run the database processor"""
    
    # Configuration
    db_path = "../scraped_data/ncl_subject_books.db"  # Default path from your scraper
    output_dir = "../processed_data"
    
    # Allow command line argument for database path
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    print("Library Database Deduplication and CSV Export Tool")
    print("=" * 55)
    
    # Create processor instance
    processor = LibraryDatabaseProcessor(db_path)
    
    # Process the database
    success = processor.process_database(output_dir)
    
    if success:
        print("\n✅ All operations completed successfully!")
    else:
        print("\n❌ Processing failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()