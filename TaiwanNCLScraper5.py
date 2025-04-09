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

# Extract the information of books
def extract_info_books(book_rows):
        # Initialize a list to store book information
        books_data = []
        
        # Extract information for each book
        for row in book_rows:
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
            year = re.search(r'</script>\s*(\d{4})', year_script).group(1)
                        
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
        return(books_data)

def scrape_multiple_subjects(subject_codes):
    """
    Function to iterate through multiple subject codes and perform a search for each.
    User confirmation is required between each search.
    
    Args:
        subject_codes: List of subject codes to search for
    """
    try:
        print("Initializing Chrome WebDriver...")
        
        # Initialize the Chrome driver
        driver = webdriver.Chrome()
        
        print("WebDriver initialized successfully")
        
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
            
            # Look for the total number of books in the search based on pattern of the text       
            tot_books = int(re.search(r'of (\d+) 筆', total_info))
        
            # Print total number of books
            print(f"Total number of books in category {subject_code}: {tot_books}")
            
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
    
    # Run the scraper with the subject list
    scrape_multiple_subjects(keywords)


