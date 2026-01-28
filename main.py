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

load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")



def scrape_linkedin_jobs(job_title: str, country: str):
    options = Options()
    # options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    linkedin_login(driver, EMAIL, PASSWORD)
    input("Solve CAPTCHA, then press ENTER to continue...")



    search_url = (
    "https://www.linkedin.com/jobs/search/"
    f"?keywords={urllib.parse.quote(args.keywords)}"
    f"&location={urllib.parse.quote(args.location)}"
    )

    driver.get(search_url)
    time.sleep(2)

    jobs_data = []

    # job_cards = driver.find_elements(By.CSS_SELECTOR, "ul.jobs-search__results-list li")
    job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job-card-container[data-job-id]")


    for card in job_cards:
        print("I am gonna try cards")
        try:
            card.click()
            time.sleep(2)

            # title = driver.find_element(By.CSS_SELECTOR, "h2.top-card-layout__title").text
            title = driver.find_element(By.CSS_SELECTOR, "h1 a").text

            # description = driver.find_element(
            #     By.CSS_SELECTOR, "div.show-more-less-html__markup"
            # ).text
            description = driver.find_element(By.ID, "job-details").text
            prefs = driver.find_elements(
                By.CSS_SELECTOR,
                "div.job-details-fit-level-preferences button strong"
            )

            tags = [p.text.strip() for p in prefs]

            is_remote = "Remote" in tags
            is_full_time = "Full-time" in tags

            jobs_data.append({
                "job_title": title,
                "remote": is_remote,
                "full_time": is_full_time,
                "job_description": description
            })

        except Exception:
            print(f"Could not scrape")
            continue

    driver.quit()
    return jobs_data

from selenium.webdriver.common.keys import Keys

def linkedin_login(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

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

    # with open("linkedin_jobs.json", "w", encoding="utf-8") as f:
    #     json.dump(results, f, indent=2, ensure_ascii=False)

    filename = f"{args.keywords}_{args.location}_linkedin.xlsx".replace(" ", "_")

    df = pd.DataFrame(results)
    df.to_excel(filename, index=False)

    print(f"Saved to {filename}")

    print(f"Scraped {len(results)} jobs")
