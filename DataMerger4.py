import sqlite3
import pandas as pd
import os

def load_and_prepare_dataset1(db_path):
    """
    Load and prepare the detailed dataset (PublicationScraper8.py output)
    """
    print(f"Loading dataset 1 from: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM books", conn)
    conn.close()
    
    print(f"Dataset 1 loaded: {len(df)} records")
    
    # Use the cleaned title and author fields for matching
    # Handle missing values by converting to empty strings
    df['title_cleaned'] = df['title_cleaned'].fillna('')
    df['author_cleaned'] = df['author_cleaned'].fillna('')
    
    return df

def load_and_prepare_dataset2(db_path):
    """
    Load and prepare the summary dataset (TaiwanNCLScraper9.py output)
    """
    print(f"Loading dataset 2 from: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM books", conn)
    conn.close()
    
    print(f"Dataset 2 loaded: {len(df)} records")
    
    # Handle missing values by converting to empty strings
    df['title'] = df['title'].fillna('')
    df['author'] = df['author'].fillna('')
    
    return df

def merge_datasets(df1, df2):
    """
    Merge the two datasets using exact matching on title and author
    """
    print("\nMerging datasets...")
    
    # Perform exact matching on title_cleaned (df1) with title (df2)
    # and author_cleaned (df1) with author (df2)
    merged_df = pd.merge(df1, df2, 
                        left_on=['title_cleaned', 'author_cleaned'], 
                        right_on=['title', 'author'], 
                        how='inner', 
                        suffixes=('_detailed', '_summary'))
    
    print(f"Exact matches found: {len(merged_df)}")
    
    # Find unmatched records
    # For df1 (detailed), find records that didn't match
    merged_keys_df1 = merged_df[['title_cleaned', 'author_cleaned']].drop_duplicates()
    unmatched_df1 = df1[~df1[['title_cleaned', 'author_cleaned']].apply(tuple, axis=1).isin(
        merged_keys_df1.apply(tuple, axis=1))]
    
    # For df2 (summary), find records that didn't match
    # Note: After merge, the original 'title' and 'author' columns from df2 
    # are renamed to 'title_summary' and 'author_summary'
    merged_keys_df2 = merged_df[['title_summary', 'author_summary']].drop_duplicates()
    unmatched_df2 = df2[~df2[['title', 'author']].apply(tuple, axis=1).isin(
        merged_keys_df2.apply(tuple, axis=1))]
    
    print(f"Unmatched records - Dataset 1: {len(unmatched_df1)}, Dataset 2: {len(unmatched_df2)}")
    
    # Add match information
    merged_df['match_type'] = 'exact'
    merged_df['similarity_score'] = 1.0
    
    return merged_df, unmatched_df1, unmatched_df2

def save_results(merged_df, unmatched_df1, unmatched_df2, output_path):
    """
    Save the merged results and unmatched records to SQLite database
    """
    print(f"\nSaving results to: {output_path}")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    conn = sqlite3.connect(output_path)
    
    # Save merged data
    merged_df.to_sql('merged_books', conn, if_exists='replace', index=False)
    print(f"Saved {len(merged_df)} merged records")
    
    # Save unmatched records from dataset 1
    unmatched_df1.to_sql('unmatched_detailed', conn, if_exists='replace', index=False)
    print(f"Saved {len(unmatched_df1)} unmatched detailed records")
    
    # Save unmatched records from dataset 2
    unmatched_df2.to_sql('unmatched_summary', conn, if_exists='replace', index=False)
    print(f"Saved {len(unmatched_df2)} unmatched summary records")
    
    conn.close()

def print_merge_summary(merged_df, unmatched_df1, unmatched_df2):
    """
    Print a summary of the merge results
    """
    print("\n" + "="*60)
    print("MERGE SUMMARY")
    print("="*60)
    
    total_records_df1 = len(merged_df) + len(unmatched_df1)
    total_records_df2 = len(merged_df) + len(unmatched_df2)
    
    print(f"Dataset 1 (Detailed): {total_records_df1} records")
    print(f"Dataset 2 (Summary): {total_records_df2} records")
    print(f"Successfully merged: {len(merged_df)} records")
    print(f"Unmatched from Dataset 1: {len(unmatched_df1)} records")
    print(f"Unmatched from Dataset 2: {len(unmatched_df2)} records")
    
    if len(merged_df) > 0:
        merge_rate_df1 = (len(merged_df) / total_records_df1) * 100
        merge_rate_df2 = (len(merged_df) / total_records_df2) * 100
        
        print(f"\nMerge rates:")
        print(f"  Dataset 1: {merge_rate_df1:.1f}%")
        print(f"  Dataset 2: {merge_rate_df2:.1f}%")
        
        # Show sample of merged data
        print(f"\nSample merged records:")
        sample_cols = ['title_cleaned', 'author_cleaned', 'title_summary', 'author_summary', 'match_type']
        available_cols = [col for col in sample_cols if col in merged_df.columns]
        print(merged_df[available_cols].head())

def main():
    """
    Main function to orchestrate the dataset merging process
    """
    # Database paths
    db1_path = "../scraped_data/ncl_subject_books_details.db"
    db2_path = "../scraped_data/ncl_subject_books.db"
    output_path = "../scraped_data/merged_ncl_books.db"
    
    print("NCL Book Dataset Merger - Exact Matching Only")
    print("="*60)
    
    # Load and prepare datasets
    df1 = load_and_prepare_dataset1(db1_path)
    df2 = load_and_prepare_dataset2(db2_path)
    
    if df1.empty or df2.empty:
        print("One or both datasets are empty. Please check the database paths.")
        return
    
    # Merge datasets
    merged_df, unmatched_df1, unmatched_df2 = merge_datasets(df1, df2)
    
    # Save results
    save_results(merged_df, unmatched_df1, unmatched_df2, output_path)
    
    # Print summary
    print_merge_summary(merged_df, unmatched_df1, unmatched_df2)
    
    print(f"\nMerge complete! Results saved to: {output_path}")
    print("\nDatabase contains three tables:")
    print("  - merged_books: Successfully merged records")
    print("  - unmatched_detailed: Unmatched records from detailed dataset")
    print("  - unmatched_summary: Unmatched records from summary dataset")

if __name__ == "__main__":
    main()