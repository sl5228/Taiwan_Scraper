import sqlite3
import pandas as pd
import re
import unicodedata
from difflib import SequenceMatcher
import os

def normalize_text(text):
    """
    Normalize text for better matching by:
    - Converting to lowercase
    - Removing extra whitespace
    - Normalizing unicode characters
    - Removing common punctuation
    """
    if pd.isna(text) or text == "missing":
        return ""
    
    # Convert to string and normalize unicode
    text = str(text)
    text = unicodedata.normalize('NFKC', text)
    
    # Remove extra whitespace and convert to lowercase
    text = ' '.join(text.split()).lower()
    
    # Remove common punctuation that might vary between sources
    text = re.sub(r'[.,;:!?\[\]()"""''、。，；：！？【】（）]', '', text)
    
    return text.strip()

def extract_year_from_text(text):
    """
    Extract a 4-digit year from various text formats
    """
    if pd.isna(text) or text == "missing":
        return None
    
    # Look for 4-digit years
    year_match = re.search(r'(\d{4})', str(text))
    if year_match:
        year = int(year_match.group(1))
        # Basic sanity check for reasonable publication years
        if 1800 <= year <= 2030:
            return year
    
    return None

def extract_author_from_text(text):
    """
    Extract author name, handling common patterns in library catalogs
    """
    if pd.isna(text) or text == "missing":
        return ""
    
    text = str(text)
    
    # Remove common suffixes like "著", "编", "主编" etc.
    text = re.sub(r'[著編主编撰写作者]$', '', text)
    
    # Take the first author if multiple authors are listed
    if ',' in text:
        text = text.split(',')[0]
    if '；' in text:
        text = text.split('；')[0]
    if ';' in text:
        text = text.split(';')[0]
    
    return text.strip()

def create_composite_key(title, author, year):
    """
    Create a composite key from title, author, and year
    """
    norm_title = normalize_text(title)
    norm_author = normalize_text(extract_author_from_text(author))
    
    # Handle missing year
    year_str = str(year) if year and not pd.isna(year) else "unknown"
    
    return f"{norm_title}|{norm_author}|{year_str}"

def similarity_score(str1, str2):
    """
    Calculate similarity score between two strings
    """
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1, str2).ratio()

def load_and_prepare_dataset1(db_path):
    """
    Load and prepare the detailed dataset (PublicationScraper output)
    """
    print(f"Loading dataset 1 from: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM books", conn)
    conn.close()
    
    print(f"Dataset 1 loaded: {len(df)} records")
    
    # Extract year from imprint or publication fields
    df['extracted_year'] = df['imprint'].apply(extract_year_from_text)
    df.loc[df['extracted_year'].isna(), 'extracted_year'] = df.loc[df['extracted_year'].isna(), 'publication'].apply(extract_year_from_text)
    
    # Use the cleaned title and author fields for matching
    # Create composite key using cleaned fields
    df['composite_key'] = df.apply(lambda row: create_composite_key(
        row.get('title_cleaned', row['title']),  # Use cleaned title if available, fallback to title
        row.get('author_cleaned', ""),  # Use cleaned author if available
        row['extracted_year']
    ), axis=1)
    
    # Create a simplified key for fuzzy matching (title + year only)
    df['simple_key'] = df.apply(lambda row: f"{normalize_text(row.get('title_cleaned', row['title']))}|{row['extracted_year'] if row['extracted_year'] else 'unknown'}", axis=1)
    
    return df

def load_and_prepare_dataset2(db_path):
    """
    Load and prepare the summary dataset (TaiwanNCLScraper output)
    """
    print(f"Loading dataset 2 from: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM books", conn)
    conn.close()
    
    print(f"Dataset 2 loaded: {len(df)} records")
    
    # Convert year to integer
    df['year_int'] = df['year'].apply(lambda x: int(x) if str(x).isdigit() else None)
    
    # Create composite key using title and author fields
    df['composite_key'] = df.apply(lambda row: create_composite_key(
        row['title'], 
        row['author'], 
        row['year_int']
    ), axis=1)
    
    # Create a simplified key for fuzzy matching
    df['simple_key'] = df.apply(lambda row: f"{normalize_text(row['title'])}|{row['year_int'] if row['year_int'] else 'unknown'}", axis=1)
    
    return df

def merge_datasets(df1, df2):
    """
    Merge the two datasets using composite keys with fallback to fuzzy matching
    Focus on matching cleaned_title + cleaned_author (df1) with title + author (df2)
    """
    print("\nMerging datasets...")
    
    # First, try exact composite key matching
    exact_matches = pd.merge(df1, df2, on='composite_key', how='inner', suffixes=('_detailed', '_summary'))
    print(f"Exact matches found: {len(exact_matches)}")
    
    # For unmatched records, try fuzzy matching
    unmatched_df1 = df1[~df1['composite_key'].isin(exact_matches['composite_key'])]
    unmatched_df2 = df2[~df2['composite_key'].isin(exact_matches['composite_key'])]
    
    print(f"Unmatched records - Dataset 1: {len(unmatched_df1)}, Dataset 2: {len(unmatched_df2)}")
    
    # Fuzzy matching focusing on cleaned title and author
    fuzzy_matches = []
    title_similarity_threshold = 0.85
    author_similarity_threshold = 0.80
    
    for idx1, row1 in unmatched_df1.iterrows():
        best_match = None
        best_score = 0
        
        # Get cleaned fields from dataset 1
        cleaned_title1 = row1.get('title_cleaned', row1['title'])
        cleaned_author1 = row1.get('author_cleaned', "")
        year1 = row1['extracted_year']
        
        for idx2, row2 in unmatched_df2.iterrows():
            # Get title and author from dataset 2
            title2 = row2['title']
            author2 = row2['author']
            year2 = row2['year_int']
            
            # Check if years match (if both available)
            if (year1 and year2 and year1 != year2):
                continue
            
            # Calculate title similarity between cleaned_title (df1) and title (df2)
            title_sim = similarity_score(normalize_text(cleaned_title1), normalize_text(title2))
            
            # Calculate author similarity between cleaned_author (df1) and author (df2)
            author_sim = similarity_score(normalize_text(cleaned_author1), normalize_text(author2))
            
            # Combined score - weight title more heavily
            combined_score = (title_sim * 0.7) + (author_sim * 0.3)
            
            # Check if both title and author meet minimum thresholds
            if (title_sim >= title_similarity_threshold and 
                author_sim >= author_similarity_threshold and 
                combined_score > best_score):
                best_score = combined_score
                best_match = row2
                best_match['title_similarity'] = title_sim
                best_match['author_similarity'] = author_sim
        
        if best_match is not None:
            # Create merged record
            merged_record = {
                # From dataset 1 (detailed)
                'subject_detailed': row1['subject'],
                'url_detailed': row1['url'],
                'record_number': row1['record_number'],
                'title_detailed': row1['title'],
                'title_cleaned': row1.get('title_cleaned', row1['title']),
                'author_cleaned': row1.get('author_cleaned', ""),
                'language': row1['language'],
                'imprint': row1['imprint'],
                'publication': row1['publication'],
                'extracted_year': row1['extracted_year'],
                'composite_key': row1['composite_key'],
                'simple_key': row1['simple_key'],
                # From dataset 2 (summary)
                'title_summary': best_match['title'],
                'url_summary': best_match['url'],
                'author': best_match['author'],
                'publisher': best_match['publisher'],
                'year': best_match['year'],
                'call_number': best_match['call_number'],
                'subject_summary': best_match['subject'],
                'year_int': best_match['year_int'],
                # Matching info
                'match_type': 'fuzzy',
                'similarity_score': best_score,
                'title_similarity': best_match['title_similarity'],
                'author_similarity': best_match['author_similarity']
            }
            fuzzy_matches.append(merged_record)
    
    print(f"Fuzzy matches found: {len(fuzzy_matches)}")
    
    # Add match type to exact matches
    exact_matches['match_type'] = 'exact'
    exact_matches['similarity_score'] = 1.0
    exact_matches['title_similarity'] = 1.0
    exact_matches['author_similarity'] = 1.0
    
    # Combine all matches
    if fuzzy_matches:
        fuzzy_df = pd.DataFrame(fuzzy_matches)
        merged_df = pd.concat([exact_matches, fuzzy_df], ignore_index=True)
    else:
        merged_df = exact_matches
    
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
        exact_matches = len(merged_df[merged_df['match_type'] == 'exact'])
        fuzzy_matches = len(merged_df[merged_df['match_type'] == 'fuzzy'])
        
        print(f"\nMatch breakdown:")
        print(f"  Exact matches: {exact_matches}")
        print(f"  Fuzzy matches: {fuzzy_matches}")
        
        merge_rate_df1 = (len(merged_df) / total_records_df1) * 100
        merge_rate_df2 = (len(merged_df) / total_records_df2) * 100
        
        print(f"\nMerge rates:")
        print(f"  Dataset 1: {merge_rate_df1:.1f}%")
        print(f"  Dataset 2: {merge_rate_df2:.1f}%")
        
        # Show fuzzy match statistics
        if fuzzy_matches > 0:
            fuzzy_df = merged_df[merged_df['match_type'] == 'fuzzy']
            avg_title_sim = fuzzy_df['title_similarity'].mean()
            avg_author_sim = fuzzy_df['author_similarity'].mean()
            avg_combined_sim = fuzzy_df['similarity_score'].mean()
            
            print(f"\nFuzzy match quality:")
            print(f"  Average title similarity: {avg_title_sim:.3f}")
            print(f"  Average author similarity: {avg_author_sim:.3f}")
            print(f"  Average combined similarity: {avg_combined_sim:.3f}")
        
        # Show sample of merged data
        print(f"\nSample merged records:")
        sample_cols = ['title_cleaned', 'author_cleaned', 'title_summary', 'author', 'extracted_year', 'match_type']
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
    
    print("NCL Book Dataset Merger")
    print("="*50)
    print("Matching cleaned_title + cleaned_author (Dataset 1) with title + author (Dataset 2)")
    print("="*50)
    
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