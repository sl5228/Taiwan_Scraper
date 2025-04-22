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


def refine_search(driver, subject_term, language="CHI", start_year="1950", end_year="1970"):
    """
    Function to refine the search on the advanced search page.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_term: The subject term to search for
        language: The language to filter by (default: "CHI" for Chinese)
        start_year: The starting year for publication date filter (default: "1950")
        end_year: The ending year for publication date filter (default: "1970")
    
    Returns:
        None
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
            
            # Check for an element with class "td2" containing an anchor tag with "set_number" in href
            # This pattern matches the example HTML you provided
            result_link = driver.find_elements(By.XPATH, 
                "//td[contains(@class, 'td2')]//a[contains(@href, 'set_number')]")

            if result_link and len(result_link) > 0:
                print("Yes - Found clickable element with result count")
                
                # Click the link to navigate to the full results
                result_link[0].click()
                print("Navigated to the full results page")
                
                # Wait for the full results page to load
                time.sleep(5)
            else:
                print("No - Did not find clickable element with result count")
                
        except Exception as e:
            print(f"Error checking for result link: {str(e)}")
            print("No - Element not found due to error")
        
        # No need to return anything
        
    except Exception as e:
        print(f"Error during search refinement: {str(e)}")
        raise

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
        print(f"Found first book title: '{title}'")
        print(f"URL: {url}")
        
        # Click on the title link
        first_title_link.click()
        print("Clicked on the first book title")
        
        # Wait for the book details page to load
        time.sleep(3)
        
        # Get the current URL after clicking
        current_url = driver.current_url
        print(f"Current URL after clicking: {current_url}")
        
        return True
        
    except Exception as e:
        print(f"Error clicking first book title: {str(e)}")
        return False

def process_book_details(driver, subject_code):
    """
    Function to extract specific information from the book details page.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_code: The subject code used for the search
    
    Returns:
        dict: The extracted book details
    """
    try:
        # Wait for the page to load
        time.sleep(2)
        wait = WebDriverWait(driver, 10)
        
        # Print the current URL
        current_url = driver.current_url
        print(f"Processing book details at URL: {current_url}")
        
        # Initialize a dictionary to store the extracted information
        book_info = {
            'subject': subject_code,
            'url': current_url,
            'record_number': "missing",
            'title': "missing",
            'language': "missing",
            'imprint': "missing"  # publication info
        }
        
        # Extract record number
        try:
            record_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Record Number')]/following-sibling::td")
            book_info['record_number'] = record_row.text.strip()
            print(f"Record Number: {book_info['record_number']}")
        except Exception as e:
            print(f"Record number field not found, using 'missing'")
        
        # Extract title
        try:
            title_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Title')]/following-sibling::td")
            # The title is in an anchor tag
            title_link = title_row.find_element(By.TAG_NAME, "a")
            book_info['title'] = title_link.text.strip()
            print(f"Title: {book_info['title']}")
        except Exception as e:
            print(f"Title field not found, using 'missing'")
        
        # Extract language
        try:
            language_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Language')]/following-sibling::td")
            book_info['language'] = language_row.text.strip()
            print(f"Language: {book_info['language']}")
        except Exception as e:
            print(f"Language field not found, using 'missing'")
        
        # Extract imprint (publication info)
        try:
            imprint_row = driver.find_element(By.XPATH, "//td[@class='td1' and @id='bold' and contains(text(), 'Imprint')]/following-sibling::td")
            book_info['imprint'] = imprint_row.text.strip()
            print(f"Imprint: {book_info['imprint']}")
        except Exception as e:
            print(f"Imprint field not found, using 'missing'")
        
        # Return the extracted information
        print("Book details extracted successfully")
        print(book_info)
        
        return book_info
        
    except Exception as e:
        print(f"Error processing book details: {str(e)}")        
        # Return a dictionary with default values
        return {
            'subject': subject_code,
            'url': driver.current_url if 'driver' in locals() else "error",
            'record_number': "missing",
            'title': "missing",
            'language': "missing",
            'imprint': "missing"
        }

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
        print("Clicked on 'Next Record' button")
        
        # Wait for the next book details page to load
        time.sleep(3)
        
        # Get the current URL after clicking
        current_url = driver.current_url
        print(f"Navigated to next book at URL: {current_url}")
        
        return True
    except Exception as e:
        print(f"Error navigating to next book: {str(e)}")
        return False

def process_all_books_for_subject(driver, subject_code):
    """
    Function to process all books for a specific subject.
    This function starts from the search results page, clicks on the first book,
    extracts its information, then navigates through all remaining books.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_code: The subject code used for the search
    
    Returns:
        list: List of dictionaries containing extracted book information
    """
    books_info = []
    
    # Click on the first book title to view its details
    if click_first_book_title(driver):
        # Process the first book
        book_info = process_book_details(driver, subject_code)
        if book_info:
            books_info.append(book_info)
            print(f"Added information for book 1 in subject '{subject_code}' to results")
        
        # Process all remaining books
        book_count = 1
        while has_next_book(driver):
            # Navigate to the next book
            if navigate_to_next_book(driver):
                book_count += 1
                # Process the current book
                book_info = process_book_details(driver, subject_code)
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
        print("Navigated back to the main search page")
        time.sleep(2)
    except Exception as e:
        print(f"Error returning to main search page: {str(e)}")
    
    return books_info

def explore_subjects_and_all_books(subject_codes, db_path):
    """
    Function to iterate through multiple subject codes, perform a search for each,
    process all books in the results for each subject, and save to a database.
    
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
        
        # Check if the database exists and create a new one if needed
        db_exists = os.path.exists(db_path)
        if db_exists:
            print(f"Database already exists at {db_path}")
            # Rename the existing database to back it up
            backup_path = db_path + ".backup"
            os.rename(db_path, backup_path)
            print(f"Renamed existing database to {backup_path}")
            print(f"Creating a new database at {db_path}")
        
        # Initialize a list to store all book information
        all_book_info = []
        
        # Loop through each subject code
        for i, subject_code in enumerate(subject_codes):
            print(f"\nProcessing subject {i+1}/{len(subject_codes)}: {subject_code}")
            
            # Navigate to the advanced search page
            navigate_to_advanced_search(driver)
            
            # Refine the search with the current subject code
            refine_search(driver, subject_code, language="CHI", start_year="1950", end_year="1970")

            # Wait for the page to load
            wait = WebDriverWait(driver, 30)

            # Extract the total number of books in the search
            try:
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
                total_info = element.text
                print(f"Raw total info text: '{total_info}'")

                # Look for the number after "Total"
                match = re.search(r'Total\s+(\d+)', total_info)
                if match:
                    tot_books = int(match.group(1))
                    print(f"Total number of books in category {subject_code}: {tot_books}")
                else:
                    print(f"Pattern didn't match. Raw text: '{total_info}'")
                    tot_books = 0  # Default to 0 if we can't extract the number
            except Exception as e:
                print(f"Error extracting total book count: {str(e)}")
                tot_books = 0
            
            # If books were found for this subject
            if tot_books > 0:
                # Process all books for this subject
                subject_books = process_all_books_for_subject(driver, subject_code)
                
                # Save the books for this subject to the database
                if subject_books:
                    # Convert the list of dictionaries to a DataFrame
                    books_df = pd.DataFrame(subject_books)
                    
                    # Connect to the SQLite database
                    conn = sqlite3.connect(db_path)
                    
                    # Save the DataFrame to the database, appending if the table exists
                    books_df.to_sql('books', conn, if_exists='append', index=False)
                    
                    # Close the connection
                    conn.close()
                    
                    print(f"Successfully saved {len(subject_books)} books for subject '{subject_code}' to database")
                    
                    # Add to the master list
                    all_book_info.extend(subject_books)
                    print(f"Added {len(subject_books)} books from subject '{subject_code}' to results")
            else:
                print(f"No books found for subject '{subject_code}'")
            
            # Sleep to avoid having problems with the website
            time.sleep(randint(1, 3))
            
            # Let user know we're moving to the next subject automatically
            if i < len(subject_codes) - 1:
                print(f"\nMoving to the next subject: {subject_codes[i+1]}")
            else:
                print("\nAll subjects have been processed.")
        
        # Print the final results
        print("\n\n===== EXTRACTED BOOK INFORMATION =====")
        print(f"Total books extracted and saved to database: {len(all_book_info)}")
        
        # Print a sample of the first 10 books
        for i, book in enumerate(all_book_info[:10]):  # Print first 10 books for preview
            print(f"\nBook {i+1}:")
            for key, value in book.items():
                print(f"  {key}: {value}")
        
        if len(all_book_info) > 10:
            print(f"\n... and {len(all_book_info) - 10} more books saved to database")
        
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
        "會計學",    # Accounting
        "農業",      # Agriculture
        "農學",      # Agronomy
        "畜牧業",    # Animal husbandry
        "應用作",    # Applied works
        "應用物理學", # Applied physics
        "水生結構",  # Aquatic structures
        "建築",      # Architecture/Construction
        "育種",      # Breeding
        "商業材料",  # Business materials
        "商業組織",  # Business organizations
        "通信",      # Communication
        "建設",      # Construction
        "彈性計",    # Elastic planning
        "工程",      # Engineering
        "炸藥",      # Explosives
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
        "皮革加工",  # Leather processing
        "木材加工",  # Wood processing
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
        "乳製品加工", # Dairy processing
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
    
    # Run the program with the subject list and database path
    book_results = explore_subjects_and_all_books(keywords, db_path)