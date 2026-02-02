from selenium.webdriver.common.by import By
import time
from dotenv import load_dotenv
import os
from selenium.webdriver.common.keys import Keys
import argparse
import urllib.parse
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import undetected_chromedriver as uc
import winsound
import urllib.parse
import argparse
import logging
import sys
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("scraper.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

sys.excepthook = handle_exception

def prompt_required(prompt_text):
    while True:
        value = input(prompt_text).strip()
        if value:
            return value
        print("This field is required. Please try again.\n")

def scrape_glassdoor_jobs(job_title: str, country: str):
    filename = f"glassdoor_jobs_{job_title}_{country}.csv"
    header = ["title", "company", "location", "salary", "link"]

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

    options = uc.ChromeOptions()

    options.add_argument("--start-maximized")
    
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    try: 
        sess = uc.Chrome()
    except Exception as e: 
        main_version_string = re.search(r"Current browser version is (\d+\.\d+\.\d+)", str(e)).group(1)
        main_version = int(main_version_string.split(".")[0])
        driver = uc.Chrome(options=options,version_main=main_version)

    try:
        # 3. Navigate to the login page
        print("Navigating to Glassdoor Login...")
        driver.get("https://www.glassdoor.com/Job/index.htm")
        wait = WebDriverWait(driver, 15)
        job_input = wait.until(EC.element_to_be_clickable((By.ID, "searchBar-jobTitle")))

        job_input.click() # Human-like click

        # Type the keyword slowly
        for char in job_title:
            job_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3)) 

        # 3. Locate the Location input
        loc_input = driver.find_element(By.ID, "searchBar-location")

        # Glassdoor often fills this automatically. Let's clear it first.
        loc_input.send_keys(Keys.CONTROL + "a")
        loc_input.send_keys(Keys.BACKSPACE)

        for char in country:
            loc_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))

        # 4. Submit the search
        time.sleep(1)
        loc_input.send_keys(Keys.ENTER)   
        jobs_data=[]     
        last_processed_index = 0
        while True:
            job_cards = driver.find_elements(By.CSS_SELECTOR, "li[data-test='jobListing']")
            new_cards = job_cards[last_processed_index:]
            for card in new_cards:
                try:
                    # 2. Extract specific fields using data attributes and unique classes
                    title_el = card.find_element(By.CSS_SELECTOR, "[data-test='job-title']")
                    company_el = card.find_element(By.CSS_SELECTOR, "[class*='EmployerProfile_compactEmployerName']")
                    location_el = card.find_element(By.CSS_SELECTOR, "[data-test='emp-location']")
                    
                    # Salary can sometimes be missing
                    try:
                        salary_el = card.find_element(By.CSS_SELECTOR, "[data-test='detailSalary']")
                        salary = salary_el.text.strip()
                    except:
                        salary = "N/A"
                        
                    link = title_el.get_attribute("href")

                    # Store the data
                    job_info = {
                        "title": title_el.text.strip(),
                        "company": company_el.text.strip(),
                        "location": location_el.text.strip(),
                        "salary": salary,
                        "link": link
                    }
                    
                    jobs_data.append(job_info)
                    print(f"jobs info: {job_info}")

                except Exception as e:
                    # This skips things like ads or "Enhance your job" cards inside the list
                    continue
            
            if jobs_data: # Only write if we actually found new jobs
                with open(filename, 'a', newline='', encoding='utf-8') as f:
                    # Use extrasaction='ignore' to prevent crashes if a key is missing
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writerows(jobs_data)
                
                # CLEAR the list after writing so you don't write duplicates to the CSV next time
                jobs_data = [] 
                print(f"Batch saved to {filename}")
                time.sleep(1)
            last_processed_index = len(job_cards)
            try:
                show_more_button = driver.find_element(By.CSS_SELECTOR, '[data-test="load-more"]')
                driver.execute_script("arguments[0].click();", show_more_button)
            except Exception as e:
                driver.save_screenshot("error_view.png")
                print(f"Could not find the option to load more: {e}")
                winsound.Beep(4000,3000)
                break

            try:
                # This looks for any button containing an SVG with 'Close' in the class or the button itself
                close_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[class*='Close'], .CloseButton, [aria-label='Close']"))
                )
                
                # Using JS click to bypass any overlays or 'not clickable' errors
                driver.execute_script("arguments[0].click();", close_button)
                print("Pop-up closed successfully.")
                time.sleep(1)
            except Exception as e:
                # If the specific button fails, try clicking the 'Escape' key as a backup
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                print(f"Could not find button, sent ESCAPE key instead. {e}")
            time.sleep(random.uniform(1.1, 2.3))


    except Exception as e:
        print(f"An exception occured: {e}")

    time.sleep(1200)
    
        
if __name__ == "__main__":
    print("=" * 50)
    print(" Glassdoor Job Scraper")
    print("=" * 50)

    title = prompt_required(
        "Enter job title (e.g. software engineer): "
    )

    location = prompt_required(
        "Enter location (e.g. Canada): "
    )

    print("\nStarting scraping...\n")
    results = scrape_glassdoor_jobs(
        job_title=urllib.parse.quote(title),
        country=urllib.parse.quote(location)
    )

