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

# Configuration - Exclude Terms
EXCLUDE_TERMS = {
    "lead",
    "manager",
    "senior",
    "principal",
    "director",
    "vp",
    "vice president",
    "sr ",
    "ciso",
    "chief",
    "level 2",
    "tier 3",
    "associate director",
    "l3",
    "architecture",
    "sme",
    "architect",
    "field",
    "software developer",
    "data scientist",
    "scientist",
    "federal account executive",
    "full stack developer",
    "traveling aircraft mechanic",
    "software engineer",
    "human resources operations",
    "ii",
    "regional technical development specialist",
    "stock plan administrator",
    "commissioning authority",
    "salesforce",
    "dir",
    "consultant",
    "adjunct faculty",
    "subject matter expert",
    "staff",
}

# Non-cybersecurity job titles to exclude
NON_CYBER_TERMS = {
    "counsel",
    "attorney",
    "lawyer",
    "legal",
    "paralegal",
    "fraud",
    "compliance officer",
    "risk manager",
    "auditor",
    "hr",
    "human resources",
    "recruiter",
    "sales",
    "marketing",
    "account executive",
    "business development",
    "project manager",
    "scrum master",
    "product manager",
    "data scientist",
    "data analyst",
    "software engineer",
    "software developer",
    "full stack",
    "frontend",
    "backend",
    "devops engineer",
    "cloud engineer",
    "network engineer",
    "help desk",
    "desktop support",
    "it support",
    "system administrator",
    "intern",
    "internship",
    "triage analyst",
}

# Valid cybersecurity job title keywords (must contain at least one)
VALID_CYBER_KEYWORDS = {
    "security",
    "cybersecurity",
    "cyber security",
    "infosec",
    "information security",
    "appsec",
    "application security",
    "devsecops",
    "security engineer",
    "security analyst",
    "security architect",
    "penetration test",
    "pen test",
    "ethical hacker",
    "bug bounty",
    "vulnerability",
    "soc analyst",
    "threat",
    "incident response",
    "malware",
    "forensic",
    "security operations",
    "identity access management",
    "iam",
    "zero trust",
    "security compliance",
    "grc",
    "governance risk",
    "cissp",
    "ceh",
    "oscp",
}

# Contract/temporary job indicators
CONTRACT_TERMS = {
    "contract",
    "contractor",
    "temporary",
    "temp ",
    "freelance",
    "corp-to-corp",
    "c2c",
    "1099",
}


def prompt_required(prompt_text):
    while True:
        value = input(prompt_text).strip()
        if value:
            return value
        logging.info("This field is required. Please try again.\n")


def get_random_user_agent():
    headers = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        },
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        },
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36"
        },
    ]
    return random.choice(headers)


def has_excluded_terms(title: str, exclude_terms: set) -> bool:
    """Check if job title contains any excluded seniority terms."""
    title_lower = title.lower()
    for term in exclude_terms:
        if term.lower() in title_lower:
            return True
    return False


def is_non_cyber_job(title: str) -> bool:
    """Check if job is not cybersecurity related."""
    title_lower = title.lower()

    for term in NON_CYBER_TERMS:
        if term in title_lower:
            return True

    has_cyber_keyword = False
    for keyword in VALID_CYBER_KEYWORDS:
        if keyword in title_lower:
            has_cyber_keyword = True
            break

    return not has_cyber_keyword


def is_contract_job(title: str, description: str) -> bool:
    """Detect contract/temporary positions."""
    title_lower = title.lower()
    desc_lower = description.lower() if description else ""

    for term in CONTRACT_TERMS:
        if term in title_lower or term in desc_lower:
            return True

    return False


def has_easy_apply(job_soup) -> bool:
    """
    Enhanced Easy Apply detection using exact CSS selectors from LinkedIn DOM.

    CSS Selectors:
    - aria-label="Easy Apply to this job"
    - svg#linkedin-bug-medium
    - div._16c012dd
    """
    print(f"looking for easy apply indicators...")
    # Method 1: Exact aria-label match (HIGHEST PRIORITY)
    easy_apply_button = job_soup.find(attrs={"aria-label": "Easy Apply to this job"})
    if easy_apply_button:
        return True

    # Method 2: Partial aria-label match
    easy_apply_aria = job_soup.find(
        attrs={"aria-label": re.compile(r"Easy Apply", re.IGNORECASE)}
    )
    if easy_apply_aria:
        return True

    # Method 3: LinkedIn bug SVG icon (unique to Easy Apply)
    linkedin_bug_svg = job_soup.find("svg", id="linkedin-bug-medium")
    if linkedin_bug_svg:
        return True

    # Method 4: Specific div class _16c012dd (Easy Apply container)
    easy_apply_container = job_soup.find("div", class_="_16c012dd")
    if easy_apply_container:
        return True

    # Method 5: Check for openSDUIApplyFlow URL parameter
    easy_apply_link = job_soup.find(
        "a", href=re.compile(r"openSDUIApplyFlow=true", re.IGNORECASE)
    )
    if easy_apply_link:
        return True

    # Method 6: Text-based search
    easy_apply_text = job_soup.find(string=re.compile(r"Easy Apply", re.IGNORECASE))
    if easy_apply_text:
        parent = easy_apply_text.find_parent()
        if parent and parent.name in ["a", "button", "span"]:
            return True

    # Method 7: Check all <a> tags
    all_links = job_soup.find_all("a")
    for link in all_links:
        link_text = link.get_text(strip=True)
        if "Easy Apply" in link_text:
            return True

    return False


def generate_main_linkedin_url(keywords):
    base_url = "https://www.linkedin.com/jobs/search-results/"
    url_friendly_keywords = keywords.replace(" ", "%20")
    query_params = (
        f"?keywords={url_friendly_keywords}&origin=SEMANTIC_SEARCH_LANDING_PAGE&f_WT=2"
    )
    url_search = base_url + query_params
    logging.info(f"Main search URL: {url_search}")

    return url_search


def get_url_next_10_positions(keywords, start_position):
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    url_friendly_keywords = keywords.replace(" ", "%20")
    query_params = f"?keywords={url_friendly_keywords}&f_WT=2&position=1&pageNum=0&start={start_position}"
    return base_url + query_params


def fetch_jobs_until_success(url):
    response = requests.get(url, headers=get_random_user_agent())
    return response


def scrape_description_and_salary(job_url):
    """Fetch job description, salary, and check for Easy Apply"""
    try:
        r = fetch_jobs_until_success(job_url)
        soup = BeautifulSoup(r.text, "html.parser")

        # Check for Easy Apply
        has_easy = has_easy_apply(soup)

        # Get salary
        salary_el = soup.find("div", class_="salary compensation__salary")
        salary = salary_el.get_text(strip=True) if salary_el else None

        # Get full job description
        desc_el = soup.select_one("section.description div.show-more-less-html__markup")
        description = desc_el.get_text(separator=" ", strip=True) if desc_el else None

        return description, salary, has_easy
    except Exception as e:
        logging.error(f"Error scraping job details: {e}")
        return None, None, False


def create_file(header, keywords):
    date_strf = datetime.datetime.now().strftime("%Y-%m-%d")
    keywords_clean = keywords.replace(" ", "_")
    file_name = f"LinkedIn_Jobs_{keywords_clean}_REMOTE_{date_strf}.csv"

    with open(file_name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
    return file_name


def scrape_linkedin_jobs(keywords, max_jobs, filters):
    main_url = generate_main_linkedin_url(keywords)
    logging.info(f"Starting scrape with URL: {main_url}")

    response = fetch_jobs_until_success(main_url)
    soup = BeautifulSoup(response.text, "html.parser")

    raw_text_el = soup.find("span", {"class": "results-context-header__job-count"})
    if raw_text_el:
        raw_text = raw_text_el.get_text(strip=True)
        all_jobs = int(re.sub(r"[^\d]", "", raw_text))
        logging.info(f"Found {all_jobs} total remote jobs matching '{keywords}'")
    else:
        all_jobs = 10000
        logging.info("Could not determine total job count")

    jobs = []
    header = [
        "title",
        "company",
        "location",
        "salary",
        "description",
        "is_remote",
        "is_easy_apply",
        "is_contract",
        "link",
    ]

    file_name = create_file(header, keywords)

    stats = {
        "total_processed": 0,
        "skipped_seniority": 0,
        "skipped_easy_apply": 0,
        "skipped_contract": 0,
        "skipped_non_cyber": 0,
        "total_scraped": 0,
    }

    start_time = datetime.datetime.now()

    # Calculate multiplier
    multiplier = 1.5
    if filters.get("exclude_easy_apply"):
        multiplier += 0.5
    if filters.get("exclude_contract"):
        multiplier += 0.3
    if filters.get("exclude_seniority"):
        multiplier += 1.0
    if filters.get("cyber_only"):
        multiplier += 1.0
    multiplier = min(multiplier, 5.0)

    logging.info(f"Filter multiplier: {multiplier}x")

    page_num = 0
    consecutive_empty_pages = 0
    max_empty_pages = 3

    while stats["total_scraped"] < max_jobs:
        start_position = page_num * 10
        current_page = page_num + 1

        target_url = get_url_next_10_positions(keywords, start_position)
        logging.info(
            f"\nPage {current_page} (Need {max_jobs - stats['total_scraped']} more jobs)"
        )
        logging.info(f"Fetching URL: {target_url}")

        response = fetch_jobs_until_success(target_url)
        soup = BeautifulSoup(response.content, "html.parser")
        alljobs = soup.find_all("li")

        if not alljobs:
            consecutive_empty_pages += 1
            logging.info(f"Empty page ({consecutive_empty_pages}/{max_empty_pages})")
            if consecutive_empty_pages >= max_empty_pages:
                break
            page_num += 1
            time.sleep(random.uniform(1, 2))
            continue
        else:
            consecutive_empty_pages = 0

        for job in alljobs:
            if stats["total_scraped"] >= max_jobs:
                break

            try:
                info = job.find("div", class_="base-search-card__info")
                title = (
                    info.find("h3", class_="base-search-card__title").text.strip()
                    if info
                    else "N/A"
                )

                stats["total_processed"] += 1

                # FILTERS
                if filters.get("cyber_only") and is_non_cyber_job(title):
                    stats["skipped_non_cyber"] += 1
                    logging.info(
                        f"SKIP [{stats['total_processed']}] Non-cyber: {title[:50]}"
                    )
                    continue

                if filters.get("exclude_seniority") and has_excluded_terms(
                    title, EXCLUDE_TERMS
                ):
                    stats["skipped_seniority"] += 1
                    logging.info(
                        f"SKIP [{stats['total_processed']}] Seniority: {title[:50]}"
                    )
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

                description, salary, is_easy = scrape_description_and_salary(joburl)

                if filters.get("exclude_easy_apply") and is_easy:
                    stats["skipped_easy_apply"] += 1
                    logging.info(
                        f"SKIP [{stats['total_processed']}] Easy Apply: {title[:50]}"
                    )
                    continue

                is_contract = is_contract_job(title, description or "")
                if filters.get("exclude_contract") and is_contract:
                    stats["skipped_contract"] += 1
                    logging.info(
                        f"SKIP [{stats['total_processed']}] Contract: {title[:50]}"
                    )
                    continue

                job_info = {
                    "title": title,
                    "company": company,
                    "location": location_job,
                    "salary": salary,
                    "description": description,
                    "is_remote": "Yes",
                    "is_easy_apply": "Yes" if is_easy else "No",
                    "is_contract": "Yes" if is_contract else "No",
                    "link": joburl,
                }

                jobs.append(job_info)
                stats["total_scraped"] += 1

                logging.info(
                    f"SAVED [{stats['total_processed']}] #{stats['total_scraped']}/{max_jobs}: {title[:50]}"
                )

            except Exception as e:
                logging.error(f"Error: {e}")
                continue

        if jobs:
            with open(file_name, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writerows(jobs)
            logging.info(
                f"Batch saved: {len(jobs)} jobs (Total: {stats['total_scraped']}/{max_jobs})"
            )
            jobs = []

        page_num += 1
        time.sleep(random.uniform(1, 3))

    end_time = datetime.datetime.now()

    logging.info("\n" + "=" * 70)
    logging.info("SCRAPING COMPLETE")
    logging.info("=" * 70)
    logging.info(f"Total processed:        {stats['total_processed']}")
    logging.info(f"Total saved:            {stats['total_scraped']}/{max_jobs}")
    logging.info(f"Skipped (seniority):    {stats['skipped_seniority']}")
    logging.info(f"Skipped (Easy Apply):   {stats['skipped_easy_apply']}")
    logging.info(f"Skipped (contract):     {stats['skipped_contract']}")
    logging.info(f"Skipped (non-cyber):    {stats['skipped_non_cyber']}")
    logging.info(f"Duration:               {end_time - start_time}")
    logging.info(f"File:                   {file_name}")
    logging.info("=" * 70)


if __name__ == "__main__":
    logging.info("=" * 70)
    logging.info(" LinkedIn Remote Cybersecurity Job Scraper")
    logging.info("=" * 70)

    keywords = prompt_required("\nSearch keywords: ")
    max_jobs = int(input("Max jobs (default=50): ").strip() or "50")

    exclude_seniority = (
        input("Exclude senior/lead? (y/n, default=y): ").strip().lower() != "n"
    )
    exclude_easy_apply = (
        input("Exclude Easy Apply? (y/n, default=y): ").strip().lower() != "n"
    )
    exclude_contract = (
        input("Exclude contract? (y/n, default=y): ").strip().lower() != "n"
    )
    cyber_only = input("Cybersecurity only? (y/n, default=y): ").strip().lower() != "n"

    filters = {
        "exclude_seniority": exclude_seniority,
        "exclude_easy_apply": exclude_easy_apply,
        "exclude_contract": exclude_contract,
        "cyber_only": cyber_only,
    }

    logging.info("\n" + "=" * 70)
    logging.info(f"Keywords:           {keywords}")
    logging.info(f"Target:             {max_jobs}")
    logging.info(f"Exclude seniority:  {exclude_seniority}")
    logging.info(f"Exclude Easy Apply: {exclude_easy_apply}")
    logging.info(f"Exclude contract:   {exclude_contract}")
    logging.info(f"Cyber only:         {cyber_only}")
    logging.info("=" * 70 + "\n")

    scrape_linkedin_jobs(keywords, max_jobs, filters)
