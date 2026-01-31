from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from dotenv import load_dotenv
import os
from selenium.webdriver.common.keys import Keys
import argparse
import urllib.parse
import pandas as pd
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc

load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")


from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Usage:
# search_and_scrape(driver, "Backend Engineer", "Canada")

def scrape_glassdoor_jobs(job_title: str, country: str):
    keyword = "Software Engineer"
    location = "Canada"
    options = uc.ChromeOptions()
    # options.add_argument(r"--user-data-dir=C:\Users\saran\AppData\Local\Google\Chrome\User Data")

    # Create a specific path for the bot's profile
    # This avoids using your 'Default' profile that might be open
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # user_data_path = os.path.join(script_dir, "glassdoor_profile")

    # options.add_argument(f"--user-data-dir={user_data_path}")
    # No need for --profile-directory=Default here, it will create its own
    # options.add_argument(r'--profile-directory=Default')
    options.add_argument("--start-maximized")
    
    # 2. Add a common User-Agent
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    # 3. Initialize the undetected driver. Undetected driver to It's a wrapper for Selenium that patches
    #  the driver binary on the fly to hide the common fingerprints that websites look for.
    driver = uc.Chrome(options=options, version_main=122)

    try:
        # 3. Navigate to the login page
        print("Navigating to Glassdoor Login...")
        # driver.get("https://www.glassdoor.com/member/profile/login")
        # input("Solve CAPTCHA, then press ENTER to continue...")
        driver.get("https://www.glassdoor.com/Job/index.htm")
        wait = WebDriverWait(driver, 15)
        job_input = wait.until(EC.element_to_be_clickable((By.ID, "searchBar-jobTitle")))

        job_input = wait.until(EC.element_to_be_clickable((By.ID, "searchBar-jobTitle")))
        job_input.click() # Human-like click

        # Type the keyword slowly
        for char in keyword:
            job_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3)) 

        # 3. Locate the Location input
        loc_input = driver.find_element(By.ID, "searchBar-location")

        # Glassdoor often fills this automatically. Let's clear it first.
        loc_input.send_keys(Keys.CONTROL + "a")
        loc_input.send_keys(Keys.BACKSPACE)

        for char in location:
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
                    # print(f"Found: {job_info['title']} at {job_info['company']}")
                    print(f"jobs info: {job_info}")

                except Exception as e:
                    # This skips things like ads or "Enhance your job" cards inside the list
                    continue
            last_processed_index = len(job_cards)
            show_more_button = driver.find_element(By.CSS_SELECTOR, '[data-test="load-more"]')
            driver.execute_script("arguments[0].click();", show_more_button)

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
                print("Could not find button, sent ESCAPE key instead.")


    except Exception as e:
        print(f"An exception occured: {e}")

    
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", required=True)
    parser.add_argument("--location", required=True)
    args = parser.parse_args()
    results = scrape_glassdoor_jobs(
        job_title="Backend Engineer",
        country="Canada"
    )

