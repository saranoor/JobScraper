from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import time
from dotenv import load_dotenv
import os
from selenium.webdriver.common.keys import Keys
import argparse
import urllib.parse
import pandas as pd
import random
import re
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import logging
import sys
import random
import csv

load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Terms to exclude from job titles
EXCLUDE_TERMS = {
    'lead', 'manager', 'senior', 'principal', 'director', 'vp', 'vice president',
    # 'sr ', 'ciso', 'chief', 'level 2', 'tier 3', 'associate director', 'l3',
    # 'architecture', 'sme', 'architect', 'field', 'software developer',
    # 'data scientist', 'scientist', 'federal account executive',
    # 'full stack developer', 'traveling aircraft mechanic', 'software engineer',
    # 'human resources operations', 'ii', 'regional technical development specialist',
    # 'stock plan administrator', 'commissioning authority', 'salesforce', 'dir',
    # 'consultant'
}

remote_dict = {
    'ALL': '',
    'ON-SITE': '1',
    'REMOTE': '2',
    'HYBRID': '3'
}

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

def should_exclude_job(title: str, exclude_terms: set) -> bool:
    """Check if job title contains any excluded terms."""
    title_lower = title.lower()
    for term in exclude_terms:
        if term in title_lower:
            return True
    return False

def create_filename(title, location):
    date_strf = datetime.datetime.now().strftime('%Y-%m-%d')
    pos = title.replace(" ", "_")
    return f'LinkedIn_Jobs_{pos}_{location}_{date_strf}.csv'

def scrape_linkedin_jobs(job_title: str, location: str, max_jobs: str,
        exclude_easy_apply:bool,
        exclude_titles:bool,
        type_of_work:str,
        headless:bool):
    
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = None
    
    filename = create_filename(job_title, location)
    header = ["title", "company", "location", "salary", "description", "type_of_work", "link"]

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

    try:
        # Try to create driver with automatic version detection
        try:
            driver = uc.Chrome(options=options)
        except Exception as e:
            main_version_string = re.search(r"Current browser version is (\d+\.\d+\.\d+)", str(e)).group(1)
            main_version = int(main_version_string.split(".")[0])
            driver = uc.Chrome(options=options,version_main=main_version)

        driver.get("https://api.ipify.org")
        ip = driver.find_element("tag name", "body").text
        print("[BROWSER IP]", ip)

        print("Navigating to Linkedin Authentication required")
        linkedin_login(driver, EMAIL, PASSWORD)
        input("Solve CAPTCHA, then press ENTER to continue...")

        search_url = (
        "https://www.linkedin.com/jobs/search/"
        f"?keywords={job_title}"
        f"&location={location}"
        )

        if type_of_work:
            remote_value = remote_dict.get(type_of_work, '')
            search_url += f'&f_WT={remote_value}'
        
        page=0
        card_num =0
        total_scraped = 0
        total_missed_card=0
        total_skipped_title=0
        total_skipped_easy = 0

        while True:
            if page==2: # for testing only, will remove later
                break
            start_val = page * 25 # Calculate the 'start' parameter (LinkedIn uses increments of 25)
            search_url+=f"&start={start_val}"
            driver.get(search_url)
            time.sleep(random.randint(1,5))

            jobs_data = []

            # job_cards = driver.find_elements(By.CSS_SELECTOR, "ul.jobs-search__results-list li")
            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job-card-container[data-job-id]")

            
            for card in job_cards:
                card_num+=1
                print("I am gonna try cards")
                try:
                    card.click()
                    time.sleep(random.randint(2,20))

                    
                    try:
                        # Target the container text directly rather than searching for an <a> tag
                        title_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title"))
    )
                        title = title_element.text
                    except:
                        title = driver.find_element(By.CSS_SELECTOR, "h1 a").text

                    if exclude_titles and should_exclude_job(title, EXCLUDE_TERMS):
                        total_skipped_title += 1
                        print(f"[SKIP-TITLE] {title} (Total: {total_skipped_title})")
                        continue
                    description = driver.find_element(By.ID, "job-details")
                    description_text = description.text
                    prefs = driver.find_elements(
                        By.CSS_SELECTOR,
                        "div.job-details-fit-level-preferences button strong"
                    )

                    tags = [p.text.strip() for p in prefs]

                    print(f"tags: {tags}")
                    if type_of_work == 'ALL':
                        if 'remote' in tags:
                            work_type = 'remote'
                        elif 'hybrid' in tags:
                            work_type = 'hybrid'
                        elif 'On-site' in tags or 'onsite' in tags:
                            work_type = 'onsite'
                        else:
                            work_type = None

                    else:
                        work_type = type_of_work

                    is_full_time = "Full-time" in tags
                    salary = next((s for s in tags if "$" in s), "Not listed")

                    # Company Name
                    try:
                        company = driver.find_element(By.CSS_SELECTOR, ".job-details-jobs-unified-top-card__company-name").text
                    except:
                        company = None

                    # Job URL (assuming 'card' is the clickable element in the list)
                    try:
                        link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    except:
                        link = None

                    # Location
                    try:
                        location = driver.find_element(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__tertiary-description-container span[dir='ltr']").text.split('·')[0].strip()
                    except:
                        location = None
                    
                    jobs_data.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "salary": salary,
                        "description": description_text,
                        "type_of_work": work_type,
                        "link": link
                    })

                    print(jobs_data[-1]['title'])

                    total_scraped+=1
                    print(f"Total scraped at the moment: {total_scraped}")

                except Exception as e:
                    print(f"Could not scrape card {card_num} because an error occured: {e}")
                    total_missed_card+=1
                    print(f"missed card number: {total_missed_card}")
            
            if jobs_data:
                with open(filename, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writerows(jobs_data)
                print(f"[SAVED] Batch saved to {filename}")
                time.sleep(1)
            page+=1

    except Exception as e:
        print(f"[ERROR] An exception occurred: {e}")
        logger.error(f"Error during scraping: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()


def linkedin_login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(random.randint(2,8))

    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password + Keys.RETURN)

    time.sleep(5)  # wait until logged in


if __name__ == "__main__":
    print("=" * 50)
    print(" LinkedIn Authentication Job Scraper")
    print(" Please have LinkedIn Login Credentials ready...")
    print("=" * 50)

    title = prompt_required(
        "Enter job title (e.g. software engineer): "
    )

    location = prompt_required(
        "Enter location (e.g. Canada): "
    )

    max_jobs_input = input(
        "Enter max number of jobs to scrape (press Enter for unlimited): "
    ).strip()

    max_jobs = int(max_jobs_input) if max_jobs_input else None

    exclude_easy = input(
        "Exclude Easy Apply jobs? (y/n, default=n): "
    ).strip().lower() in ['y', 'yes']

    exclude_titles = input(
        "Exclude senior/manager/lead positions? (y/n, default=n): "
    ).strip().lower() in ['y', 'yes']

    type_of_work = prompt_required(
        "Type of job? (ALL/ON-SITE/REMOTE/HYBRID, default=ALL): "
    )
    
    headless_mode = input(
        "Run in headless mode (invisible browser)? (y/n, default=y): "
    ).strip().lower()
    
    headless = headless_mode not in ['n', 'no']

    print("\nStarting scraping...")
    if headless:
        print("[MODE] Headless (invisible browser)")
    else:
        print("[MODE] Visible browser")
        
    if exclude_easy:
        print("[FILTER] Filtering out Easy Apply jobs")
    if exclude_titles:
        print("[FILTER] Filtering out senior/manager/lead positions")

    print()

    results = scrape_linkedin_jobs(
        job_title=title,
        location=location,
        max_jobs=max_jobs,
        exclude_easy_apply=exclude_easy,
        exclude_titles=exclude_titles,
        type_of_work=type_of_work,
        headless=headless
    )
