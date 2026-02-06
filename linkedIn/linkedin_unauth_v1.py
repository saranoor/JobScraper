# Import relevant packages
import requests
from bs4 import BeautifulSoup
import datetime
import random
import math
import re
import time
import csv
import logging

current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            f"scraper_linkedin_unauth_{current_timestamp}.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

remote_dict = {"ALL": "", "ON-SITE": "1", "REMOTE": "2", "HYBRID": "3"}

EXCLUDE_TERMS = {
    "lead",
    "senior",
    "principal",
    "director",
    "vp",
    "vice president",
    # 'sr ', 'ciso', 'chief', 'level 2', 'tier 3', 'associate director', 'l3',
    # 'architecture', 'sme', 'architect', 'field', 'software developer',
    # 'data scientist', 'scientist', 'federal account executive',
    # 'full stack developer', 'traveling aircraft mechanic', 'software engineer',
    # 'human resources operations', 'ii', 'regional technical development specialist',
    # 'stock plan administrator', 'commissioning authority', 'salesforce', 'dir',
    # 'consultant'
}


def prompt_required(prompt_text):
    while True:
        value = input(prompt_text).strip()
        if value:
            return value
        logging.info("This field is required. Please try again.\n")


def get_random_user_agent():

    headers = [
        {"User-Agent": "Mozilla/5.0"},
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"
        },
        {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36"
        },
        {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36"
        },
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"
        },
    ]

    selected_header = random.choice(headers)
    return selected_header


def should_exclude_job(title: str, exclude_terms: set) -> bool:
    """Check if job title contains any excluded terms."""
    title_lower = title.lower()
    for term in exclude_terms:
        if term in title_lower:
            return True
    return False


def generate_main_linkedin_url(position, location, remote, distance):

    # Base URL for LinkedIn job search
    base_url = "https://www.linkedin.com/jobs/search/"

    # Replace spaces in position with URL encoding
    url_friendly_position = position.replace(" ", "%20")

    # Construct the query parameters
    query_params = f"?keywords={url_friendly_position}&location={location}"

    if distance:
        query_params += f"&distance={distance}"

    if remote:
        remote_value = remote_dict.get(remote, "")
        query_params += f"&f_WT={remote_value}"

    # Combine base URL with query parameters
    url_search = base_url + query_params
    logging.info(f"url search: {url_search}")
    return url_search


def fetch_jobs_until_success(url):
    response = requests.get(url, headers=get_random_user_agent())
    return response


def get_url_next_10_positions(position, location, start_position, remote="ALL"):

    # Base URL for LinkedIn job search
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    # Replace spaces in position with URL encoding
    url_friendly_position = position.replace(" ", "%20")

    # Construct the query parameters
    query_params = f"?keywords={url_friendly_position}&location={location}"

    if distance:
        query_params += f"&distance={distance}"

    if remote:
        remote_value = remote_dict.get(remote, "")
        query_params += f"&f_WT={remote_value}"
    query_params += f"&position=1&pageNum=0&start={start_position}"

    # Combine base URL with query parameters
    url_search = base_url + query_params

    return url_search


def scrape_description_and_salary(headers, job_url):
    r = fetch_jobs_until_success(job_url)

    soup = BeautifulSoup(r.text, "html.parser")
    salary_el = soup.find("div", class_="salary compensation__salary")
    salary = salary_el.get_text(strip=True) if salary_el else None

    # Job description (FULL text, even when "Show more" exists)
    desc_el = soup.select_one("section.description div.show-more-less-html__markup")
    description = desc_el.get_text(separator=" ", strip=True) if desc_el else None

    return description, salary


def create_file(header, position, remote, location):
    date_strf = datetime.datetime.now().strftime("%Y-%m-%d")
    pos = position.replace(" ", "_")
    # Start with the base file name
    file_name = f"LinkedIn_Jobs_{pos}_{location}"

    # Append remote if it's not 'ALL'
    if remote != "ALL":
        file_name += f"_{remote}"

    # Append the date to the file name
    file_name += f"_{date_strf}.csv"
    with open(file_name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
    return file_name


def scrape_linkedin_jobs(position, location, remote, max_jobs, distance):
    # header = get_random_user_agent()
    main_url = generate_main_linkedin_url(position, location, remote, distance)
    logging.info(f"main_url: {main_url}")
    response = fetch_jobs_until_success(main_url)
    soup = BeautifulSoup(response.text, "html.parser")
    raw_text = soup.find(
        "span", {"class": "results-context-header__job-count"}
    ).get_text(strip=True)

    all_jobs = int(re.sub(r"[^\d]", "", raw_text))
    logging.info(
        f"There are a total of {all_jobs} jobs that will be scraped based on the given conditions."
    )

    jobs = []
    total_pages = math.ceil(all_jobs / 10)

    header = [
        "title",
        "company",
        "location",
        "salary",
        "description",
        "is_remote",
        "link",
    ]

    file_name = create_file(header, position, remote, location)

    total_skipped_title = 0

    start_time = datetime.datetime.now()

    for i in range(0, max_jobs, 10):
        current_page = i / 10 + 1
        target_url = get_url_next_10_positions(position, location, i, remote)
        logging.info(f"taget url: {target_url}")
        response = fetch_jobs_until_success(target_url)
        logging.info(f"Parsing data for page: {int(current_page)}/{total_pages}")

        soup = BeautifulSoup(response.content, "html.parser")
        alljobs = soup.find_all("li")

        for job in alljobs:
            start_time_for_this_job = datetime.datetime.now()
            try:
                info = job.find("div", class_="base-search-card__info")
                title = (
                    info.find("h3", class_="base-search-card__title").text.strip()
                    if info
                    else "N/A"
                )
                if exclude_titles and should_exclude_job(title, EXCLUDE_TERMS):
                    total_skipped_title += 1
                    logging.info(f"[SKIP-TITLE] {title} (Total: {total_skipped_title})")
                    continue
                company = (
                    info.find("h4", class_="base-search-card__subtitle").text.strip()
                    if info
                    else "N/A"
                )

                metadata = job.find("div", class_="base-search-card__metadata")
                location_element = (
                    metadata.find("span", class_="job-search-card__location")
                    if metadata
                    else None
                )
                location_job = (
                    location_element.text.strip() if location_element else "N/A"
                )

                joburl_element = job.find("a", class_="base-card__full-link")
                joburl = joburl_element["href"] if joburl_element else "N/A"
                description, salary = scrape_description_and_salary(header, joburl)
                job_info = {
                    "title": title,
                    "company": company,
                    "location": location_job,
                    "salary": salary,
                    "description": description,
                    "is_remote": "Yes" if remote == "REMOTE" else "NO",
                    "link": joburl,
                }

                jobs.append(job_info)
            #
            except Exception as e:
                logging.info(f"Error processing job: {e}")
                continue
            end_time_for_this_job = datetime.datetime.now()
            print(
                "Duration: {}".format(end_time_for_this_job - start_time_for_this_job)
            )
        # write it to csv file
        if jobs:
            with open(file_name, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writerows(jobs)
            jobs = []
            logging.info(f"[SAVED] Batch saved to {file_name}")
            time.sleep(1)

    end_time = datetime.datetime.now()
    print("Duration: {}".format(end_time - start_time))


if __name__ == "__main__":

    logging.info("=" * 50)
    logging.info(
        " Welcome to LinkedIN Job Scraper(unauthenticated version/guest version)"
    )
    logging.info("=" * 50)

    title = prompt_required("Enter job title (e.g. software engineer): ")

    location = prompt_required("Enter location (e.g. Canada): ")

    max_jobs_input = input(
        "Out of 1000, Enter max number of jobs to scrape (press Enter for 1000): "
    ).strip()

    max_jobs = int(max_jobs_input) if max_jobs_input else 1000

    # Ask if they want to exclude certain job titles
    exclude_titles = input(
        "Exclude senior/manager/lead positions? (y/n, default=n): "
    ).strip().lower() in ["y", "yes"]

    # Ask if what type of jobs they want
    remote = prompt_required("Type of job? (ALL/ON-SITE/REMOTE/HYBRID, default=ALL): ")

    # Ask for distance
    distance_input = input(
        "Enter distance in miles (e.g. 5, 10, 25, 50, 100 — press Enter for ALL): "
    ).strip()

    distance = int(distance_input) if distance_input else None

    logging.info("\nStarting scraping as a guest(unauthenticated)...")

    if exclude_titles:
        logging.info("[FILTER] Filtering out senior/manager/lead positions")
    if remote == "REMOTE":
        logging.info("[FILTER] Remote jobs only")
    logging.info(f"remote: {remote}")

    scrape_linkedin_jobs(title, location, remote, max_jobs, distance)
