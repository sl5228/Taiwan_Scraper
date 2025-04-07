#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modified on Mon Mar 31 2025

This code scrapes the technical books of the National Central Library of Taiwan

    - It uses keywords to search for technical books in the library catalog
    - We use the Advanced Search feature to look for books on specific topics
    - We refine the search by filtering only books in Chinese between 1500 and 2023
    - The website only shows 20 books at a time, so we iterate over all the pages
        with technical books, extract the main information 
        (title, author, year, call number) and save it.

Based on original code by: hk3384
"""


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

#%% Main functions to webscrape.

# Function to search by keyword
def search_by_keyword(driver, keyword, wait):
    # Navigate to the main search page
    base_url = "https://aleweb.ncl.edu.tw/F"
    driver.get(base_url)
    
    # Wait for the page to load
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "form[name='search']")))
    
    # Look for the advanced search link and click it
    adv_search_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Advanced Search') or contains(text(), '進階查詢')]")
    adv_search_link.click()
    
    # Wait for the advanced search form to load
    wait.until(EC.presence_of_element_located((By.NAME, "request")))
    
    # Enter the keyword
    search_input = driver.find_element(By.NAME, "request")
    search_input.clear()
    search_input.send_keys(keyword)
    
    # Select "Subject" as the field to search (WRD is for words in subject)
    field_select = Select(driver.find_element(By.NAME, "find_code"))
    field_select.select_by_value("WRD")
    
    # Turn off "Words Adjacent" if it's available and selected
    try:
        adjacent_checkbox = driver.find_element(By.NAME, "adjacent")
        if adjacent_checkbox.is_selected():
            adjacent_checkbox.click()
    except:
        # If the checkbox isn't found, continue without error
        pass
    
    # Set up the language filter for Chinese
    try:
        language_select = Select(driver.find_element(By.NAME, "request_lang"))
        language_select.select_by_value("CHI")
    except:
        print("Could not set language filter directly, will apply in refinement")
        
    # Set up date range 1500-2023
    try:
        start_year = driver.find_element(By.NAME, "year_type")
        start_year.clear()
        start_year.send_keys("1500")
        
        end_year = driver.find_element(By.NAME, "year_type_2")
        end_year.clear()
        end_year.send_keys("2023")
    except:
        print("Could not set date range directly, will apply in refinement")
    
    # Set material type to Book
    try:
        material_select = Select(driver.find_element(By.NAME, "material_type"))
        material_select.select_by_value("BK")
    except:
        print("Could not set material type directly, will apply in refinement")
    
    # Submit the search
    submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Search']")
    submit_button.click()
    
    # Wait for search results
    try:
        # First check if we have results
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
        return True
    except:
        # Check if we have no results
        try:
            no_results = driver.find_element(By.XPATH, "//*[contains(text(), 'No records found')]")
            print(f"No results found for keyword: {keyword}")
            return False
        except:
            # If neither results nor "no results" message is found, try to refine anyway
            return True

# Function to refine the search (look for books in Chinese, between 1500 and 2023)
def refine_request(driver, language, start_year, end_year, wait):
        # Look for 'Refine' section (to refine the search)
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.bar a[title='Refine']")))
        
        # time.sleep(8)

        # Open webpage, look for refine button, press, add refining options (chinese, books, 1500-2023)
        # Extract the href attribute (URL)
        refine_url = element.get_attribute('href')                
        # Navigate to the extracted URL
        driver.get(refine_url)

        #time.sleep(8)
                
        # Select 'CHI' from the first dropdown
        select_element1 = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_1")))
        select1 = Select(select_element1)
        select1.select_by_value(language)

        # time.sleep(3)
        
        # Enter '1500' in the first text input (updated from 1925)
        input_element1 = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_2")))
        input_element1.send_keys(start_year)
        
        # time.sleep(3)

        # Enter '2023' in the second text input
        input_element2 = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_3")))
        input_element2.send_keys(end_year)
        
        # time.sleep(3)
        
        # Select 'BK' from the second dropdown
        select_element2 = wait.until(EC.presence_of_element_located((By.NAME, "filter_request_4")))
        select2 = Select(select_element2)
        select2.select_by_value("BK")

        # time.sleep(8)
        
        # Click button 'Go' to filter based on the selected options
        submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='image'][alt='Submit modify form']")
        submit_button.click()

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
    
#%% Main Scraper Function for Keywords
def scrape_taiwan_ncl_by_keyword(keyword, db_path):
    # Define chrome and driver
    driver = webdriver.Chrome()
    
    try:
        # Set up wait
        wait = WebDriverWait(driver, 60)
        
        # Search by keyword
        search_success = search_by_keyword(driver, keyword, wait)
        
        if not search_success:
            driver.quit()
            return
        
        # Check if we need to refine the search (if some options couldn't be set on the search page)
        try:
            # Try to refine the search if the Refine button exists
            refine_link = driver.find_element(By.CSS_SELECTOR, "td.bar a[title='Refine']")
            refine_request(driver=driver, language="CHI", start_year="1500", end_year="2023", wait=wait)
        except Exception as e:
            # If no refine button, assume search was already properly filtered
            print(f"Could not refine search: {e}")
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 30)
        
        # Extract the total number of books in the search
        try:
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
            total_info = element.text
            # Look for the total number of books in the search based on pattern of the text       
            tot_books = int(re.search(r'of (\d+) 筆', total_info).group(1))
            # Print total number of books
            print(f"Total number of books for keyword '{keyword}': {tot_books}")
        except Exception as e:
            print(f"Could not determine number of books for keyword '{keyword}', assuming zero: {e}")
            driver.quit()
            return
        
        # Total number of pages to scrape from
        num_pages = math.ceil(tot_books/20)

        # Extract information of books
        wait = WebDriverWait(driver, 10)
        book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))

        # Initialize a master list to store all books across pages
        all_books_data = []
        for page in range(0, num_pages):
            print(f"Scraping page {page+1}/{num_pages} of keyword {keyword}")
        
            # Wait for the book rows to load on the current page
            wait = WebDriverWait(driver, 10)
            book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
        
            # Use predefined function to extract info from books on the current page
            books_data = extract_info_books(book_rows)
            
            # Add keyword to each book entry
            for book in books_data:
                book['keyword'] = keyword
        
            # Append current page's data to the master list
            all_books_data.extend(books_data)
            
            # Sleep to avoid having problems with the website
            time.sleep(randint(1,5))
            # If it's not the last page, go to the next page
            if page < num_pages-1:
                try:
                    next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "img[src$='f-next-page.gif'][alt='Next Page']")))
                    next_button.click()
                except Exception as e:
                    print(f"Could not navigate to next page: {e}")
                    break
        
        # Save books into a dataframe
        books_df = pd.DataFrame(all_books_data)

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Connect to the SQLite database (creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)        
        # Save the DataFrame to the database, appending if the table exists
        books_df.to_sql('books_by_keyword', conn, if_exists='append', index=False)        
        # Close the connection
        conn.close()
        
        print(f"Successfully saved {len(all_books_data)} books for keyword '{keyword}'")

    except Exception as e:
        print(f"An error occurred while scraping keyword {keyword}: {str(e)}")
        # Close the driver if it's still open
        if driver:
            driver.quit()
    finally:
        # Make sure to close the driver even if there's an error
        if driver:
            try:
                driver.quit()
            except:
                pass

#%% Test the scraper with a single keyword          
db_path = "../scraped_data/keyword_test.db"
scrape_taiwan_ncl_by_keyword(keyword="工程", db_path=db_path)  # Example: Engineering

#%% Scrape with a list of keywords
db_path = "../scraped_data/keywords_data.db"

# List of keywords to search for
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

for keyword in keywords:
    try:
        scrape_taiwan_ncl_by_keyword(keyword, db_path=db_path)
    except Exception as e:
        print(f"An error occurred while scraping keyword {keyword}: {str(e)}")
    
    # Add a delay between keywords to avoid overloading the server
    time.sleep(randint(10, 20))

# Connect to the database to check results
try:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM books_by_keyword", conn)
    conn.close()
    
    # Count books per keyword
    books_per_keyword = df.groupby('keyword')['title'].count()
    print("\nSummary of books collected by keyword:")
    print(books_per_keyword)
    
    # Total books collected
    print(f"\nTotal books collected: {len(df)}")
    
except Exception as e:
    print(f"Error accessing database: {str(e)}")

#%% THINK ABOUT USING A VPN!!!!!!