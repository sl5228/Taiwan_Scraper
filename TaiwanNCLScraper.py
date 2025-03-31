#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec  5 11:11:38 2024

This code scrapes the technical books of the National Central Library of Taiwan

    - It uses the Chinese Classification System (CCL) to look for books in each 
        subcategory that we consider as technical (the list is below). 
    - We can look for the books of each of those subcategories using a base URL
    - We refine the search by filtering only books in Chinese between 1500 and 2023.
    - The website only shows 20 books at a time, so we iterate over all the pages
        with technical books, extract the main information 
        (title, author, year, call number) and save it.

@author: hk3384
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

#%% Main functions to webscrape.

# Function to refine the search (look for books in Chinese, between 1500 and 2023)
def refine_request(driver,language,start_year,end_year,wait):
        # Look for 'Refine' section (to refine the search)
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.bar a[title='Refine']")))
        
        # time.sleep(8)

        # Open webpage, look for refine button, press, add refining options (chinese, books, 1925-2023)
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
        
        # Enter '1925' in the first text input
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
    
#%% Main Scraper Function (uses both functions from above)
def scrape_taiwan_ncl(category,db_path):
    # Define chrome and driver
    driver = webdriver.Chrome()
    
    try:
        # category = "449"        
        url = "https://aleweb.ncl.edu.tw/aleph-cgi/top/call_no_list.cgi?call_no=" + category

        # Set up Chrome driver
        # Sometimes URL doesn't load the first time, try twice if it doesn't work the 1st
        try:
            driver.get(url)
            # Wait for the page to load
            wait = WebDriverWait(driver, 60)
        except Exception as e:
            # try second time
            try:
                driver.get(url)
                # Wait for the page to load
                wait = WebDriverWait(driver, 60)
            except Exception as e:
                print(f"Couldn't load the URL for category {category}: {str(e)}")
                
        # Refine search (search only books in Japanese between 1925 and 2023)
        refine_request(driver=driver,language="CHI", start_year="1925", end_year="2023",wait=wait)

        # Wait for the page to load
        wait = WebDriverWait(driver, 30)
        # Extract the total number of books in the search
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.text3[width='20%'][nowrap]")))
        total_info = element.text
        # Look for the total number of books in the search based on pattern of the text       
        tot_books = int(re.search(r'of (\d+) 筆', total_info).group(1))
        # Print total number of books
        print(f"Total number of books in category {category}: {tot_books}")
        
        # Total number of pages to scrape from
        num_pages = math.ceil(tot_books/20)

        # Extract information of books
        wait = WebDriverWait(driver, 10)
        book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))

        # Initialize a master list to store all books across pages
        all_books_data = []
        for page in range(0, num_pages): # page = 25
            print(f"Scraping page {page+1}/{num_pages} of category {category}")
        
            # Wait for the book rows to load on the current page
            wait = WebDriverWait(driver, 10)
            book_rows = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr[valign='baseline']")))
        
            # Use predefined function to extract info from books on the current page
            books_data = extract_info_books(book_rows)
        
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
            else:
                # Close the driver
                driver.quit()
        
        # Save books into a dataframe
        books_df = pd.DataFrame(all_books_data)
        # Add category number (add the description later)
        books_df['category'] = category

        # Connect to the SQLite database (creates it if it doesn't exist)
        conn = sqlite3.connect(db_path)        
        # Save the DataFrame to the database, appending if the table exists
        books_df.to_sql('books', conn, if_exists='append', index=False)        
        # Close the connection
        conn.close()

    except Exception as e:
            print(f"An error occurred while scraping category {category}: {str(e)}")
            # Close the driver if it's still open
            if driver:
                driver.quit()
            # You might want to log the error or take other actions here

#%% Test the scraper            
db_path = "../scraped_data/test_dataset__.db"
scrape_taiwan_ncl(category="444", db_path=db_path)


list_of_call_nb = [430] + [431] + list(range(433,454)) + list(range(456,499))

    
conn = sqlite3.connect(db_path)        
df = pd.read_sql_query("SELECT * FROM books", conn)

#%% Scrape with loop for each category

db_path = "../scraped_data/real_test_scraper.db"

list_of_call_nb = [430] + [431] + list(range(433,454)) + list(range(456,499))


for category in list_of_call_nb:
    try:
        scrape_taiwan_ncl(str(category),db_path=db_path)
    except Exception as e:
            print(f"An error occurred while scraping category {category}: {str(e)}")

        
# Re-scrape those categories that had an error
scraped_categ = set(map(int,df['category'].unique()))
tot_categ = set(list_of_call_nb)

categ_to_scrape = list(tot_categ - scraped_categ)

for category in categ_to_scrape:
    try:
        scrape_taiwan_ncl(str(category),db_path=db_path)
    except Exception as e:
            print(f"An error occurred while scraping category {category}: {str(e)}")


books_per_category = df.groupby('category')['title'].count()

#%% THINK ABOUT USING A VPN!!!!!!