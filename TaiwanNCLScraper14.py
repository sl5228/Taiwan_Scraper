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

class CombinedScrapingState:
    """Class to manage scraping state for recovery purposes with special Management handling"""
    
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
        """Get the default state structure"""
        return {
            'phase': 'regular',  # 'regular' or 'management_periods'
            'regular_subjects_completed': False,
            'current_subject_index': 0,
            'current_page': 0,
            'current_subject': None,
            'total_pages': 0,
            'completed_subjects': [],
            'last_url': None,
            'total_books_in_subject': 0,
            # Management period-specific fields
            'current_period_index': 0,
            'current_period': None,
            'completed_periods': [],
            'management_subjects_for_period': []
        }
    
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
        """Mark a subject as completed"""
        if subject not in self.state['completed_subjects']:
            self.state['completed_subjects'].append(subject)
        self.save_state()
    
    def complete_regular_phase(self):
        """Mark regular subjects phase as completed"""
        self.state['regular_subjects_completed'] = True
        self.state['phase'] = 'management_periods'
        self.save_state()
    
    def update_management_period_progress(self, period_index, period_tuple):
        """Update progress for Management time periods"""
        self.state['current_period_index'] = period_index
        self.state['current_period'] = period_tuple
        self.state['current_page'] = 0
        self.save_state()
    
    def complete_management_period(self, period_tuple):
        """Mark a Management time period as completed"""
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
    """Navigate directly to a specific URL for recovery purposes"""
    try:
        driver.get(url)
        print(f"Successfully navigated to URL: {url}")
        time.sleep(3)  # Wait for page to load
        return True
    except Exception as e:
        print(f"Error navigating to URL {url}: {e}")
        return False

def refine_search(driver, subject_term, language="CHI", start_year="1900", end_year="2023"):
    """
    Function to refine the search on the advanced search page.
    """
    try:
        wait = WebDriverWait(driver, 30)
        
        # Select the Subject option from dropdown
        subject_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "find_code")))
        subject_select = Select(subject_dropdown)
        subject_select.select_by_value("WSU")
        print("Selected Subject option from dropdown")
        
        # Enter the subject term in the search input
        search_input = wait.until(EC.presence_of_element_located((By.NAME, "request")))
        search_input.clear()
        search_input.send_keys(subject_term)
        print(f"Entered subject term: {subject_term}")
        
        # Select radio button
        try:
            adjacent_radio = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "input[name='adjacent1'][value='N']")
            ))
            adjacent_radio.click()
            time.sleep(1)
            
            if not adjacent_radio.is_selected():
                driver.execute_script("arguments[0].click();", adjacent_radio)
                time.sleep(1)
                print("Selected 'N' radio button using JavaScript")
            else:
                print("Selected 'N' radio button")
                
        except Exception as radio_error:
            print(f"Error with radio button: {str(radio_error)}")
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
        
        # Enter the start year
        start_year_input = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_2")))
        start_year_input.clear()
        start_year_input.send_keys(start_year)
        print(f"Entered start year: {start_year}")
        
        # Enter the end year
        end_year_input = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_3")))
        end_year_input.clear()
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
        
        # Check for results
        try:
            time.sleep(2)
            short_wait = WebDriverWait(driver, 5)
            
            result_link = short_wait.until(EC.presence_of_element_located(
                (By.XPATH, "//td[contains(@class, 'td2')]//a[contains(@href, 'set_number')]")
            ))

            print("Found clickable element with result count")
            result_link.click()
            print("Navigated to the full results page")
            time.sleep(5)
            return True
                
        except Exception as e:
            print("No search results found")
            return False
        
    except Exception as e:
        print(f"Error during search refinement: {str(e)}")
        return False

def navigate_to_page(driver, target_page, current_page=0):
    """Navigate to a specific page number"""
    try:
        wait = WebDriverWait(driver, 10)
        
        if target_page == current_page:
            print(f"Already on target page {target_page + 1}")
            return True
        
        pages_to_navigate = target_page - current_page
        
        if pages_to_navigate > 0:
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
            print("Backward navigation not implemented")
            return False
        
        print(f"Successfully navigated to page {target_page + 1}")
        return True
        
    except Exception as e:
        print(f"Error navigating to page {target_page + 1}: {e}")
        return False

def extract_info_books(book_rows):
    """Extract book information from the current page"""
    books_data = []
    
    for row in book_rows:
        try:
            # Extract title and URL
            title_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(3) a.brieftit")
            title = title_element.text
            url = title_element.get_attribute('href')
        
            # Extract author
            author_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(4)")
            author = author_element.text
        
            # Extract publisher
            publisher_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(5)")
            publisher = publisher_element.text
        
            # Extract year of publication
            year_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(6)")
            year_script = year_element.get_attribute('innerHTML')
            
            # Debug first row
            if books_data == []:
                print(f"Sample year_script: {year_script[:100]}...")
            
            year_match = re.search(r'</script>\s*(\d{4})', year_script)
            if year_match:
                year = year_match.group(1)
            else:
                alt_match = re.search(r'(\d{4})', year_script)
                if alt_match:
                    year = alt_match.group(1)
                else:
                    year = "Unknown"
                        
            # Extract call number
            call_number_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(7)")
            call_number = call_number_element.text.strip() if call_number_element.text.strip() else None
        
            books_data.append({
                'title': title,
                'url': url,
                'author': author,
                'publisher': publisher,
                'year': year,
                'call_number': call_number,
            })
        except Exception as e:
            print(f"Error extracting information from a book row: {str(e)}")
            continue
            
    return books_data

def save_page_data_to_db(books_data, subject_code, db_path, page_num, start_year=None, end_year=None):
    """
    Function to save a single page's worth of book data to the database.
    Only saves: title, url, author, publisher, year, call_number, and subject
    """
    try:
        if books_data:
            books_df = pd.DataFrame(books_data)
            books_df['subject'] = subject_code
            
            # Ensure we only keep the required columns
            required_columns = ['title', 'url', 'author', 'publisher', 'year', 'call_number', 'subject']
            books_df = books_df[required_columns]
            
            conn = sqlite3.connect(db_path)
            books_df.to_sql('books', conn, if_exists='append', index=False)
            conn.close()
            
            period_info = f" (period {start_year}-{end_year})" if start_year else ""
            print(f"Successfully saved {len(books_df)} books from page {page_num}{period_info} to database")
            return True
        else:
            print(f"No book data to save for page {page_num}")
            return False
            
    except Exception as e:
        print(f"Error saving page {page_num} data to database: {str(e)}")
        return False

def generate_management_time_periods():
    """Generate the 15-year time periods for Management scraping"""
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

def scrape_regular_subjects(driver, subject_codes, db_path, state_manager, start_index=0):
    """Scrape all regular subjects (excluding Management) with 1900-2023 range"""
    
    print("\n" + "="*60)
    print("PHASE 1: REGULAR SUBJECTS (1900-2023)")
    print("="*60)
    
    # Filter out Management from the list
    regular_subjects = [s for s in subject_codes if s != "管理"]
    print(f"Regular subjects to process: {len(regular_subjects)}")
    
    for i in range(start_index, len(regular_subjects)):
        subject_code = regular_subjects[i]
        print(f"\nProcessing regular subject {i+1}/{len(regular_subjects)}: {subject_code}")
        
        if subject_code in state_manager.state['completed_subjects']:
            print(f"Subject {subject_code} already completed, skipping...")
            continue
        
        # Navigate to advanced search page
        navigate_to_advanced_search(driver)
        
        # Refine the search (1900-2023 for regular subjects)
        results_found = refine_search(driver, subject_code, language="CHI", start_year="1900", end_year="2023")
        
        if not results_found:
            print(f"Skipping subject '{subject_code}' - no search results found")
            state_manager.complete_subject(subject_code)
            continue
        
        try:
            wait = WebDriverWait(driver, 30)
            
            # Extract total number of books
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
            total_info = element.text
            print(f"Raw total info text: '{total_info}'")
            
            match = re.search(r'Total\s+(\d+)', total_info)
            if match:
                tot_books = int(match.group(1))
                print(f"Total number of books in category {subject_code}: {tot_books}")
            else:
                print(f"Pattern didn't match. Raw text: '{total_info}'")
                tot_books = 0
            
            # Calculate total pages
            num_pages = math.ceil(tot_books / 20)
            print(f"Total pages to scrape: {num_pages}")
            
            # Update state
            state_manager.update_subject_progress(i, subject_code, num_pages, tot_books)
            
            total_books_saved = 0
            
            # Process all pages
            for page in range(num_pages):
                print(f"Scraping page {page+1}/{num_pages} of category {subject_code}")
                
                # Update state with current page
                current_url = driver.current_url
                state_manager.update_page_progress(page, current_url)
                
                # Extract books from current page
                wait = WebDriverWait(driver, 10)
                book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
                
                books_data = extract_info_books(book_rows)
                
                # Save to database
                if save_page_data_to_db(books_data, subject_code, db_path, page+1):
                    total_books_saved += len(books_data)
                
                time.sleep(randint(1, 5))
                
                # Navigate to next page
                if page < num_pages - 1:
                    try:
                        next_button = wait.until(EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "img[src$='f-next-page.gif'][alt='Next Page']")
                        ))
                        next_button.click()
                        time.sleep(3)
                    except Exception as e:
                        print(f"Could not navigate to next page: {e}")
                        break
            
            print(f"Completed processing subject '{subject_code}': {total_books_saved} total books saved")
            state_manager.complete_subject(subject_code)
            
        except Exception as e:
            print(f"Error processing subject '{subject_code}': {str(e)}")
            raise

def scrape_management_periods(driver, db_path, state_manager, start_period_index=0):
    """Scrape Management subject using 15-year time periods"""
    
    print("\n" + "="*60)
    print("PHASE 2: MANAGEMENT BY TIME PERIODS")
    print("="*60)
    
    time_periods = generate_management_time_periods()
    print(f"Time periods to process: {len(time_periods)}")
    
    for period_idx in range(start_period_index, len(time_periods)):
        start_year, end_year = time_periods[period_idx]
        print(f"\nProcessing Management period {period_idx+1}/{len(time_periods)}: {start_year}-{end_year}")
        
        # Skip if already completed
        if (start_year, end_year) in state_manager.state['completed_periods']:
            print(f"Period {start_year}-{end_year} already completed, skipping...")
            continue
        
        # Update state
        state_manager.update_management_period_progress(period_idx, (start_year, end_year))
        
        # Navigate to advanced search page
        navigate_to_advanced_search(driver)
        
        # Search for Management in this time period
        results_found = refine_search(driver, "管理", language="CHI", 
                                    start_year=str(start_year), end_year=str(end_year))
        
        if not results_found:
            print(f"No results found for Management in period {start_year}-{end_year}")
            state_manager.complete_management_period((start_year, end_year))
            continue
        
        try:
            wait = WebDriverWait(driver, 30)
            
            # Extract total number of books
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
            total_info = element.text
            print(f"Raw total info text: '{total_info}'")
            
            match = re.search(r'Total\s+(\d+)', total_info)
            if match:
                tot_books = int(match.group(1))
                print(f"Total Management books in period {start_year}-{end_year}: {tot_books}")
            else:
                tot_books = 0
            
            # Calculate total pages
            num_pages = math.ceil(tot_books / 20)
            print(f"Total pages to scrape: {num_pages}")
            
            total_books_saved = 0
            
            # Process all pages for this time period
            for page in range(num_pages):
                print(f"Scraping page {page+1}/{num_pages} of Management ({start_year}-{end_year})")
                
                # Update state
                current_url = driver.current_url
                state_manager.update_page_progress(page, current_url)
                
                # Extract books from current page
                wait = WebDriverWait(driver, 10)
                book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
                
                books_data = extract_info_books(book_rows)
                
                # Save to database with period information
                if save_page_data_to_db(books_data, "管理", db_path, page+1, start_year, end_year):
                    total_books_saved += len(books_data)
                
                time.sleep(randint(1, 5))
                
                # Navigate to next page
                if page < num_pages - 1:
                    try:
                        next_button = wait.until(EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "img[src$='f-next-page.gif'][alt='Next Page']")
                        ))
                        next_button.click()
                        time.sleep(3)
                    except Exception as e:
                        print(f"Could not navigate to next page: {e}")
                        break
            
            print(f"Completed Management period {start_year}-{end_year}: {total_books_saved} books saved")
            state_manager.complete_management_period((start_year, end_year))
            
        except Exception as e:
            print(f"Error processing Management period {start_year}-{end_year}: {str(e)}")
            raise

def scrape_combined_approach(subject_codes, db_path, state_file_path):
    """
    Main function that combines regular scraping for most subjects and 
    time-period scraping for Management
    """
    max_retries = 3
    retry_count = 0
    
    # Initialize state manager
    state_manager = CombinedScrapingState(state_file_path)
    
    # Create directories
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
    
    print("Combined Taiwan NCL Scraper")
    print("===========================")
    print("Phase 1: Regular subjects (1900-2023)")
    print("Phase 2: Management by 15-year periods")
    print()
    
    while retry_count < max_retries:
        driver = None
        try:
            print(f"Starting scraping attempt {retry_count + 1}/{max_retries}")
            
            driver = initialize_driver()
            
            # Phase 1: Regular subjects (exclude Management)
            if not state_manager.state['regular_subjects_completed']:
                print("Starting/Resuming Phase 1: Regular subjects...")
                start_subject_index = state_manager.state['current_subject_index']
                scrape_regular_subjects(driver, subject_codes, db_path, state_manager, start_subject_index)
                state_manager.complete_regular_phase()
                print("\nPhase 1 completed! Moving to Phase 2...")
            else:
                print("Phase 1 already completed, proceeding to Phase 2...")
            
            # Phase 2: Management with time periods
            if state_manager.state['phase'] == 'management_periods':
                print("Starting/Resuming Phase 2: Management by time periods...")
                start_period_index = state_manager.state['current_period_index']
                scrape_management_periods(driver, db_path, state_manager, start_period_index)
            
            # If we get here, both phases completed successfully
            print("\n" + "="*60)
            print("ALL PHASES COMPLETED SUCCESSFULLY!")
            print("="*60)
            state_manager.reset_state()
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
            if driver:
                try:
                    driver.quit()
                    print("Browser closed")
                except:
                    pass

def main():
    """Main function with user interaction for recovery"""
    # Define paths
    db_path = "../scraped_data/ncl_combined_scraping.db"
    state_file_path = "../scraped_data/combined_scraping_state.json"
    
    # Define all keywords
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
        "運輸",      # Transportation
        "水結構",    # Water structures
    ]
    
    # Check for previous state
    state_manager = CombinedScrapingState(state_file_path)
    
    if state_manager.state['current_subject'] is not None or state_manager.state['current_period'] is not None:
        phase = state_manager.state['phase']
        if phase == 'regular':
            subject_info = f"regular subject {state_manager.state['current_subject_index']+1}"
            page_info = f"page {state_manager.state['current_page']+1}"
            response = input(f"Found incomplete session in Phase 1 ({subject_info}, {page_info}). Resume? (y/n): ")
        else:
            period_info = f"Management period {state_manager.state['current_period_index']+1}"
            page_info = f"page {state_manager.state['current_page']+1}"
            response = input(f"Found incomplete session in Phase 2 ({period_info}, {page_info}). Resume? (y/n): ")
        
        if response.lower() != 'y':
            print("Starting fresh session...")
            state_manager.reset_state()
        else:
            print("Resuming previous session...")
    
    # Print summary
    regular_subjects = [s for s in keywords if s != "管理"]
    management_periods = generate_management_time_periods()
    
    print(f"\nScraping Plan:")
    print(f"Phase 1 - Regular subjects: {len(regular_subjects)} subjects (1900-2023)")
    print(f"Phase 2 - Management periods: {len(management_periods)} time periods")
    print(f"Total estimated searches: {len(regular_subjects)} + {len(management_periods)} = {len(regular_subjects) + len(management_periods)}")
    print()
    
    # Run the combined scraper
    scrape_combined_approach(keywords, db_path, state_file_path)

if __name__ == "__main__":
    main()