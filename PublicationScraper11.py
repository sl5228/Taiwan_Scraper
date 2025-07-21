#%%  Import packages
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import re
from random import randint
import pandas as pd
import sqlite3
import os

def save_book_to_database(book_info, db_path):
    """
    Function to save a single book's information to the database.
    
    Args:
        book_info: Dictionary containing book information
        db_path: Path to the SQLite database file
    
    Returns:
        bool: True if successfully saved, False otherwise
    """
    try:
        # Convert the dictionary to a DataFrame
        book_df = pd.DataFrame([book_info])  # Note: single book in a list
        
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        
        # Save the DataFrame to the database, appending if the table exists
        book_df.to_sql('books', conn, if_exists='append', index=False)
        
        # Close the connection
        conn.close()
        
        print(f"Successfully saved book '{book_info.get('title_cleaned', 'Unknown')}' to database")
        return True
        
    except Exception as e:
        print(f"Error saving book to database: {str(e)}")
        return False

def navigate_to_advanced_search(driver):
    """
    Function to navigate from the main NCL website to the advanced search page.
    
    Args:
        driver: The Selenium WebDriver instance
    
    Returns:
        None
    """
    try:
        # Open the main NCL website
        driver.get("https://aleweb.ncl.edu.tw/F?func=file&file_name=find-b&CON_LNG=ENG")
        # print("Opened the Full Catalog page")
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 30)
        
        # Find and click on the "Advanced Search" link
        advanced_search_link = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a.mainmenu02[title='Advanced Search']")
        ))
        advanced_search_link.click()
        # print("Clicked on Advanced Search link")
        
    except Exception as e:
        print(f"Error navigating to advanced search page: {str(e)}")
        raise


def refine_search(driver, subject_term, language="CHI", start_year="1950", end_year="2023"):
    """
    Function to refine the search on the advanced search page.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_term: The subject term to search for
        language: The language to filter by (default: "CHI" for Chinese)
        start_year: The starting year for publication date filter (default: "1950")
        end_year: The ending year for publication date filter (default: "2023")
    
    Returns:
        bool: True if search results were found, False otherwise
    """
    try:
        wait = WebDriverWait(driver, 30)
        
        # Now on the advanced search page, select the Subject option from dropdown
        subject_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "find_code")))
        subject_select = Select(subject_dropdown)
        subject_select.select_by_value("WSU")
        # print("Selected Subject option from dropdown")
        
        # Enter the subject term in the search input
        search_input = wait.until(EC.presence_of_element_located((By.NAME, "request")))
        search_input.clear()  # Clear the field first
        search_input.send_keys(subject_term)
        # print(f"Entered subject term: {subject_term}")
        
        # Improved radio button selection with retry mechanism
        try:
            # First approach - try to find and click using CSS selector
            adjacent_radio = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[name='adjacent1'][value='N']")
            ))
            adjacent_radio.click()
            # Add a small pause after clicking
            time.sleep(1)
            
            # Verify if it was selected
            if not adjacent_radio.is_selected():
                # If not selected, try JavaScript approach
                driver.execute_script("arguments[0].click();", adjacent_radio)
                time.sleep(1)
                # print("Selected 'N' radio button using JavaScript")
            else:
                # print("Selected 'N' radio button")
                pass
                
        except Exception as radio_error:
            print(f"Error with first radio button approach: {str(radio_error)}")
            # Try alternate approach by finding parent element first
            try:
                adjacent_radio = driver.find_element(
                    By.XPATH, "//input[@type='radio' and @name='adjacent1' and @value='N']"
                )
                driver.execute_script("arguments[0].click();", adjacent_radio)
                # print("Selected 'N' radio button using XPath and JavaScript")
            except Exception as alt_radio_error:
                print(f"Error with alternate radio button approach: {str(alt_radio_error)}")
                raise
        
        # Select Chinese from the language dropdown
        language_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_1")))
        language_select = Select(language_dropdown)
        language_select.select_by_value(language)
        # print(f"Selected language: {language}")
        
        # Enter the start year in the textbox - clear first
        start_year_input = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_2")))
        start_year_input.clear()  # Clear the field first
        start_year_input.send_keys(start_year)
        # print(f"Entered start year: {start_year}")
        
        # Enter the end year in the textbox - clear first
        end_year_input = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_3")))
        end_year_input.clear()  # Clear the field first
        end_year_input.send_keys(end_year)
        # print(f"Entered end year: {end_year}")
        
        # Select Book from the material type dropdown
        material_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_4")))
        material_select = Select(material_dropdown)
        material_select.select_by_value("BK")
        # print("Selected Book option from material type dropdown")
        
        # Submit the search form
        submit_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[type='image'][alt=' Go ']")
        ))
        submit_button.click()
        # print("Clicked submit button to start search")
        
        # Check for the specific clickable element containing the result count
        try:
            # Wait a bit for the element to be available
            time.sleep(2)
            
            # Use a shorter timeout for checking if results exist (reduced from 30 to 5 seconds)
            short_wait = WebDriverWait(driver, 5)
            
            # Check for an element with class "td2" containing an anchor tag with "set_number" in href
            result_link = short_wait.until(EC.presence_of_element_located(
                (By.XPATH, "//td[contains(@class, 'td2')]//a[contains(@href, 'set_number')]")
            ))

            # If we get here, a result link was found
            # print("Yes - Found clickable element with result count")
            
            # Click the link to navigate to the full results
            result_link.click()
            # print("Navigated to the full results page")
            
            # Wait for the full results page to load
            time.sleep(5)
            
            # Return True to indicate that results were found
            return True
                
        except Exception as e:
            print(f"No - Did not find clickable element with result count for subject '{subject_term}'")
            # Return False to indicate that no results were found
            return False
        
    except Exception as e:
        print(f"Error during search refinement: {str(e)}")
        # Return False to indicate failure
        return False

def click_first_book_title(driver):
    """
    Function to click on the title of the first book in the search results.
    
    Args:
        driver: The Selenium WebDriver instance
    
    Returns:
        bool: True if a book title was found and clicked, False otherwise
    """
    try:
        # Wait for the book rows to load
        wait = WebDriverWait(driver, 10)
        
        # Look for the first book title link using CSS selector
        first_title_link = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "td.td1 a.brieftit")
        ))
        
        # Get the title and URL for logging
        title = first_title_link.text
        url = first_title_link.get_attribute('href')
        # print(f"Found first book title: '{title}'")
        # print(f"URL: {url}")
        
        # Click on the title link
        first_title_link.click()
        # print("Clicked on the first book title")
        
        # Wait for the book details page to load
        time.sleep(3)
        
        # Get the current URL after clicking
        current_url = driver.current_url
        # print(f"Current URL after clicking: {current_url}")
        
        return True
        
    except Exception as e:
        print(f"Error clicking first book title: {str(e)}")
        return False

def process_book_details(driver, subject_code, db_path):
    """
    Function to extract specific information from the book details page and save to database.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_code: The subject code used for the search
        db_path: Path to the SQLite database file
    
    Returns:
        dict: The extracted book details (also saves to database)
    """
    try:
        # Wait for the page to load
        time.sleep(2)
        wait = WebDriverWait(driver, 10)
        
        # Print the current URL
        current_url = driver.current_url
        # print(f"Processing book details at URL: {current_url}")
        
        # Initialize a dictionary to store the extracted information
        book_info = {
            'subject': subject_code,
            'url': current_url,
            'record_number': "missing",
            'title': "missing",
            'title_cleaned': "missing",  # NEW FIELD: cleaned title
            'author_cleaned': "missing",  # NEW FIELD: cleaned author
            'language': "missing",
            'imprint': "missing",  # publication info
            'publication': "missing"  # NEW FIELD: publication information
        }
        
        # Extract record number
        try:
            record_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Record Number')]/following-sibling::td")
            book_info['record_number'] = record_row.text.strip()
            # print(f"Record Number: {book_info['record_number']}")
        except Exception as e:
            # print(f"Record number field not found, using 'missing'")
            pass
        
        # Extract title
        try:
            title_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Title')]/following-sibling::td")
            # The title is in an anchor tag
            title_link = title_row.find_element(By.TAG_NAME, "a")
            book_info['title'] = title_link.text.strip()
            # print(f"Title: {book_info['title']}")
            
            # Split title and author
            title_text = book_info['title']
            if title_text != "missing" and "/" in title_text:
                # Split by "/" and take the first part as title, second as author
                parts = title_text.split("/", 1)  # Split only on first "/" to handle titles with multiple "/"
                book_info['title_cleaned'] = parts[0].strip()
                book_info['author_cleaned'] = parts[1].strip()
            elif title_text != "missing":
                # If no "/" found, assume entire text is the title
                book_info['title_cleaned'] = title_text
                book_info['author_cleaned'] = "missing"
            
            # print(f"Title Cleaned: {book_info['title_cleaned']}")
            # print(f"Author Cleaned: {book_info['author_cleaned']}")
            
        except Exception as e:
            # print(f"Title field not found, using 'missing'")
            pass
        
        # Extract language
        try:
            language_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Language')]/following-sibling::td")
            book_info['language'] = language_row.text.strip()
            # print(f"Language: {book_info['language']}")
        except Exception as e:
            # print(f"Language field not found, using 'missing'")
            pass
        
        # Extract imprint (publication info)
        try:
            imprint_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Imprint')]/following-sibling::td")
            book_info['imprint'] = imprint_row.text.strip()
            # print(f"Imprint: {book_info['imprint']}")
        except Exception as e:
            # print(f"Imprint field not found, using 'missing'")
            pass
        
        # Extract publication information
        try:
            # Try to find the "Publication" field first
            publication_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Publication')]/following-sibling::td")
            book_info['publication'] = publication_row.text.strip()
            # print(f"Publication: {book_info['publication']}")
        except Exception as e:
            # print(f"Publication field not found, trying alternative selectors...")
            # Try alternative selectors in case the field name is different
            try:
                # Try "Publish" or "Published" as field names
                for field_text in ['Publish', 'Published', 'Publication date', 'Publish date']:
                    try:
                        pub_row = driver.find_element(By.XPATH, f"//td[@class='td1' and @id='bold' and contains(text(), '{field_text}')]/following-sibling::td")
                        book_info['publication'] = pub_row.text.strip()
                        # print(f"Found publication info with field name '{field_text}': {book_info['publication']}")
                        break
                    except:
                        continue
                else:
                    # If none of the alternative field names worked, keep as "missing"
                    # print(f"Publication field not found with any alternative selector, using 'missing'")
                    pass
            except Exception as inner_e:
                # print(f"Error in alternative publication extraction: {str(inner_e)}")
                pass
        
        # SAVE TO DATABASE IMMEDIATELY AFTER EXTRACTION
        save_book_to_database(book_info, db_path)
        
        # Return the extracted information
        # print("Book details extracted successfully")
        # print(book_info)
        
        return book_info
        
    except Exception as e:
        print(f"Error processing book details: {str(e)}")        
        # Return a dictionary with default values
        error_book_info = {
            'subject': subject_code,
            'url': driver.current_url if 'driver' in locals() else "error",
            'record_number': "missing",
            'title': "missing",
            'title_cleaned': "missing",  # NEW FIELD in error case too
            'author_cleaned': "missing",  # NEW FIELD in error case too
            'language': "missing",
            'imprint': "missing",
            'publication': "missing"  # NEW FIELD in error case too
        }
        
        # Still try to save error case to database for tracking
        save_book_to_database(error_book_info, db_path)
        
        return error_book_info

def has_next_book(driver):
    """
    Function to check if there is a "Next Record" button on the current book details page.
    
    Args:
        driver: The Selenium WebDriver instance
    
    Returns:
        bool: True if a "Next Record" button is found, False otherwise
    """
    try:
        # Look for the "Next Record" button
        next_button = driver.find_element(By.XPATH, "//img[@alt='Next Record']")
        return True
    except:
        return False

def navigate_to_next_book(driver):
    """
    Function to navigate to the next book by clicking the "Next Record" button.
    
    Args:
        driver: The Selenium WebDriver instance
    
    Returns:
        bool: True if successfully navigated to the next book, False otherwise
    """
    try:
        # Find and click on the "Next Record" button
        next_button = driver.find_element(By.XPATH, "//img[@alt='Next Record']")
        # Get the parent <a> tag that contains the image
        next_link = next_button.find_element(By.XPATH, "./..")
        
        # Click on the link
        next_link.click()
        # print("Clicked on 'Next Record' button")
        
        # Wait for the next book details page to load
        time.sleep(3)
        
        # Get the current URL after clicking
        current_url = driver.current_url
        # print(f"Navigated to next book at URL: {current_url}")
        
        return True
    except Exception as e:
        print(f"Error navigating to next book: {str(e)}")
        return False

def process_all_books_for_subject(driver, subject_code, total_books, db_path):
    """
    Function to process all books for a specific subject.
    If there's only one book, the website automatically shows the book details page.
    If there are multiple books, we need to click on the first book title to view its details,
    then navigate through all remaining books.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_code: The subject code used for the search
        total_books: Total number of books found for this subject
        db_path: Path to the SQLite database file
    
    Returns:
        list: List of dictionaries containing extracted book information
    """
    books_info = []
    
    # If there's only one book, the website automatically shows the book details page
    if total_books == 1:
        print(f"Only 1 book found for subject '{subject_code}' - website automatically shows book details")
        # Process the book details directly (no need to click on a book title)
        book_info = process_book_details(driver, subject_code, db_path)
        if book_info:
            books_info.append(book_info)
            print(f"Added information for the single book in subject '{subject_code}' to results")
        print(f"Processing complete for subject '{subject_code}'")
    else:
        # Multiple books - need to click on the first book title to view its details
        if click_first_book_title(driver):
            # Process the first book
            book_info = process_book_details(driver, subject_code, db_path)
            if book_info:
                books_info.append(book_info)
                print(f"Added information for book 1 in subject '{subject_code}' to results")
            
            # Process all remaining books
            book_count = 1
            while has_next_book(driver) and book_count < total_books:
                # Navigate to the next book
                if navigate_to_next_book(driver):
                    book_count += 1
                    # Process the current book
                    book_info = process_book_details(driver, subject_code, db_path)
                    if book_info:
                        books_info.append(book_info)
                        print(f"Added information for book {book_count} in subject '{subject_code}' to results")
                else:
                    print(f"Failed to navigate to the next book after book {book_count}")
                    break
            
            print(f"Processed a total of {len(books_info)} books for subject '{subject_code}'")
        else:
            print(f"Could not click on the first book title for subject '{subject_code}'")
    
    # Navigate back to the main search page
    try:
        # Find and click on a link to go back to the main search
        # This might need to be customized based on the website's navigation
        driver.get("https://aleweb.ncl.edu.tw/F?func=file&file_name=find-b&CON_LNG=ENG")
        # print("Navigated back to the main search page")
        time.sleep(2)
    except Exception as e:
        print(f"Error returning to main search page: {str(e)}")
    
    return books_info

def explore_subjects_and_all_books(subject_codes, db_path):
    """
    Function to iterate through multiple subject codes, perform a search for each,
    process all books in the results for each subject, and save to a database.
    Now saves each book individually to the database as it's processed.
    
    Args:
        subject_codes: List of subject codes to search for
        db_path: Path to the SQLite database file
    
    Returns:
        list: List of dictionaries containing extracted book information
    """
    try:
        print("Initializing Chrome WebDriver...")
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome()
        
        print("WebDriver initialized successfully")
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Just print a message about the database - will append to it if it exists
        if os.path.exists(db_path):
            print(f"Database exists at {db_path}, will append new data")
        else:
            print(f"Creating a new database at {db_path}")
        
        # Initialize a list to store all book information (for return purposes)
        all_book_info = []
        
        # Loop through each subject code
        for i, subject_code in enumerate(subject_codes):
            print(f"\nProcessing subject {i+1}/{len(subject_codes)}: {subject_code}")
            
            # Navigate to the advanced search page
            navigate_to_advanced_search(driver)
            
            # Refine the search with the current subject code
            # Now returns a Boolean indicating if search results were found
            results_found = refine_search(driver, subject_code, language="CHI", start_year="1950", end_year="2023")
            
            # Only proceed if search results were found
            if results_found:
                try:
                    # Wait for the page to load
                    wait = WebDriverWait(driver, 30)

                    # Extract the total number of books in the search
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
                    total_info = element.text
                    # print(f"Raw total info text: '{total_info}'")

                    # Look for the number after "Total"
                    match = re.search(r'Total\s+(\d+)', total_info)
                    if match:
                        tot_books = int(match.group(1))
                        print(f"Total number of books in category {subject_code}: {tot_books}")
                    else:
                        # print(f"Pattern didn't match. Raw text: '{total_info}'")
                        tot_books = 0  # Default to 0 if we can't extract the number

                    # If books were found for this subject
                    if tot_books > 0:
                        # Process all books for this subject, passing the database path
                        # Note: Books are now saved individually within process_all_books_for_subject
                        subject_books = process_all_books_for_subject(driver, subject_code, tot_books, db_path)
                        
                        # Add to the master list (for return purposes and summary)
                        all_book_info.extend(subject_books)
                        
                        print(f"Successfully processed and saved {len(subject_books)} books for subject '{subject_code}'")
                    else:
                        print(f"No books found for subject '{subject_code}'")
                        
                except Exception as e:
                    print(f"Error processing search results for subject '{subject_code}': {str(e)}")
                    # Continue to the next subject regardless of errors
            else:
                print(f"No search results found for subject '{subject_code}' - moving to next subject")
            
            # Sleep to avoid having problems with the website
            time.sleep(randint(1, 3))
            
            # Let user know we're moving to the next subject automatically
            if i < len(subject_codes) - 1:
                print(f"\nMoving to the next subject: {subject_codes[i+1]}")
            else:
                print("\nAll subjects have been processed.")
        
        # Print the final results
        print("\n\n===== EXTRACTED BOOK INFORMATION SUMMARY =====")
        print(f"Total books extracted and saved to database: {len(all_book_info)}")
        print(f"Note: Each book was saved to the database immediately after being scraped.")
        
        # Print a sample of the first 10 books with updated field display
        for i, book in enumerate(all_book_info[:10]):  # Print first 10 books for preview
            print(f"\nBook {i+1}:")
            # Updated to ensure 'publication' field is shown
            field_order = ['subject', 'url', 'record_number', 'title', 'language', 'imprint', 'publication']
            for key in field_order:
                if key in book:
                    print(f"  {key}: {book[key]}")
            # Print any other fields that might exist
            for key, value in book.items():
                if key not in field_order:
                    print(f"  {key}: {value}")
        
        if len(all_book_info) > 10:
            print(f"\n... and {len(all_book_info) - 10} more books were saved to database")
        
        # Give the user a chance to review results before closing the browser
        input("\nPress Enter to close the browser...")
        
        return all_book_info
    
    except Exception as e:
        print(f"Error during exploration: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        # Close the driver if it was successfully initialized
        if 'driver' in locals():
            driver.quit()
            print("Browser closed")
        else:
            print("Driver was not initialized")

# Call this function with a list of subject codes
if __name__ == "__main__":
    # Define the database path
    db_path = "../scraped_data/ncl_subject_books_details.db"
    
    # Define the list of Chinese keywords
    keywords = [
        "水生結構", #Aquatic Structures
        "商業組織",  #Business Organizations
        "交通管制",  #Traffic Control
    ]
    
    # Run the program with the subject list and database path
    book_results = explore_subjects_and_all_books(keywords, db_path)