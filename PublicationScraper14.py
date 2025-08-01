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
import json
import traceback
from selenium.common.exceptions import WebDriverException, TimeoutException

# State management for crash recovery
STATE_FILE = "../scraped_data/scraping_state.json"

def save_state(period_index, current_period, subject_index, current_subject, book_index=0, total_books=0, current_url=""):
    """
    Save the current scraping state to a file for crash recovery.
    
    Args:
        period_index: Current time period index being processed
        current_period: Current time period tuple (start_year, end_year)
        subject_index: Current subject index being processed
        current_subject: Current subject code being processed
        book_index: Current book index within the subject (0-based)
        total_books: Total books for current subject
        current_url: Current URL being processed
    """
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        
        state = {
            "period_index": period_index,
            "current_period": current_period,
            "subject_index": subject_index,
            "current_subject": current_subject,
            "book_index": book_index,
            "total_books": total_books,
            "current_url": current_url,
            "timestamp": time.time()
        }
        
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        
        print(f"State saved: Period {period_index+1} ({current_period[0]}-{current_period[1]}), Subject {subject_index+1}, Book {book_index+1}/{total_books}")
        
    except Exception as e:
        print(f"Warning: Could not save state: {str(e)}")

def load_state():
    """
    Load the previous scraping state from file.
    
    Returns:
        dict: State dictionary or None if no valid state found
    """
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            period_info = f"Period {state['period_index']+1} ({state['current_period'][0]}-{state['current_period'][1]})"
            print(f"Found previous state: {period_info}, Subject {state['subject_index']+1}, Book {state['book_index']+1}/{state['total_books']}")
            return state
        return None
    except Exception as e:
        print(f"Could not load previous state: {str(e)}")
        return None

def clear_state():
    """Clear the state file after successful completion."""
    try:
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
            print("State file cleared")
    except Exception as e:
        print(f"Warning: Could not clear state file: {str(e)}")

def initialize_driver():
    """Initialize a new Chrome WebDriver with robust options."""
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("Chrome WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {str(e)}")
        raise

def safe_driver_operation(func, driver, *args, max_retries=3, **kwargs):
    """
    Safely execute a driver operation with crash recovery.
    
    Args:
        func: Function to execute
        driver: WebDriver instance (will be recreated if needed)
        max_retries: Maximum number of retries
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Tuple: (result, updated_driver)
    """
    for attempt in range(max_retries):
        try:
            result = func(driver, *args, **kwargs)
            return result, driver
        except (WebDriverException, TimeoutException) as e:
            print(f"WebDriver error on attempt {attempt + 1}: {str(e)}")
            
            if attempt < max_retries - 1:
                print("Attempting to recover...")
                try:
                    driver.quit()
                except:
                    pass
                
                # Wait before retrying
                time.sleep(5)
                driver = initialize_driver()
                print("WebDriver reinitialized")
            else:
                print(f"Failed after {max_retries} attempts")
                raise
        except Exception as e:
            print(f"Non-WebDriver error: {str(e)}")
            raise
    
    return None, driver

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

            # EXTRACT THE COUNT FROM THE CLICKABLE ELEMENT BEFORE CLICKING
            result_text = result_link.text.strip()
            print(f"Found clickable result element with text: '{result_text}'")
            
            # Try to extract number from the result text
            # Look for patterns like "1 records found", "5 records found", etc.
            count_match = re.search(r'(\d+)', result_text)
            if count_match:
                result_count = int(count_match.group(1))
                print(f"Extracted result count from clickable element: {result_count}")
                # Store this count globally so it can be accessed later
                driver.ncl_result_count = result_count
            else:
                print(f"Could not extract numeric count from result text: '{result_text}'")
                # Set a default that will be overridden later if possible
                driver.ncl_result_count = None
            
            # Click the link to navigate to the full results
            result_link.click()
            # print("Navigated to the full results page")
            
            # Wait for the full results page to load
            time.sleep(5)
            
            # Return True to indicate that results were found
            return True
                
        except Exception as e:
            print(f"No - Did not find clickable element with result count for subject '{subject_term}' ({start_year}-{end_year})")
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

def navigate_to_specific_book(driver, book_index, total_books):
    """
    Navigate to a specific book by index in the search results.
    
    Args:
        driver: The Selenium WebDriver instance
        book_index: 0-based index of the book to navigate to
        total_books: Total number of books available
    
    Returns:
        bool: True if successfully navigated to the book, False otherwise
    """
    try:
        if book_index == 0:
            # For the first book, just click on the first title
            return click_first_book_title(driver)
        else:
            # For subsequent books, we need to navigate step by step
            # First, click on the first book
            if not click_first_book_title(driver):
                return False
            
            # Then navigate through books until we reach the target index
            current_index = 0
            while current_index < book_index and has_next_book(driver):
                if not navigate_to_next_book(driver):
                    return False
                current_index += 1
            
            return current_index == book_index
    except Exception as e:
        print(f"Error navigating to book {book_index}: {str(e)}")
        return False

def process_book_details(driver, subject_code, start_year, end_year, db_path):
    """
    Function to extract specific information from the book details page and save to database.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_code: The subject code used for the search
        start_year: Start year of the search period
        end_year: End year of the search period
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
            'search_period': f"{start_year}-{end_year}",  # NEW FIELD: search period
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
            'search_period': f"{start_year}-{end_year}",
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

def process_all_books_for_subject(driver, subject_code, start_year, end_year, total_books, db_path, resume_from_book=0):
    """
    Function to process all books for a specific subject with crash recovery support.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_code: The subject code used for the search
        start_year: Start year of the search period
        end_year: End year of the search period
        total_books: Total number of books found for this subject
        db_path: Path to the SQLite database file
        resume_from_book: Book index to resume from (0-based)
    
    Returns:
        list: List of dictionaries containing extracted book information
    """
    books_info = []
    
    try:
        # If there's only one book, the website automatically shows the book details page
        if total_books == 1:
            print(f"Only 1 book found for subject '{subject_code}' ({start_year}-{end_year}) - website automatically shows book details")
            if resume_from_book == 0:  # Only process if we haven't processed it yet
                # Process the book details directly
                book_info = process_book_details(driver, subject_code, start_year, end_year, db_path)
                if book_info:
                    books_info.append(book_info)
                    print(f"Added information for the single book in subject '{subject_code}' ({start_year}-{end_year}) to results")
            print(f"Processing complete for subject '{subject_code}' ({start_year}-{end_year})")
        else:
            # Multiple books - need to navigate appropriately
            if resume_from_book == 0:
                # Starting fresh - click on the first book title
                if not click_first_book_title(driver):
                    print(f"Could not click on the first book title for subject '{subject_code}' ({start_year}-{end_year})")
                    return books_info
            else:
                # Resuming - navigate to the specific book
                print(f"Resuming from book {resume_from_book + 1}/{total_books}")
                if not navigate_to_specific_book(driver, resume_from_book, total_books):
                    print(f"Could not navigate to book {resume_from_book + 1} for subject '{subject_code}' ({start_year}-{end_year})")
                    return books_info
            
            # Process books starting from resume_from_book
            for book_index in range(resume_from_book, total_books):
                print(f"Processing book {book_index + 1}/{total_books} for subject '{subject_code}' ({start_year}-{end_year})")
                
                # Process the current book
                book_info, driver = safe_driver_operation(process_book_details, driver, subject_code, start_year, end_year, db_path)
                if book_info:
                    books_info.append(book_info)
                    print(f"Added information for book {book_index + 1} in subject '{subject_code}' ({start_year}-{end_year}) to results")
                
                # If this is not the last book, navigate to the next one
                if book_index < total_books - 1:
                    if has_next_book(driver):
                        success, driver = safe_driver_operation(navigate_to_next_book, driver)
                        if not success:
                            print(f"Failed to navigate to next book after book {book_index + 1}")
                            break
                    else:
                        print(f"No 'Next Record' button found after book {book_index + 1}")
                        break
            
            print(f"Processed a total of {len(books_info)} books for subject '{subject_code}' ({start_year}-{end_year})")
    
    except Exception as e:
        print(f"Error processing books for subject '{subject_code}' ({start_year}-{end_year}): {str(e)}")
        traceback.print_exc()
    
    return books_info

def explore_subjects_and_all_books_by_periods(subject_codes, time_periods, db_path, resume_state=None):
    """
    Function to iterate through time periods, then through multiple subject codes with crash recovery support.
    
    Args:
        subject_codes: List of subject codes to search for
        time_periods: List of tuples (start_year, end_year) for time periods
        db_path: Path to the SQLite database file
        resume_state: Previous state to resume from (if any)
    
    Returns:
        list: List of dictionaries containing extracted book information
    """
    driver = None
    
    try:
        print("Initializing Chrome WebDriver...")
        driver = initialize_driver()
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Database setup message
        if os.path.exists(db_path):
            print(f"Database exists at {db_path}, will append new data")
        else:
            print(f"Creating a new database at {db_path}")
        
        # Initialize a list to store all book information
        all_book_info = []
        
        # Determine starting point
        start_period_index = 0
        start_subject_index = 0
        start_book_index = 0
        
        if resume_state:
            start_period_index = resume_state["period_index"]
            start_subject_index = resume_state["subject_index"]
            start_book_index = resume_state["book_index"]
            period_info = f"{resume_state['current_period'][0]}-{resume_state['current_period'][1]}"
            print(f"Resuming from period {start_period_index + 1}/{len(time_periods)} ({period_info}), subject {start_subject_index + 1}/{len(subject_codes)}, book {start_book_index + 1}")
        
        # Loop through each time period
        for period_idx in range(start_period_index, len(time_periods)):
            start_year, end_year = time_periods[period_idx]
            print(f"\n{'='*60}")
            print(f"PROCESSING TIME PERIOD {period_idx+1}/{len(time_periods)}: {start_year}-{end_year}")
            print(f"{'='*60}")
            
            # Determine which subject to start from for this period
            current_subject_start = start_subject_index if period_idx == start_period_index else 0
            
            # Loop through each subject code for this time period
            for subject_idx in range(current_subject_start, len(subject_codes)):
                subject_code = subject_codes[subject_idx]
                print(f"\nProcessing subject {subject_idx+1}/{len(subject_codes)} in period {start_year}-{end_year}: {subject_code}")
                
                try:
                    # Navigate to the advanced search page
                    navigate_to_advanced_search(driver)
                    
                    # Refine the search with the current subject code and time period
                    results_found, driver = safe_driver_operation(refine_search, driver, subject_code, "CHI", str(start_year), str(end_year))
                    
                    # Only proceed if search results were found
                    if results_found:
                        try:
                            # Wait for the page to load
                            wait = WebDriverWait(driver, 30)

                            # Try to extract the total number of books using the traditional method first
                            tot_books = 0
                            try:
                                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
                                total_info = element.text

                                # Look for the number after "Total"
                                match = re.search(r'Total\s+(\d+)', total_info)
                                if match:
                                    tot_books = int(match.group(1))
                                    print(f"Total number of books (from results page): {tot_books}")
                                else:
                                    raise Exception("Could not parse total from results page")
                                    
                            except Exception as e:
                                print(f"Traditional method failed: {str(e)}")
                                
                                # Fall back to the count we extracted from the clickable element
                                if hasattr(driver, 'ncl_result_count') and driver.ncl_result_count is not None:
                                    tot_books = driver.ncl_result_count
                                    print(f"Using count from clickable element: {tot_books}")
                                else:
                                    print("No fallback count available, assuming 0 books")
                                    tot_books = 0

                            print(f"Final total number of books in category {subject_code} ({start_year}-{end_year}): {tot_books}")

                            # If books were found for this subject and period
                            if tot_books > 0:
                                # Determine which book to start from for this subject
                                current_book_start = start_book_index if (period_idx == start_period_index and subject_idx == start_subject_index) else 0
                                
                                # Update state for this subject and period
                                save_state(period_idx, (start_year, end_year), subject_idx, subject_code, current_book_start, tot_books, driver.current_url)
                                
                                # Process books for this subject and period
                                subject_books = process_all_books_for_subject(
                                    driver, subject_code, start_year, end_year, tot_books, db_path, current_book_start
                                )
                                
                                # Add to the master list
                                all_book_info.extend(subject_books)
                                
                                print(f"Successfully processed and saved {len(subject_books)} books for subject '{subject_code}' ({start_year}-{end_year})")
                            else:
                                print(f"No books found for subject '{subject_code}' ({start_year}-{end_year})")
                                
                        except Exception as e:
                            print(f"Error processing search results for subject '{subject_code}' ({start_year}-{end_year}): {str(e)}")
                            traceback.print_exc()
                            # Continue to the next subject
                    else:
                        print(f"No search results found for subject '{subject_code}' ({start_year}-{end_year}) - moving to next subject")
                    
                    # Reset book start index for subsequent subjects
                    start_book_index = 0
                    
                    # Sleep to avoid problems with the website
                    time.sleep(randint(1, 3))
                    
                    # Let user know we're moving to the next subject
                    if subject_idx < len(subject_codes) - 1:
                        print(f"Moving to the next subject: {subject_codes[subject_idx+1]}")
                    else:
                        print(f"All subjects processed for period {start_year}-{end_year}")
                        
                except Exception as e:
                    print(f"Critical error processing subject '{subject_code}' ({start_year}-{end_year}): {str(e)}")
                    traceback.print_exc()
                    
                    # Try to recover by reinitializing the driver
                    try:
                        if driver:
                            driver.quit()
                        driver = initialize_driver()
                        print("Driver reinitialized due to critical error")
                        
                        # Save current state before continuing
                        save_state(period_idx, (start_year, end_year), subject_idx, subject_code, 0, 0, "")
                        
                    except Exception as recovery_error:
                        print(f"Failed to recover from critical error: {str(recovery_error)}")
                        raise
            
            # Reset subject start index for subsequent periods
            start_subject_index = 0
            
            # Let user know we're moving to the next period
            if period_idx < len(time_periods) - 1:
                next_start_year, next_end_year = time_periods[period_idx + 1]
                print(f"\n{'='*60}")
                print(f"COMPLETED PERIOD {start_year}-{end_year}")
                print(f"Moving to next time period: {next_start_year}-{next_end_year}")
                print(f"{'='*60}")
            else:
                print(f"\n{'='*60}")
                print("ALL TIME PERIODS HAVE BEEN PROCESSED!")
                print(f"{'='*60}")
        
        # Clear state file on successful completion
        clear_state()
        
        # Print the final results
        print("\n\n===== EXTRACTED BOOK INFORMATION SUMMARY =====")
        print(f"Total books extracted and saved to database: {len(all_book_info)}")
        print(f"Note: Each book was saved to the database immediately after being scraped.")
        
        # Print summary by time period
        print("\n===== SUMMARY BY TIME PERIOD =====")
        for period_idx, (start_year, end_year) in enumerate(time_periods):
            period_books = [book for book in all_book_info if book.get('search_period') == f"{start_year}-{end_year}"]
            print(f"Period {start_year}-{end_year}: {len(period_books)} books")
        
        # Print a sample of the first 10 books
        print("\n===== SAMPLE OF FIRST 10 BOOKS =====")
        for i, book in enumerate(all_book_info[:10]):
            print(f"\nBook {i+1}:")
            field_order = ['subject', 'search_period', 'url', 'record_number', 'title', 'language', 'imprint', 'publication']
            for key in field_order:
                if key in book:
                    print(f"  {key}: {book[key]}")
            # Print any other fields that might exist
            for key, value in book.items():
                if key not in field_order:
                    print(f"  {key}: {value}")
        
        if len(all_book_info) > 10:
            print(f"\n... and {len(all_book_info) - 10} more books were saved to database")
        
        return all_book_info
    
    except Exception as e:
        print(f"Fatal error during exploration: {str(e)}")
        traceback.print_exc()
        
        # Save current state for potential resume
        if 'period_idx' in locals() and 'subject_idx' in locals():
            try:
                current_period = time_periods[period_idx] if period_idx < len(time_periods) else (0, 0)
                current_subject = subject_codes[subject_idx] if subject_idx < len(subject_codes) else "unknown"
                save_state(period_idx, current_period, subject_idx, current_subject, 0, 0, driver.current_url if driver else "")
                print("State saved for potential resume")
            except:
                print("Could not save state on fatal error")
        
        return []
    finally:
        # Close the driver if it exists
        if driver:
            try:
                driver.quit()
                print("Browser closed")
            except:
                print("Error closing browser")

def main_with_recovery():
    """
    Main function that handles crash recovery automatically with time period cycling.
    """
    # Define the database path
    db_path = "../scraped_data/ncl_subject_books_details.db"
    
    # Define the list of Chinese keywords
    keywords = [
       "會計學",    # Accounting
       "農業",      # Agriculture
       "農學",      # Agronomy
       "畜牧業",    # Animal husbandry
       "應用作",    # Applied Operations
       "應用物理學", # Applied physics
        "水生結構",  # Aquatic structures
        "建築",      # Architecture
        "育種",      # Breeding
        "商業材料",  # Business materials
        "商業組織",  # Business organizations
        "通信",      # Communication
        "建設",      # Construction
        "彈性計",    # Elastometers
        "工程",      # Engineering
       "炸藥",      # Explosives
       "農業",    # Farming
       "釣魚",      # Fishing
       "林業",      # Forestry
       "鍛造作品",  # Forged works
       "燃料",      # Fuel
       "毛皮製品",  # Fur products
       "提供",     # Furnishing 
        "傢俱",     # Furnishings
       "硬體",      # Hardware
        "家政學",    # Home economics
       "家庭工作坊", # Home workshop
       "園藝",      # Horticulture
       "家用電器",  # Household appliances
       "工業",      # Industry
        "鐵",        # Iron
       "皮具",      # Leather goods
       "皮革加工", # Leather processing
       "木材加工",  # Lumber processing
       "管理",      # Management
       "製造",      # Manufacturing
       "製造業",    # Manufacturing industry
       "冶金",      # Metallurgy
       "五金",      # Hardware/Metal products
       "金工",      # Metalwork
       "軍事",      # Military
       "採礦",      # Mining
       "專利",      # Patents
       "藥理學",    # Pharmacology
       "種植園作物", # Plantation crops
       "精密儀器",  # Precision instruments
       "乳製品加工", # Processing of dairy products
       "公共關係",  # Public relations
       "鐵路",      # Railways
        "屋頂覆蓋物", # Roofing materials
       "鋼",        # Steel
        "科技",      # Technology
       "紡織品",    # Textiles
       "交通管制",  # Traffic control
       "運輸",      # Transportation
        "水結構",    # Water structures
       "木製品"     # Wood products
    ]
    
    # Define the time periods (start_year, end_year)
    time_periods = [
        (1900, 1920),
        (1920, 1940), 
        (1940, 1960),
        (1960, 1980),
        (1980, 2000),
        (2000, 2020),
        (2020, 2023)
    ]
    
    print("Time Period Cycling Scraper")
    print("===========================")
    print("This scraper will search through all keywords for each time period:")
    for i, (start_year, end_year) in enumerate(time_periods):
        print(f"  Period {i+1}: {start_year}-{end_year}")
    print(f"Total keywords per period: {len(keywords)}")
    print(f"Total searches to perform: {len(time_periods)} × {len(keywords)} = {len(time_periods) * len(keywords)}")
    print()
    
    # Check for previous state
    resume_state = load_state()
    
    if resume_state:
        period_info = f"period {resume_state['period_index']+1} ({resume_state['current_period'][0]}-{resume_state['current_period'][1]})"
        response = input(f"Found previous incomplete session. Resume from {period_info}, subject {resume_state['subject_index']+1}, book {resume_state['book_index']+1}? (y/n): ")
        if response.lower() != 'y':
            print("Starting fresh session...")
            clear_state()
            resume_state = None
        else:
            print("Resuming previous session...")
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Run the program with crash recovery and time period cycling
            book_results = explore_subjects_and_all_books_by_periods(keywords, time_periods, db_path, resume_state)
            
            if book_results or not resume_state:  # Success or first run
                print("Scraping completed successfully!")
                break
            else:
                print("No results obtained, but this might be expected if resuming from end of list")
                break
                
        except Exception as e:
            retry_count += 1
            print(f"\nProgram crashed (attempt {retry_count}/{max_retries}): {str(e)}")
            
            if retry_count < max_retries:
                print("Attempting to recover and continue...")
                # Load the latest state
                resume_state = load_state()
                if resume_state:
                    period_info = f"period {resume_state['period_index']+1} ({resume_state['current_period'][0]}-{resume_state['current_period'][1]})"
                    print(f"Will resume from {period_info}, subject {resume_state['subject_index']+1}, book {resume_state['book_index']+1}")
                else:
                    print("No recovery state found, will restart from beginning")
                
                # Wait before retrying
                time.sleep(10)
            else:
                print("Maximum retry attempts reached. Please check the logs and try again manually.")
                print("You can resume from the last saved state by running the program again.")
                break

# Call this function with crash recovery and time period cycling
if __name__ == "__main__":
    main_with_recovery()