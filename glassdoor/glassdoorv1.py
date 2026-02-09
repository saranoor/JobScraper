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
import urllib.parse
import argparse
import logging
import sys
import re

# Terms to exclude from job titles
EXCLUDE_TERMS = {
    'lead', 'manager', 'senior', 'principal', 'director', 'vp', 'vice president',
    'sr ', 'ciso', 'chief', 'level 2', 'tier 3', 'associate director', 'l3',
    'architecture', 'sme', 'architect', 'field', 'software developer',
    'data scientist', 'scientist', 'federal account executive',
    'full stack developer', 'traveling aircraft mechanic', 'software engineer',
    'human resources operations', 'ii', 'regional technical development specialist',
    'stock plan administrator', 'commissioning authority', 'salesforce', 'dir',
    'consultant'
}

# Remote job detection patterns
REMOTE_PATTERNS = [
    r'\bremote\b',
    r'work\s*from\s*home',
    r'#li[-_ ]?remote',
    r'\b100\s*%?\s*remote\b',
    r'office\s+or\s+remote',
    r'hybrid\s+remote'
]

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

def is_remote_job(location: str, description: str = "") -> bool:
    """Check if job is remote based on location and description."""
    combined_text = f"{location} {description}".lower()
    for pattern in REMOTE_PATTERNS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            return True
    return False

def scrape_glassdoor_jobs(job_title: str, country: str, max_jobs: int = None, 
                          exclude_easy_apply: bool = False, 
                          exclude_titles: bool = False,
                          remote_only: bool = False):
    filename = f"glassdoor_jobs_{job_title}_{country}.csv"
    header = ["title", "company", "location", "salary", "description", "is_remote", "link"]

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

    driver = None
    
    try:
        options = uc.ChromeOptions()

        # HEADLESS MODE - Run without visible browser
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        options.add_argument("--start-maximized")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # Initialize driver with version detection
        try: 
            driver = uc.Chrome(options=options, use_subprocess=True)
        except Exception as e:
            print(f"First attempt failed: {e}")
            if "Current browser version is" in str(e):
                version_match = re.search(r"Current browser version is (\d+)\.", str(e))
                if version_match:
                    main_version = int(version_match.group(1))
                    print(f"Detected Chrome version {main_version}, retrying...")
                    
                    options = uc.ChromeOptions()
                    options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--start-maximized")
                    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
                    
                    driver = uc.Chrome(options=options, version_main=main_version, use_subprocess=True)
            else:
                raise

        # Navigate to Glassdoor
        print("Navigating to Glassdoor...")
        driver.get("https://www.glassdoor.com/Job/index.htm")
        wait = WebDriverWait(driver, 15)
        job_input = wait.until(EC.element_to_be_clickable((By.ID, "searchBar-jobTitle")))

        job_input.click()

        # Type the keyword slowly
        for char in job_title:
            job_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3)) 

        # Locate the Location input
        loc_input = driver.find_element(By.ID, "searchBar-location")

        # Clear and enter location
        loc_input.send_keys(Keys.CONTROL + "a")
        loc_input.send_keys(Keys.BACKSPACE)

        for char in country:
            loc_input.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))

        # Submit the search
        time.sleep(1)
        loc_input.send_keys(Keys.ENTER)
        
        # Wait for results to load
        time.sleep(3)
        
        jobs_data = []     
        last_processed_index = 0
        total_scraped = 0
        total_skipped_easy = 0
        total_skipped_title = 0
        total_skipped_remote = 0
        
        while True:
            if max_jobs and total_scraped >= max_jobs:
                print(f"\nReached target of {max_jobs} jobs. Stopping...")
                break
                
            job_cards = driver.find_elements(By.CSS_SELECTOR, "li[data-test='jobListing']")
            new_cards = job_cards[last_processed_index:]
            
            for card in new_cards:
                if max_jobs and total_scraped >= max_jobs:
                    break
                    
                try:
                    # Extract title first for filtering
                    title_el = card.find_element(By.CSS_SELECTOR, "[data-test='job-title']")
                    job_title_text = title_el.text.strip()
                    
                    # CHECK FOR EXCLUDED TITLES
                    if exclude_titles and should_exclude_job(job_title_text, EXCLUDE_TERMS):
                        total_skipped_title += 1
                        print(f"[SKIP-TITLE] {job_title_text} (Total: {total_skipped_title})")
                        continue
                    
                    # CHECK FOR EASY APPLY BUTTON
                    if exclude_easy_apply:
                        try:
                            easy_apply_button = card.find_element(By.CSS_SELECTOR, "[data-test='easyApply'], .EasyApplyButton_content__1cGPo")
                            total_skipped_easy += 1
                            print(f"[SKIP-EASY] Easy Apply job skipped (Total: {total_skipped_easy})")
                            continue
                        except:
                            pass
                    
                    # Extract other basic fields
                    company_el = card.find_element(By.CSS_SELECTOR, "[class*='EmployerProfile_compactEmployerName']")
                    location_el = card.find_element(By.CSS_SELECTOR, "[data-test='emp-location']")
                    location_text = location_el.text.strip()
                    
                    # Salary
                    try:
                        salary_el = card.find_element(By.CSS_SELECTOR, "[data-test='detailSalary']")
                        salary = salary_el.text.strip()
                    except:
                        salary = "N/A"
                    
                    link = title_el.get_attribute("href")
                    
                    # Click on the job card to load description
                    description = "N/A"
                    try:
                        # Scroll to card and click
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                        time.sleep(0.5)
                        card.click()
                        time.sleep(1.5)  # Wait for description to load
                        
                        # Try to extract description
                        try:
                            desc_el = driver.find_element(By.CSS_SELECTOR, "[class*='JobDetails_jobDescription']")
                            description = desc_el.text.strip()[:500]  # Limit to 500 chars
                        except:
                            try:
                                desc_el = driver.find_element(By.CSS_SELECTOR, ".jobDescriptionContent")
                                description = desc_el.text.strip()[:500]
                            except:
                                pass
                    except Exception as e:
                        logger.debug(f"Could not extract description: {e}")
                    
                    # Check if remote
                    remote_status = is_remote_job(location_text, description)
                    
                    # FILTER BY REMOTE IF ENABLED
                    if remote_only and not remote_status:
                        total_skipped_remote += 1
                        print(f"[SKIP-REMOTE] Non-remote job skipped (Total: {total_skipped_remote})")
                        continue
                    
                    # Store the data
                    job_info = {
                        "title": job_title_text,
                        "company": company_el.text.strip(),
                        "location": location_text,
                        "salary": salary,
                        "description": description,
                        "is_remote": "Yes" if remote_status else "No",
                        "link": link
                    }
                    
                    jobs_data.append(job_info)
                    total_scraped += 1
                    remote_indicator = "[REMOTE]" if remote_status else "[ONSITE]"
                    print(f"[SCRAPED {total_scraped}/{max_jobs if max_jobs else 'unlimited'}] {remote_indicator} {job_info['title']} at {job_info['company']}")

                except Exception as e:
                    logger.debug(f"Error processing card: {e}")
                    continue
            
            if jobs_data:
                with open(filename, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=header)
                    writer.writerows(jobs_data)
                
                jobs_data = []
                print(f"[SAVED] Batch saved to {filename}")
                time.sleep(1)
                
            last_processed_index = len(job_cards)
            
            if max_jobs and total_scraped >= max_jobs:
                break
            
            try:
                show_more_button = driver.find_element(By.CSS_SELECTOR, '[data-test="load-more"]')
                driver.execute_script("arguments[0].click();", show_more_button)
                time.sleep(2)
            except Exception as e:
                driver.save_screenshot("error_view.png")
                print(f"[INFO] Could not find the option to load more")
                break

            try:
                close_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[class*='Close'], .CloseButton, [aria-label='Close']"))
                )
                driver.execute_script("arguments[0].click();", close_button)
                print("[INFO] Pop-up closed successfully.")
                time.sleep(1)
            except Exception as e:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            
            time.sleep(random.uniform(1.1, 2.3))

        print(f"\n{'='*50}")
        print(f"[COMPLETE] Scraping complete!")
        print(f"[STATS] Total jobs scraped: {total_scraped}")
        if exclude_easy_apply:
            print(f"[STATS] Easy Apply jobs skipped: {total_skipped_easy}")
        if exclude_titles:
            print(f"[STATS] Excluded titles skipped: {total_skipped_title}")
        if remote_only:
            print(f"[STATS] Non-remote jobs skipped: {total_skipped_remote}")
        print(f"[STATS] Results saved to: {filename}")
        print(f"{'='*50}")

    except Exception as e:
        print(f"[ERROR] An exception occurred: {e}")
        logger.error(f"Error during scraping: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()

        
if __name__ == "__main__":
    print("=" * 50)
    print(" Glassdoor Job Scraper (Headless Mode)")
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

    # Ask if they want to exclude Easy Apply jobs
    exclude_easy = input(
        "Exclude Easy Apply jobs? (y/n, default=n): "
    ).strip().lower() in ['y', 'yes']
    
    # Ask if they want to exclude certain job titles
    exclude_titles = input(
        "Exclude senior/manager/lead positions? (y/n, default=n): "
    ).strip().lower() in ['y', 'yes']
    
    # Ask if they want remote only
    remote_only = input(
        "Remote jobs only? (y/n, default=n): "
    ).strip().lower() in ['y', 'yes']

    print("\nStarting scraping in headless mode...")
    if exclude_easy:
        print("[FILTER] Filtering out Easy Apply jobs")
    if exclude_titles:
        print("[FILTER] Filtering out senior/manager/lead positions")
    if remote_only:
        print("[FILTER] Remote jobs only")
    print()
    
    results = scrape_glassdoor_jobs(
        job_title=urllib.parse.quote(title),
        country=urllib.parse.quote(location),
        max_jobs=max_jobs,
        exclude_easy_apply=exclude_easy,
        exclude_titles=exclude_titles,
        remote_only=remote_only
    )