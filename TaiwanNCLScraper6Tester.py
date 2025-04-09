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


def refine_search(driver, subject_term, language="CHI", start_year="1500", end_year="2023"):
    """
    Function to refine the search on the advanced search page.
    
    Args:
        driver: The Selenium WebDriver instance
        subject_term: The subject term to search for
        language: The language to filter by (default: "CHI" for Chinese)
        start_year: The starting year for publication date filter (default: "1500")
        end_year: The ending year for publication date filter (default: "2023")
    
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

def extract_info_books(book_rows):
    # Initialize a list to store book information
    books_data = []
    
    # Extract information for each book
    for row in book_rows:
        try:
            # Extract title
            title_element = row.find_element(By.CSS_SELECTOR, "td.td1:nth-child(3) a.brieftit")
            title = title_element.text
        
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

def scrape_multiple_subjects(subject_codes, db_path):
    """
    Function to iterate through multiple subject codes, perform a search for each,
    extract all book information, and save to a database.
    
    Args:
        subject_codes: List of subject codes to search for
        db_path: Path to the SQLite database file
    """
    try:
        print("Initializing Chrome WebDriver...")
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome()
        
        print("WebDriver initialized successfully")
        
        # Create the directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Loop through each subject code
        for i, subject_code in enumerate(subject_codes):
            print(f"\nProcessing subject {i+1}/{len(subject_codes)}: {subject_code}")
            
            # Navigate to the advanced search page
            navigate_to_advanced_search(driver)
            
            # Refine the search with the current subject code
            refine_search(driver, subject_code, language="CHI", start_year="1500", end_year="2023")

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
                print(f"Total number of books in category {subject_code}: {tot_books}")
            else:
                print(f"Pattern didn't match. Raw text: '{total_info}'")
                tot_books = 0  # Default to 0 if we can't extract the number
            
            # Calculate total number of pages (20 books per page)
            num_pages = math.ceil(tot_books / 20)
            print(f"Total pages to scrape: {num_pages}")
            
            # Initialize a master list to store all books across pages
            all_books_data = []
            
            # Iterate through all pages
            for page in range(0, num_pages):
                print(f"Scraping page {page+1}/{num_pages} of category {subject_code}")
                
                # Wait for the book rows to load on the current page
                wait = WebDriverWait(driver, 10)
                book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
                
                # Use predefined function to extract info from books on the current page
                books_data = extract_info_books(book_rows)
                
                # Append current page's data to the master list
                all_books_data.extend(books_data)
                
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
            
            # Save books into a dataframe
            books_df = pd.DataFrame(all_books_data)
            
            # Add subject term to the dataframe
            books_df['subject'] = subject_code
            
            print(f"Extracted {len(books_df)} books for subject '{subject_code}'")
            
            # Connect to the SQLite database (creates it if it doesn't exist)
            conn = sqlite3.connect(db_path)
            
            # Save the DataFrame to the database, appending if the table exists
            books_df.to_sql('books', conn, if_exists='append', index=False)
            
            # Close the connection
            conn.close()
            
            print(f"Successfully saved data for subject '{subject_code}' to database")
            
            # If this is not the last subject, ask for confirmation before continuing
            if i < len(subject_codes) - 1:
                user_input = input(f"\nPress Enter to continue to the next subject ({subject_codes[i+1]}) or type 'exit' to stop: ")
                if user_input.lower() == 'exit':
                    print("Exiting the program as requested.")
                    break
            else:
                print("\nAll subjects have been processed.")
                
        input("Press Enter to close the browser...")
    
    except Exception as e:
        print(f"Error during subject scraping: {str(e)}")
        import traceback
        traceback.print_exc()
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
    db_path = "../scraped_data/ncl_subject_books.db"
    
    # Define the list of Chinese keywords
    keywords = [
        "冶金",   #Metallurgy
        "紡織品", #Textiles
        "育種",   #Breeding
        "應用作", #Applied Operations
        "釣魚",   #Fishing
        "農學",   #Agronomy
        "硬體",   #Hardware
        "公共關係", #Public Relations
        "藥理學",  #Pharmacology
        "林業",   #Forestry
        "製造業",  #Manufacturing
    ]
    # Run the scraper with the subject list and database path
    scrape_multiple_subjects(keywords, db_path)


