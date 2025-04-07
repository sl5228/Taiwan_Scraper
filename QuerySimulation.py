#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extension of TaiwanNCLScraper to use Advanced Search with specific keywords
This script performs the following steps:
1. Navigates to the National Library Catalogue Advanced Search page
2. Sets specific search filters:
   - Subject as the field to search
   - Language: Chinese
   - Date: 1500-2023
   - Words Adjacent turned off
   - Material Type: Book
   - Collection: All
3. Searches for a specific keyword from a given list
4. Extracts book information from the results

@author: Research Assistant
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import re
import pandas as pd
import math
import sqlite3
from random import randint
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='ncl_scraper.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

def advanced_search(driver, keyword, wait):
    """
    Navigate to the Advanced Search page and set up the search with specific filters
    
    Parameters:
    driver (webdriver): Selenium webdriver instance
    keyword (str): The keyword to search for
    wait (WebDriverWait): WebDriverWait instance for handling element loading
    """
    try:
        # Navigate to the National Central Library website directly to the advanced search page
        base_url = "https://aleweb.ncl.edu.tw/F/NMXR8CKBVFDXPRNNBJ8H93VNXF78YD5T3X9IYJSJSTGRKDYT8E-16332?func=find-a"
        driver.get(base_url)
        logger.info(f"Navigated to the advanced search URL directly")
        
        # Take a screenshot to debug what we're seeing
        driver.save_screenshot("advanced_search_page.png")
        logger.info("Saved screenshot of the advanced search page")
        
        # Wait for the page to load - looking for the search input field
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='request']")))
        
        # Print the HTML of the page to the log for debugging
        logger.info("Page HTML structure:")
        logger.info(driver.page_source[:1000])  # First 1000 chars to avoid huge logs
        
        # Enter the keyword in the search field
        search_input = driver.find_element(By.CSS_SELECTOR, "input[name='request']")
        search_input.clear()
        search_input.send_keys(keyword)
        logger.info(f"Entered keyword: {keyword}")
        
        # Try to find available form elements and log their names/ids
        form_elements = driver.find_elements(By.CSS_SELECTOR, "select, input")
        logger.info("Available form elements:")
        for elem in form_elements:
            elem_name = elem.get_attribute("name")
            elem_id = elem.get_attribute("id")
            elem_type = elem.get_attribute("type")
            logger.info(f"Element: name={elem_name}, id={elem_id}, type={elem_type}")
        
        # Select 'Subject' as the field to search - try different selector methods
        try:
            # First attempt: by name
            field_select = Select(driver.find_element(By.NAME, "find_code"))
            field_select.select_by_value("WRD")
            logger.info("Selected Subject field by name='find_code'")
        except:
            try:
                # Second attempt: by more general CSS selector
                field_selects = driver.find_elements(By.CSS_SELECTOR, "select")
                for select_elem in field_selects:
                    if "code" in select_elem.get_attribute("name").lower():
                        field_select = Select(select_elem)
                        field_select.select_by_value("WRD")
                        logger.info("Selected Subject field by finding select with 'code' in name")
                        break
            except Exception as e:
                logger.warning(f"Could not set search field type: {e}")
        
        # Try to set Chinese language - attempt multiple approaches
        try:
            # First try by name
            language_elements = driver.find_elements(By.CSS_SELECTOR, "select")
            for elem in language_elements:
                elem_name = elem.get_attribute("name")
                if elem_name and ("lang" in elem_name.lower() or "language" in elem_name.lower()):
                    language_select = Select(elem)
                    try:
                        language_select.select_by_value("CHI")
                        logger.info(f"Set language to Chinese using element with name: {elem_name}")
                        break
                    except:
                        try:
                            # Try visible text if value doesn't work
                            language_select.select_by_visible_text("Chinese")
                            logger.info("Set language to Chinese by visible text")
                            break
                        except Exception as e:
                            logger.warning(f"Could not select language by visible text: {e}")
        except Exception as e:
            logger.warning(f"Could not set language to Chinese: {e}")
        
        # Set Date range: 1500-2023 - try to find year input fields
        year_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        year_fields_set = False
        
        for i, input_elem in enumerate(year_inputs):
            input_name = input_elem.get_attribute("name")
            if input_name and ("year" in input_name.lower() or "date" in input_name.lower()):
                if not year_fields_set:
                    try:
                        input_elem.clear()
                        input_elem.send_keys("1500")
                        logger.info(f"Set start year using element with name: {input_name}")
                        
                        # Look for the next input field for end year
                        if i + 1 < len(year_inputs):
                            next_input = year_inputs[i + 1]
                            next_input.clear()
                            next_input.send_keys("2023")
                            logger.info("Set end year to 2023")
                            year_fields_set = True
                    except Exception as e:
                        logger.warning(f"Could not set year range: {e}")
        
        # Set Material Type to Book - try to find the right selector
        try:
            material_selects = driver.find_elements(By.CSS_SELECTOR, "select")
            for select_elem in material_selects:
                select_name = select_elem.get_attribute("name")
                if select_name and ("material" in select_name.lower() or "type" in select_name.lower()):
                    material_select = Select(select_elem)
                    try:
                        material_select.select_by_value("BK")
                        logger.info(f"Set material type to Book using element with name: {select_name}")
                        break
                    except:
                        try:
                            material_select.select_by_visible_text("Book")
                            logger.info("Set material type to Book by visible text")
                            break
                        except Exception as e:
                            logger.warning(f"Could not select material type: {e}")
        except Exception as e:
            logger.warning(f"Could not set material type to Book: {e}")
        
        # Try to find and click the search/submit button
        submit_buttons = driver.find_elements(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
        submit_clicked = False
        
        for button in submit_buttons:
            button_value = button.get_attribute("value")
            button_text = button.text
            
            if button_value and ("search" in button_value.lower() or "submit" in button_value.lower()) or \
               button_text and ("search" in button_text.lower() or "submit" in button_text.lower()):
                button.click()
                logger.info(f"Clicked submit button with value/text: {button_value or button_text}")
                submit_clicked = True
                break
        
        if not submit_clicked:
            # Try a more generic approach - just click the first submit button
            for button in submit_buttons:
                try:
                    button.click()
                    logger.info("Clicked first available submit button")
                    submit_clicked = True
                    break
                except:
                    continue
        
        if not submit_clicked:
            logger.error("Could not find any submit button to click")
            raise Exception("No submit button found")
        
        # Take a screenshot after submitting the search
        time.sleep(5)  # Wait a bit for the page to load
        driver.save_screenshot("search_results_page.png")
        logger.info("Saved screenshot of search results page")
        
        # Wait for results to load - be more flexible in what we look for
        try:
            wait.until(EC.presence_of_any_element_located((
                By.CSS_SELECTOR, 
                "tr[valign='baseline'], .items-list, .results-list, table.items"
            )))
            logger.info("Search results loaded successfully")
        except Exception as e:
            logger.warning(f"Could not detect standard search results: {e}")
            # If we didn't find expected elements, check if there's any table with results
            tables = driver.find_elements(By.CSS_SELECTOR, "table")
            if len(tables) > 1:
                logger.info(f"Found {len(tables)} tables that might contain results")
            else:
                logger.error("Could not find any tables that might contain results")
                raise Exception("No search results found")
        
    except Exception as e:
        logger.error(f"Error during advanced search: {str(e)}")
        # Save screenshot to help diagnose the issue
        try:
            driver.save_screenshot("error_screenshot.png")
            logger.info("Saved error screenshot")
        except:
            pass
        raise

def extract_info_books(book_rows):
    """
    Extract information from book rows
    
    Parameters:
    book_rows (list): List of WebElements representing book rows
    
    Returns:
    list: List of dictionaries containing book information
    """
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
            year_match = re.search(r'</script>\s*(\d{4})', year_script)
            year = year_match.group(1) if year_match else "Unknown"
                    
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
                'keyword': current_keyword  # Add the keyword used for this search
            })
        except Exception as e:
            logger.warning(f"Error extracting info for a book: {str(e)}")
            continue
            
    return books_data

def scrape_taiwan_ncl_by_keyword(keyword, db_path):
    """
    Search for books by keyword using advanced search and scrape the results
    
    Parameters:
    keyword (str): Keyword to search for
    db_path (str): Path to SQLite database file
    """
    # Define chrome and driver with webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    global current_keyword
    current_keyword = keyword
    
    try:
        # Set up wait
        wait = WebDriverWait(driver, 60)
        
        # Perform advanced search with the keyword
        advanced_search(driver, keyword, wait)
        
        # Extract the total number of books in the search
        try:
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
            total_info = element.text
            # Look for the total number of books in the search based on pattern of the text       
            tot_books_match = re.search(r'of (\d+) 筆', total_info)
            tot_books = int(tot_books_match.group(1)) if tot_books_match else 0
            
            # Print total number of books
            logger.info(f"Total number of books for keyword '{keyword}': {tot_books}")
            print(f"Total number of books for keyword '{keyword}': {tot_books}")
        except Exception as e:
            logger.warning(f"Could not determine total number of books: {str(e)}")
            tot_books = 0
        
        # If no books found, return
        if tot_books == 0:
            logger.info(f"No books found for keyword '{keyword}'")
            driver.quit()
            return
        
        # Total number of pages to scrape from
        num_pages = math.ceil(tot_books/20)
        
        # Initialize a master list to store all books across pages
        all_books_data = []
        
        for page in range(0, num_pages):
            logger.info(f"Scraping page {page+1}/{num_pages} for keyword '{keyword}'")
            print(f"Scraping page {page+1}/{num_pages} for keyword '{keyword}'")
            
            # Wait for the book rows to load on the current page
            book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
            
            # Use function to extract info from books on the current page
            books_data = extract_info_books(book_rows)
            
            # Append current page's data to the master list
            all_books_data.extend(books_data)
            
            # Sleep to avoid having problems with the website
            time.sleep(randint(1, 5))
            
            # If it's not the last page, go to the next page
            if page < num_pages-1:
                try:
                    next_button = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "img[src$='f-next-page.gif'][alt='Next Page']")
                    ))
                    next_button.click()
                except Exception as e:
                    logger.error(f"Could not navigate to next page: {str(e)}")
                    break
            
        # Save books into a dataframe
        books_df = pd.DataFrame(all_books_data)
        
        # Connect to the SQLite database (creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)        
        # Save the DataFrame to the database, appending if the table exists
        books_df.to_sql('books_by_keyword', conn, if_exists='append', index=False)        
        # Close the connection
        conn.close()
        
        logger.info(f"Successfully scraped and saved {len(all_books_data)} books for keyword '{keyword}'")
        print(f"Successfully scraped and saved {len(all_books_data)} books for keyword '{keyword}'")
        
    except Exception as e:
        logger.error(f"An error occurred while scraping keyword '{keyword}': {str(e)}")
        print(f"An error occurred while scraping keyword '{keyword}': {str(e)}")
    finally:
        # Close the driver
        driver.quit()

def main():
    # Path to the database
    db_path = "../scraped_data/ncl_keyword_search.db"
    
    # List of specific keywords to search for
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
        "通信 建設", # Communication construction
        "彈性計",    # Elastic planning
        "工程",      # Engineering
        "炸藥",      # Explosives
        "釣魚",      # Fishing
        "林業",      # Forestry
        "鍛造作品",  # Forged works
        "燃料",      # Fuel
        "毛皮製品",  # Fur products
        "提供 傢俱", # Furniture provision
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
    
    # Scrape for each keyword
    for keyword in keywords:
        try:
            scrape_taiwan_ncl_by_keyword(keyword, db_path)
            # Add a longer delay between keywords to avoid being blocked
            time.sleep(randint(10, 20))
        except Exception as e:
            logger.error(f"Failed to scrape for keyword '{keyword}': {str(e)}")
            print(f"Failed to scrape for keyword '{keyword}': {str(e)}")

if __name__ == "__main__":
    main()