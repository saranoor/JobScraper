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


load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

RAW_PROXIES = [
    "31.59.20.176:6754:fnqvxcbv:n5up65ti6mxu",
    "23.95.150.145:6114:fnqvxcbv:n5up65ti6mxu",
    "198.23.239.134:6540:fnqvxcbv:n5up65ti6mxu",
    "107.172.163.27:6543:fnqvxcbv:n5up65ti6mxu",
    "198.105.121.200:6462:fnqvxcbv:n5up65ti6mxu",
]

def build_proxy(raw):
    ip, port, user, pwd = raw.split(":")
    proxy = f"http://{user}:{pwd}@{ip}:{port}"
    return {"http": proxy, "https": proxy}



import random

def get_random_proxy():
    return build_proxy(random.choice(RAW_PROXIES))

def scrape_linkedin_jobs(job_title: str, country: str):

    proxy_url = random.choice(RAW_PROXIES)
    proxy_options = {
    'proxy': {
        'http': f'http://{proxy_url}',
        'https': f'http://{proxy_url}',
    }
    }
    options = uc.ChromeOptions()

    options.add_argument("--start-maximized")
    
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    try: 
        driver = uc.Chrome()
    except Exception as e: 
        main_version_string = re.search(r"Current browser version is (\d+\.\d+\.\d+)", str(e)).group(1)
        main_version = int(main_version_string.split(".")[0])
        driver = uc.Chrome(options=options,version_main=main_version)

    driver.get("https://api.ipify.org")
    ip = driver.find_element("tag name", "body").text
    print("[BROWSER IP]", ip)

    linkedin_login(driver, EMAIL, PASSWORD)
    input("Solve CAPTCHA, then press ENTER to continue...")

    # print("[PROXY STRING]", proxy)

    search_url = (
    "https://www.linkedin.com/jobs/search/"
    f"?keywords={urllib.parse.quote(args.keywords)}"
    f"&location={urllib.parse.quote(args.location)}"
    )
    
    page=0
    card_num =0
    missed_card_num=0
    while True:
        if page==5:
            break
        # Calculate the 'start' parameter (LinkedIn uses increments of 25)
        start_val = page * 25
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

                # title = driver.find_element(By.CSS_SELECTOR, "h2.top-card-layout__title").text
                
                try:
                    # Target the container text directly rather than searching for an <a> tag
                    title_element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "job-details-jobs-unified-top-card__job-title"))
)
                    title = title_element.text
                except:
                    # Fallback to the card text if the detail pane is being stubborn
                    # title = card.find_element(By.CSS_SELECTOR, ".job-card-list__title").text

                    title = driver.find_element(By.CSS_SELECTOR, "h1 a").text

                # description = driver.find_element(
                #     By.CSS_SELECTOR, "div.show-more-less-html__markup"
                # ).text
                description = driver.find_element(By.ID, "job-details")
                description_text = description.text
                prefs = driver.find_elements(
                    By.CSS_SELECTOR,
                    "div.job-details-fit-level-preferences button strong"
                )

                tags = [p.text.strip() for p in prefs]

                is_remote = "Remote" in tags
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
                    "job_title": title,
                    "company": company,
                    "location": location,
                    "salary": salary,
                    "description": description_text,
                    "is_remote": "Yes" if is_remote else "NO",
                    "link": link
                })

                print(jobs_data[-1]['job_title'])

            except Exception as e:
                print(f"Could not scrape card: {e}")
                print(f"card number: {card_num}")
                missed_card_num+=1
                print(f"missed card number: {missed_card_num}")
                continue
        page+=1


    driver.quit()
    return jobs_data


def linkedin_login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(random.randint(2,8))

    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password + Keys.RETURN)

    time.sleep(5)  # wait until logged in


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keywords", required=True)
    parser.add_argument("--location", required=True)
    args = parser.parse_args()

    results = scrape_linkedin_jobs(
        job_title="Backend Engineer",
        country="Canada"
    )

    filename = f"{args.keywords}_{args.location}_linkedin.csv".replace(" ", "_")

    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)

    print(f"Saved to {filename}")

    print(f"Scraped {len(results)} jobs")
