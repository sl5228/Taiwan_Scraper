#%%  Import packages
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import re
import pandas as pd
import math
import sqlite3
from random import randint
import os
import json
import traceback

class ScrapingState:
    """Class to manage scraping state for recovery purposes with time periods"""
    
    def __init__(self, state_file_path):
        self.state_file = state_file_path
        self.state = self.load_state()
    
    def load_state(self):
        """Load the scraping state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self.get_default_state()
        return self.get_default_state()
    
    def save_state(self):
        """Save the current scraping state to file"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def get_default_state(self):
        """Get the default state structure with time periods"""
        return {
            'current_period_index': 0,
            'current_period': None,
            'current_subject_index': 0,
            'current_page': 0,
            'current_subject': None,
            'total_pages': 0,
            'completed_subjects': [],
            'completed_periods': [],
            'last_url': None,
            'total_books_in_subject': 0
        }
    
    def update_period_progress(self, period_index, period_tuple):
        """Update progress for current time period"""
        self.state['current_period_index'] = period_index
        self.state['current_period'] = period_tuple
        self.state['current_subject_index'] = 0  # Reset subject index for new period
        self.state['current_page'] = 0
        self.state['completed_subjects'] = []  # Reset completed subjects for new period
        self.save_state()
    
    def update_subject_progress(self, subject_index, subject, total_pages, total_books):
        """Update progress for current subject"""
        self.state['current_subject_index'] = subject_index
        self.state['current_subject'] = subject
        self.state['current_page'] = 0
        self.state['total_pages'] = total_pages
        self.state['total_books_in_subject'] = total_books
        self.save_state()
    
    def update_page_progress(self, page, url=None):
        """Update progress for current page"""
        self.state['current_page'] = page
        if url:
            self.state['last_url'] = url
        self.save_state()
    
    def complete_subject(self, subject):
        """Mark a subject as completed for current period"""
        if subject not in self.state['completed_subjects']:
            self.state['completed_subjects'].append(subject)
        self.save_state()
    
    def complete_period(self, period_tuple):
        """Mark a time period as completed"""
        if period_tuple not in self.state['completed_periods']:
            self.state['completed_periods'].append(period_tuple)
        self.save_state()
    
    def reset_state(self):
        """Reset the state to start fresh"""
        self.state = self.get_default_state()
        self.save_state()

def initialize_driver():
    """Initialize Chrome WebDriver with recovery-friendly options"""
    try:
        options = webdriver.ChromeOptions()
        # Add options to make the driver more stable
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=options)
        print("WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        raise

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
        print("Opened the Full Catalog page")
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 30)
        
        # Find and click on the "Advanced Search" link
        advanced_search_link = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a.mainmenu02[title='Advanced Search']")
        ))
        advanced_search_link.click()
        print("Clicked on Advanced Search link")
        
    except Exception as e:
        print(f"Error navigating to advanced search page: {str(e)}")
        raise

def navigate_to_url_directly(driver, url):
    """
    Navigate directly to a specific URL for recovery purposes
    
    Args:
        driver: The Selenium WebDriver instance
        url: The URL to navigate to
    """
    try:
        driver.get(url)
        print(f"Successfully navigated to URL: {url}")
        time.sleep(3)  # Wait for page to load
        return True
    except Exception as e:
        print(f"Error navigating to URL {url}: {e}")
        return False

def refine_search(driver, subject_term, language="CHI", start_year="1500", end_year="2023"):
    """
    Function to refine the search on the advanced search page.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_term: The subject term to search for
        language: The language to filter by (default: "CHI" for Chinese)
        start_year: The starting year for publication date filter
        end_year: The ending year for publication date filter
    
    Returns:
        bool: True if search results were found, False otherwise
    """
    try:
        wait = WebDriverWait(driver, 30)
        
        # Now on the advanced search page, select the Subject option from dropdown
        subject_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "find_code")))
        subject_select = Select(subject_dropdown)
        subject_select.select_by_value("WSU")
        print("Selected Subject option from dropdown")
        
        # Enter the subject term in the search input
        search_input = wait.until(EC.presence_of_element_located((By.NAME, "request")))
        search_input.clear()  # Clear the field first
        search_input.send_keys(subject_term)
        print(f"Entered subject term: {subject_term}")
        
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
                print("Selected 'N' radio button using JavaScript")
            else:
                print("Selected 'N' radio button")
                
        except Exception as radio_error:
            print(f"Error with first radio button approach: {str(radio_error)}")
            # Try alternate approach by finding parent element first
            try:
                adjacent_radio = driver.find_element(
                    By.XPATH, "//input[@type='radio' and @name='adjacent1' and @value='N']"
                )
                driver.execute_script("arguments[0].click();", adjacent_radio)
                print("Selected 'N' radio button using XPath and JavaScript")
            except Exception as alt_radio_error:
                print(f"Error with alternate radio button approach: {str(alt_radio_error)}")
                raise
        
        # Select Chinese from the language dropdown
        language_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_1")))
        language_select = Select(language_dropdown)
        language_select.select_by_value(language)
        print(f"Selected language: {language}")
        
        # Enter the start year in the textbox - clear first
        start_year_input = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_2")))
        start_year_input.clear()  # Clear the field first
        start_year_input.send_keys(start_year)
        print(f"Entered start year: {start_year}")
        
        # Enter the end year in the textbox - clear first
        end_year_input = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_3")))
        end_year_input.clear()  # Clear the field first
        end_year_input.send_keys(end_year)
        print(f"Entered end year: {end_year}")
        
        # Select Book from the material type dropdown
        material_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_4")))
        material_select = Select(material_dropdown)
        material_select.select_by_value("BK")
        print("Selected Book option from material type dropdown")
        
        # Submit the search form
        submit_button = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "input[type='image'][alt=' Go ']")
        ))
        submit_button.click()
        print("Clicked submit button to start search")
        
        # Check for the specific clickable element containing the result count
        try:
            # Wait a bit for the element to be available
            time.sleep(2)
            
            # Use a shorter timeout for checking if results exist
            short_wait = WebDriverWait(driver, 5)
            
            # Check for an element with class "td2" containing an anchor tag with "set_number" in href
            # This pattern matches the example HTML you provided
            result_link = short_wait.until(EC.presence_of_element_located(
                (By.XPATH, "//td[contains(@class, 'td2')]//a[contains(@href, 'set_number')]")
            ))

            # If we get here, a result link was found
            print("Yes - Found clickable element with result count")
            
            # Click the link to navigate to the full results
            result_link.click()
            print("Navigated to the full results page")
            
            # Wait for the full results page to load
            time.sleep(5)
            
            # Return True to indicate that results were found
            return True
                
        except Exception as e:
            print("No - Did not find clickable element with result count")
            print(f"No search results found for subject '{subject_term}'")
            
            # Return False to indicate that no results were found
            return False
        
    except Exception as e:
        print(f"Error during search refinement: {str(e)}")
        # Return False to indicate failure
        return False

def navigate_to_page(driver, target_page, current_page=0):
    """
    Navigate to a specific page number from the current page
    
    Args:
        driver: The Selenium WebDriver instance
        target_page: The page number to navigate to (0-indexed)
        current_page: The current page number (0-indexed)
    
    Returns:
        bool: True if navigation was successful, False otherwise
    """
    try:
        wait = WebDriverWait(driver, 10)
        
        if target_page == current_page:
            print(f"Already on target page {target_page + 1}")
            return True
        
        # Calculate how many pages to navigate
        pages_to_navigate = target_page - current_page
        
        if pages_to_navigate > 0:
            # Navigate forward
            for _ in range(pages_to_navigate):
                try:
                    next_button = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "img[src$='f-next-page.gif'][alt='Next Page']")
                    ))
                    next_button.click()
                    time.sleep(3)
                    print(f"Navigated forward one page")
                except Exception as e:
                    print(f"Could not navigate to next page: {e}")
                    return False
        else:
            # Navigate backward (if needed - though this might be tricky with this website)
            print("Backward navigation not implemented - restarting search might be needed")
            return False
        
        print(f"Successfully navigated to page {target_page + 1}")
        return True
        
    except Exception as e:
        print(f"Error navigating to page {target_page + 1}: {e}")
        return False

def extract_info_books(book_rows):
    """Extract book information from the current page"""
    # Initialize a list to store book information
    books_data = []
    
    # Extract information for each book
    for row in book_rows:
        try:
            # Extract title and URL
            title_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(3) a.brieftit")
            title = title_element.text
            # Extract the URL from the href attribute
            url = title_element.get_attribute('href')
        
            # Extract author
            author_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(4)")
            author = author_element.text
        
            # Extract publisher
            publisher_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(5)")
            publisher = publisher_element.text
        
            # Extract year of publication (handling JavaScript-rendered content)
            year_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(6)")
            year_script = year_element.get_attribute('innerHTML')
            
            # Print the first row's year script to debug
            if books_data == []:  # If this is the first book
                print(f"Sample year_script: {year_script[:100]}...")  # Print first 100 chars
            
            # Try different patterns for the year
            year_match = re.search(r'</script>\s*(\d{4})', year_script)
            if year_match:
                year = year_match.group(1)
            else:
                # Try another pattern or just extract any 4 digits
                alt_match = re.search(r'(\d{4})', year_script)
                if alt_match:
                    year = alt_match.group(1)
                else:
                    year = "Unknown"  # Default if no year found
                        
            # Extract call number (if available)
            call_number_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(7)")
            call_number = call_number_element.text.strip() if call_number_element.text.strip() else None
        
            # Append extracted data to the books_data list
            books_data.append({
                'title': title,
                'url': url,  # Added the URL to the data dictionary
                'author': author,
                'publisher': publisher,
                'year': year,
                'call_number': call_number,
            })
        except Exception as e:
            print(f"Error extracting information from a book row: {str(e)}")
            # Continue with the next row instead of failing completely
            continue
            
    return books_data

def save_page_data_to_db(books_data, subject_code, start_year, end_year, db_path, page_num):
    """
    Function to save a single page's worth of book data to the database.
    
    Args:
        books_data: List of dictionaries containing book information
        subject_code: The subject term that was searched
        start_year: Start year of the time period
        end_year: End year of the time period
        db_path: Path to the SQLite database file
        page_num: Page number being saved (for logging purposes)
    
    Returns:
        bool: True if data was saved successfully, False otherwise
    """
    try:
        if books_data:
            # Convert to DataFrame
            books_df = pd.DataFrame(books_data)
            
            # Add subject term and time period to the dataframe
            books_df['subject'] = subject_code
            books_df['search_period_start'] = start_year
            books_df['search_period_end'] = end_year
            books_df['search_period'] = f"{start_year}-{end_year}"
            
            # Connect to the SQLite database (creates it if it doesn't exist)
            conn = sqlite3.connect(db_path)
            
            # Save the DataFrame to the database, appending if the table exists
            books_df.to_sql('books', conn, if_exists='append', index=False)
            
            # Close the connection
            conn.close()
            
            print(f"Successfully saved {len(books_df)} books from page {page_num} (period {start_year}-{end_year}) to database")
            return True
        else:
            print(f"No book data to save for page {page_num}")
            return False
            
    except Exception as e:
        print(f"Error saving page {page_num} data to database: {str(e)}")
        return False

def attempt_recovery(driver, state_manager, subject_codes, time_periods):
    """
    Attempt to recover from the last saved state
    
    Args:
        driver: The Selenium WebDriver instance
        state_manager: The ScrapingState instance
        subject_codes: List of all subject codes
        time_periods: List of time period tuples
    
    Returns:
        tuple: (success, current_period_index, current_subject_index, current_page)
    """
    try:
        state = state_manager.state
        
        if state['current_period'] is None:
            print("No previous state found, starting fresh")
            return True, 0, 0, 0
        
        period_info = f"{state['current_period'][0]}-{state['current_period'][1]}"
        print(f"Attempting recovery from period: {period_info}")
        print(f"Subject: {state['current_subject']}")
        print(f"Last page was: {state['current_page'] + 1}")
        
        # If we have a direct URL, try to navigate to it
        if state['last_url']:
            print(f"Attempting to navigate to last URL: {state['last_url']}")
            if navigate_to_url_directly(driver, state['last_url']):
                return True, state['current_period_index'], state['current_subject_index'], state['current_page']
        
        # If direct URL navigation failed, try to recreate the search
        print("Direct URL navigation failed, recreating search...")
        
        # Navigate to advanced search page
        navigate_to_advanced_search(driver)
        
        # Get current period and subject
        current_period = state['current_period']
        current_subject = subject_codes[state['current_subject_index']]
        
        # Perform the search for the current subject and period
        results_found = refine_search(driver, current_subject, language="CHI", 
                                    start_year=str(current_period[0]), 
                                    end_year=str(current_period[1]))
        
        if not results_found:
            print(f"Could not recreate search for subject: {current_subject} in period {current_period[0]}-{current_period[1]}")
            return False, state['current_period_index'], state['current_subject_index'], 0
        
        # Navigate to the correct page if needed
        if state['current_page'] > 0:
            print(f"Navigating to page {state['current_page'] + 1}...")
            if not navigate_to_page(driver, state['current_page'], 0):
                print("Could not navigate to the correct page, starting from page 1")
                return True, state['current_period_index'], state['current_subject_index'], 0
        
        print("Recovery successful!")
        return True, state['current_period_index'], state['current_subject_index'], state['current_page']
        
    except Exception as e:
        print(f"Recovery failed: {e}")
        return False, 0, 0, 0

def scrape_multiple_subjects_with_time_periods(subject_codes, time_periods, db_path, state_file_path):
    """
    Function to iterate through time periods, then through multiple subject codes with recovery mechanism.
    
    Args:
        subject_codes: List of subject codes to search for
        time_periods: List of tuples (start_year, end_year) for time periods
        db_path: Path to the SQLite database file
        state_file_path: Path to the state file for recovery
    """
    max_retries = 3
    retry_count = 0
    
    # Initialize state manager
    state_manager = ScrapingState(state_file_path)
    
    # Create database directory
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
    
    # Print overview
    print("Time Period Cycling Scraper")
    print("===========================")
    print("This scraper will search through all keywords for each time period:")
    for i, (start_year, end_year) in enumerate(time_periods):
        print(f"  Period {i+1}: {start_year}-{end_year}")
    print(f"Total keywords per period: {len(subject_codes)}")
    print(f"Total searches to perform: {len(time_periods)} × {len(subject_codes)} = {len(time_periods) * len(subject_codes)}")
    print()
    
    while retry_count < max_retries:
        driver = None
        try:
            print(f"Starting scraping attempt {retry_count + 1}/{max_retries}")
            
            # Initialize the Chrome driver
            driver = initialize_driver()
            
            # Attempt recovery if this isn't the first try
            if retry_count > 0:
                print("Attempting recovery from previous state...")
                recovery_success, start_period_idx, start_subject_idx, start_page = attempt_recovery(
                    driver, state_manager, subject_codes, time_periods)
                if not recovery_success:
                    print("Recovery failed, starting fresh")
                    start_period_idx = 0
                    start_subject_idx = 0
                    start_page = 0
            else:
                start_period_idx = state_manager.state['current_period_index']
                start_subject_idx = state_manager.state['current_subject_index']
                start_page = state_manager.state['current_page']
            
            # Process time periods starting from recovery point
            for period_idx in range(start_period_idx, len(time_periods)):
                start_year, end_year = time_periods[period_idx]
                print(f"\n{'='*60}")
                print(f"PROCESSING TIME PERIOD {period_idx+1}/{len(time_periods)}: {start_year}-{end_year}")
                print(f"{'='*60}")
                
                # Skip if we've already completed this period
                if (start_year, end_year) in state_manager.state['completed_periods']:
                    print(f"Period {start_year}-{end_year} already completed, skipping...")
                    continue
                
                # Update state with current period
                state_manager.update_period_progress(period_idx, (start_year, end_year))
                
                # Determine which subject to start from for this period
                current_subject_start = start_subject_idx if period_idx == start_period_idx else 0
                
                # Process subjects starting from the recovery point
                for subject_idx in range(current_subject_start, len(subject_codes)):
                    subject_code = subject_codes[subject_idx]
                    print(f"\nProcessing subject {subject_idx+1}/{len(subject_codes)} in period {start_year}-{end_year}: {subject_code}")
                    
                    # Skip if we've already completed this subject in current period
                    if subject_code in state_manager.state['completed_subjects']:
                        print(f"Subject {subject_code} already completed in this period, skipping...")
                        continue
                    
                    # If this is a recovery and we're on the same subject and period, skip navigation
                    if (retry_count > 0 and period_idx == start_period_idx and 
                        subject_idx == start_subject_idx and start_page > 0):
                        print("Continuing from recovered state...")
                    else:
                        # Navigate to the advanced search page
                        navigate_to_advanced_search(driver)
                        
                        # Refine the search with the current subject code and time period
                        results_found = refine_search(driver, subject_code, language="CHI", 
                                                    start_year=str(start_year), end_year=str(end_year))
                        
                        if not results_found:
                            print(f"Skipping subject '{subject_code}' for period {start_year}-{end_year} - no search results found")
                            state_manager.complete_subject(subject_code)
                            continue
                        
                        start_page = 0  # Reset start page for new subjects
                    
                    try:
                        # Wait for the page to load
                        wait = WebDriverWait(driver, 30)
        
                        # Extract the total number of books in the search
                        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
                        total_info = element.text
                        print(f"Raw total info text: '{total_info}'")
        
                        # Look for the number after "Total"
                        match = re.search(r'Total\s+(\d+)', total_info)
                        if match:
                            tot_books = int(match.group(1))
                            print(f"Total number of books in category {subject_code} ({start_year}-{end_year}): {tot_books}")
                        else:
                            print(f"Pattern didn't match. Raw text: '{total_info}'")
                            tot_books = 0
                    
                        # Calculate total number of pages (20 books per page)
                        num_pages = math.ceil(tot_books / 20)
                        print(f"Total pages to scrape: {num_pages}")
                        
                        # Update state with subject progress
                        state_manager.update_subject_progress(subject_idx, subject_code, num_pages, tot_books)
                        
                        # Track total books saved for this subject
                        total_books_saved = 0
                        
                        # Iterate through all pages starting from the recovery point
                        for page in range(start_page, num_pages):
                            print(f"Scraping page {page+1}/{num_pages} of category {subject_code} ({start_year}-{end_year})")
                            
                            # Update state with current page
                            current_url = driver.current_url
                            state_manager.update_page_progress(page, current_url)
                            
                            # Wait for the book rows to load on the current page
                            wait = WebDriverWait(driver, 10)
                            book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
                            
                            # Use predefined function to extract info from books on the current page
                            books_data = extract_info_books(book_rows)
                            
                            # Save current page's data to database immediately with time period info
                            if save_page_data_to_db(books_data, subject_code, start_year, end_year, db_path, page+1):
                                total_books_saved += len(books_data)
                            
                            # Sleep to avoid having problems with the website
                            time.sleep(randint(1, 5))
                            
                            # If it's not the last page, go to the next page
                            if page < num_pages - 1:
                                try:
                                    next_button = wait.until(EC.element_to_be_clickable(
                                        (By.CSS_SELECTOR, "img[src$='f-next-page.gif'][alt='Next Page']")
                                    ))
                                    next_button.click()
                                    # Wait for the next page to load
                                    time.sleep(3)
                                except Exception as e:
                                    print(f"Could not navigate to next page: {e}")
                                    break
                        
                        print(f"Completed processing subject '{subject_code}' for period {start_year}-{end_year}: {total_books_saved} total books saved to database")
                        
                        # Mark subject as completed for this period
                        state_manager.complete_subject(subject_code)
                        start_page = 0  # Reset for next subject
                        
                    except Exception as e:
                        print(f"Error processing search results for subject '{subject_code}' in period {start_year}-{end_year}: {str(e)}")
                        raise  # Re-raise to trigger recovery
                
                # Mark this time period as completed
                state_manager.complete_period((start_year, end_year))
                print(f"\n{'='*60}")
                print(f"COMPLETED PERIOD {start_year}-{end_year}")
                if period_idx < len(time_periods) - 1:
                    next_start, next_end = time_periods[period_idx + 1]
                    print(f"Moving to next time period: {next_start}-{next_end}")
                print(f"{'='*60}")
                
                # Reset subject start index for subsequent periods
                start_subject_idx = 0
            
            # If we get here, all periods and subjects were processed successfully
            print("\n\n===== ALL TIME PERIODS COMPLETED SUCCESSFULLY! =====")
            state_manager.reset_state()  # Clear the state file
            break
            
        except KeyboardInterrupt:
            print("\nScraping interrupted by user")
            break
        except Exception as e:
            print(f"Error during scraping attempt {retry_count + 1}: {str(e)}")
            traceback.print_exc()
            retry_count += 1
            
            if retry_count < max_retries:
                print(f"Retrying in 10 seconds... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(10)
            else:
                print("Max retries reached. Scraping failed.")
        finally:
            # Close the driver if it was successfully initialized
            if driver:
                try:
                    driver.quit()
                    print("Browser closed")
                except:
                    pass

def generate_time_periods():
    """
    Generate the specific time periods for the Taiwan NCL scraper
    
    Returns:
        List of tuples (start_year, end_year)
    """
    periods = [
        (1900, 1915),
        (1915, 1930),
        (1930, 1945),
        (1945, 1960),
        (1960, 1975),
        (1975, 1990),
        (1990, 2005),
        (2005, 2020),
        (2020, 2023)
    ]
    
    return periods

def main_with_time_periods():
    """
    Main function that handles crash recovery automatically with time period cycling.
    """
    # Define the database path
    db_path = "../scraped_data/ncl_subject_books_time_periods.db"
    state_file_path = "../scraped_data/scraping_state_time_periods.json"
    
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
        "農業",      # Farming
        "釣魚",      # Fishing
        "林業",      # Forestry
        "鍛造作品",  # Forged works
        "燃料",      # Fuel
        "毛皮製品",  # Fur products
        "提供",      # Furnishing 
        "傢俱",      # Furnishings
        "硬體",      # Hardware
        "家政學",    # Home economics
        "家庭工作坊", # Home workshop
        "園藝",      # Horticulture
        "家用電器",  # Household appliances
        "工業",      # Industry
        "鐵",        # Iron
        "皮具",      # Leather goods
        "皮革加工",  # Leather processing
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
    
    # Generate the specific time periods for Taiwan NCL scraper
    time_periods = generate_time_periods()
    
    print("Enhanced Taiwan NCL Scraper with Time Period Cycling")
    print("=====================================================")
    print("Generated time periods:")
    for i, (start_year, end_year) in enumerate(time_periods):
        print(f"  Period {i+1}: {start_year}-{end_year}")
    print(f"Total keywords per period: {len(keywords)}")
    print(f"Total searches to perform: {len(time_periods)} × {len(keywords)} = {len(time_periods) * len(keywords)}")
    print()
    
    # Check for previous state
    state_manager = ScrapingState(state_file_path)
    
    if state_manager.state['current_period'] is not None:
        period_info = f"period {state_manager.state['current_period'][0]}-{state_manager.state['current_period'][1]}"
        subject_info = f"subject {state_manager.state['current_subject_index']+1}"
        page_info = f"page {state_manager.state['current_page']+1}"
        response = input(f"Found previous incomplete session. Resume from {period_info}, {subject_info}, {page_info}? (y/n): ")
        if response.lower() != 'y':
            print("Starting fresh session...")
            state_manager.reset_state()
        else:
            print("Resuming previous session...")
    
    # Run the scraper with time period cycling
    scrape_multiple_subjects_with_time_periods(keywords, time_periods, db_path, state_file_path)

# Legacy function maintained for compatibility - now uses time period cycling by default
def scrape_multiple_subjects(subject_codes, db_path):
    """
    Legacy function maintained for compatibility - now uses time period cycling
    """
    state_file_path = os.path.join(os.path.dirname(db_path), "scraping_state.json")
    time_periods = generate_time_periods()
    scrape_multiple_subjects_with_time_periods(subject_codes, time_periods, db_path, state_file_path)

# Call this function with time period cycling
if __name__ == "__main__":
    main_with_time_periods()