from seleniumbase import Driver
import datetime
import random
import re
import logging
import csv
import os
import time
from urllib.parse import urlencode, quote_plus
from dotenv import load_dotenv
from selenium.webdriver.common.by import By

current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            f"scraper_ziprecruiter_unauth_{current_timestamp}.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

remote_dict = {"ALL": "", "ON-SITE": "1", "REMOTE": "2", "HYBRID": "3"}

EXCLUDE_TERMS = {"lead", "senior", "principal", "director", "vp", "vice president"}
load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
CHROME_PROFILE_DIR = os.getenv("CHROME_PROFILE_DIR")


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


def create_filename(header, title, location, mode_of_work):
    date_strf = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pos = title.replace(" ", "_")
    filename = f"Ziprecruiter_Jobs_{pos}_{location}"

    if mode_of_work != "ALL" and mode_of_work is not None:
        filename += f"_{mode_of_work}"

    filename += f"_{date_strf}.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
    return filename


class Ziprecruiter:
    BASE_URL = "https://www.ziprecruiter.com/jobs-search"

    jobs_collected = 0
    card_num = 0
    total_scraped = 0
    total_missed_card = 0
    total_skipped_title = 0
    total_skipped_easy = 0
    abort_scraping = False

    def __init__(self, headless=True, except_titles=False, exclude_easy_apply=False):
        self.headless = headless
        self.exclude_titles = except_titles
        self.exclude_easy_apply = exclude_easy_apply
        self.driver = self._setup_driver()

    def _setup_driver(self):
        """Initializes SeleniumBase UC Mode. Versioning is handled automatically."""
        # Use headless2 for better stealth if headless is requested
        return Driver(
            uc=True,
            headless2=self.headless,
            user_data_dir=CHROME_PROFILE_DIR,
            agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )

    def dismiss_popups(self):
        logging.info("Checking for pop-ups...")
        time.sleep(1)
        try:
            self.driver.send_keys("body", "\ue00c")
            logging.info("Sent Escape key.")
        except Exception as e:
            logging.error(f"Failed to dismiss popup: {e}")

    def quit(self):
        if self.driver:
            self.driver.quit()

    def extract_job_data(self, card):
        data = {
            "title": None,
            "company": None,
            "location": None,
            "salary": None,
            "mode_of_work": "Onsite",
            "link": None,
            "easy_apply": None,
            "employment_type": None,
            "description": None,
        }
        try:
            title_element = card.find_element(By.TAG_NAME, "h2")
            data["title"] = title_element.text.strip()

            logger.info(f"Processing card #{self.card_num}: {data['title']}")

            if should_exclude_job(data["title"], EXCLUDE_TERMS):
                logger.info(
                    f"Skipping card #{self.card_num} (Excluded Title): {data['title']}"
                )
                self.total_skipped_title += 1
                return None

            try:
                data["company"] = card.find_element(
                    By.CSS_SELECTOR, "a[data-testid='job-card-company']"
                ).text
            except Exception as e:
                logger.warning(f"Company name not found for card #{self.card_num}: {e}")
                data["company"] = "N/A"

            try:
                # 1. Use By.CSS_SELECTOR and then By.XPATH for the parent
                loc_element = card.find_element(
                    By.CSS_SELECTOR, "[data-testid='job-card-location']"
                )
                loc_container = loc_element.find_element(By.XPATH, "..")

                full_text = loc_container.text
                data["location"] = loc_element.text
            except Exception as e:
                logger.warning(f"Location not found for card #{self.card_num}: {e}")
                data["location"] = "N/A"
                full_text = ""

            try:
                data["salary"] = card.find_element(
                    By.XPATH, ".//p[contains(text(), '$')]"
                ).text
            except Exception:
                data["salary"] = None
                logger.info(f"Salary not found for card #{self.card_num}")

            if "Remote" in full_text:
                data["mode_of_work"] = "Remote"
            elif "Hybrid" in full_text:
                data["mode_of_work"] = "Hybrid"
            else:
                data["mode_of_work"] = "Onsite"

            try:
                card.find_element(By.CSS_SELECTOR, "button[aria-label^='View']").click()
                time.sleep(random.uniform(1.5, 2.5))
            except Exception as e:
                logger.error(f"Failed to click job card #{self.card_num}: {e}")
                self.total_missed_card += 1
                return None

            try:
                self.driver.wait_for_element(
                    "[data-testid='job-details-scroll-container']", timeout=5
                )
                data["description"] = self.driver.get_text(
                    "[data-testid='job-details-scroll-container']"
                )
            except Exception as e:
                logger.warning(f"Description not found for card #{self.card_num}: {e}")
                data["description"] = "N/A"

            apply_element = self.driver.find_element("[aria-label*='Apply']")
            apply_text = apply_element.text.strip().lower()
            data["easy_apply"] = True if "quick apply" in apply_text else False

            try:
                data["link"] = apply_element.get_attribute("href")
                logger.info(f"link found is: {data['link']} for card #{self.card_num}")
                if data["link"] is None:
                    raise Exception("Apply button does not have href attribute")
            except Exception as e:
                logger.warning(
                    f"Failed to get link from Apply button for card #{self.card_num}: {e}"
                )
                try:
                    link_el = card.find_element(
                        By.CSS_SELECTOR, "a[data-testid='job-card-title'], a.job_link"
                    )
                    relative_url = link_el.get_attribute("href")

                    data["link"] = (
                        relative_url
                        if "http" in relative_url
                        else f"https://www.ziprecruiter.com{relative_url}"
                    )
                    logger.info(
                        f"Link extracted from title for card # in first attempt{self.card_num}: {data['link']}"
                    )
                    time.sleep(1)
                except Exception as e:
                    data["link"] = None

            if data["easy_apply"] and self.exclude_easy_apply:
                self.total_skipped_easy += 1
                return None

            try:
                el_selector = "[data-testid='job-details-scroll-container'] p:contains('time'), [data-testid='job-details-scroll-container'] p:contains('Contract')"
                self.driver.wait_for_element(el_selector, timeout=3)
                data["employment_type"] = self.driver.get_text(el_selector)
            except Exception:
                data["employment_type"] = "N/A"
                logger.info(f"Employment type not found for card #{self.card_num}")
            self.total_scraped += 1
            return data

        except Exception as e:
            logger.error(f"Error extracting card #{self.card_num}: {e}")
            self.total_missed_card += 1
            return None

    def _generate_url(
        self,
        search,
        location,
        zip_apply_only,
        mode_of_work,
        radius,
        days,
        min_salary,
        max_salary,
        employment_type,
        experience_level,
        page,
    ):
        params = {
            "search": search,
            "location": location,
            "radius": radius,
        }
        params["refine_by_apply_type"] = "has_zipapply" if zip_apply_only else ""
        params["refine_by_location_type"] = mode_of_work if mode_of_work else ""
        params["days"] = days if days else ""
        params["refine_by_salary"] = min_salary if min_salary else ""
        params["refine_by_salary_ceil"] = max_salary if max_salary else ""

        if employment_type is None:
            params["refine_by_employment"] = "all"
        elif employment_type == "all":
            params["refine_by_employment"] = ""
        elif employment_type:
            params["refine_by_employment"] = f"employment_type:{employment_type}"

        params["refine_by_experience_level"] = (
            ",".join(experience_level) if experience_level else ""
        )

        params["page"] = f"{page}"

        return f"{self.BASE_URL}?{urlencode(params, quote_via=quote_plus)}"

    def scraper_zip_recruiter(
        self,
        *,
        search: str,
        location: str,
        zip_apply_only: bool = False,
        mode_of_work: str | None,
        radius: int = 5000,
        days: int | None = None,
        min_salary: int | None = 0,
        max_salary: int | None = 300000,
        employment_type: str | None,
        experience_level: list[str] | None = None,
        max_jobs: int | None = None,
    ):
        header = [
            "title",
            "company",
            "location",
            "salary",
            "mode_of_work",
            "employment_type",
            "easy_apply",
            "link",
            "description",
        ]
        filename = create_filename(header, search, location, mode_of_work)
        page = 0

        try:
            while not self.abort_scraping:
                url = self._generate_url(
                    search=search,
                    location=location,
                    zip_apply_only=zip_apply_only,
                    mode_of_work=mode_of_work,
                    radius=radius,
                    days=days,
                    min_salary=min_salary,
                    max_salary=max_salary,
                    employment_type=employment_type,
                    experience_level=experience_level,
                    page=page,
                )

                self.driver.uc_open_with_reconnect(url, reconnect_time=2)
                self.dismiss_popups()

                container_selector = "section[class*='job_results_two_pane']"

                self.driver.wait_for_element(container_selector, timeout=10)

                job_cards = self.driver.find_elements(
                    f"{container_selector} > div, {container_selector} [data-testid='job-card']"
                )

                if not job_cards:
                    break

                logger.info(
                    f"Found {len(job_cards)} job cards on page {page}. Processing..."
                )
                jobs_data = []
                for card in job_cards[1:-2]:
                    self.card_num += 1
                    job_info = self.extract_job_data(card)

                    if job_info:
                        jobs_data.append(job_info)

                    if max_jobs and self.card_num >= max_jobs:
                        self.abort_scraping = True
                        break

                if jobs_data:
                    with open(filename, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=header)
                        writer.writerows(jobs_data)
                if self.abort_scraping:
                    logger.info(
                        f"Reached max jobs limit of {max_jobs}. Stopping scraper."
                    )
                    break
                logging.info(f"number of jobs read in this batch: {len(jobs_data)-3}")
                logging.info(f"[SAVED] Batch saved to {filename}")
                time.sleep(random.randint(2, 5))
                page += 1
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            if self.driver:
                logging.info(f"Total cards found: {self.card_num}")
                logging.info(f"Total cards scrape: {self.total_scraped}")
                logging.info(
                    f"Total card missed(this number do not include skipped title, and skipped easy): {self.total_missed_card}"
                )
                logging.info(f"Total cards skipped title: {self.total_skipped_title}")
                logging.info(f"Total cards skippled easy:{self.total_skipped_easy}")
                self.quit()


if __name__ == "__main__":

    logging.info("=" * 50)
    logging.info(" Welcome to Zip Recruiter Job Scraper (UnAuthentication required)")
    logging.info("=" * 50)

    title = "Software Engineer"  # prompt_required("Enter job title (e.g. software engineer): ")
    location = "USA"  # prompt_required("Enter location (e.g. USA): ")

    max_jobs_input = input(
        "Enter max number of jobs to scrape (press Enter for unlimited): "
    ).strip()
    max_jobs = int(max_jobs_input) if max_jobs_input else None

    zipapply_only_input = (
        input("Only show Easy/Quick Apply jobs? (y/n, default n): ").strip().lower()
    )
    zipapply_only = True if zipapply_only_input == "y" else False

    mode_of_work = input(
        "Enter mode (no_remote, remote, hybrid - press Enter for all): "
    ).strip()
    mode_of_work = mode_of_work if mode_of_work else None

    distance_input = input(
        "Enter search radius in miles (5, 10, 25, 50 - press Enter for default): "
    ).strip()
    distance = int(distance_input) if distance_input else 5000

    days_input = input(
        "Enter max days posted (e.g. 1, 5, 10 - press Enter for posted any time): "
    ).strip()
    days = int(days_input) if days_input else None

    min_salary_input = input(
        "Enter minimum salary (e.g. 0 - press Enter for no minimum): "
    ).strip()
    min_salary = int(min_salary_input) if min_salary_input else None

    max_salary_input = input(
        "Enter maximum salary (e.g. 100000 - press Enter for no maximum): "
    ).strip()
    max_salary = int(max_salary_input) if max_salary_input else None

    employment_type_input = input(
        "Enter employment type (all, full_time, part_time, contract, as_needed, other - press Enter for keeping it empty): "
    ).strip()
    employment_type = employment_type_input if employment_type_input else None

    exp_input = (
        input(
            "Enter experience levels (no_experience, junior, mid, senior, or type comma separated; for eg: junior, mid - press Enter for all of them): "
        )
        .strip()
        .lower()
    )
    experience_level = [e.strip() for e in exp_input.split(",")] if exp_input else None

    headless_mode = (
        input("Run in headless mode (invisible browser)? (y/n, default=n): ")
        .strip()
        .lower()
    )

    headless = not headless_mode not in ["n", "no"]

    logging.info("\nStarting scraping...")

    exclude_title = (
        input("Do you want to exclude some titles? (y/n, default=y): ").strip().lower()
    )
    exclude_title = True if exclude_title in ["y", "yes"] else False

    exclude_easy_apply = (
        input("Exclude Easy Apply jobs? (y/n, default=n): ").strip().lower()
    )
    exclude_easy_apply = True if exclude_easy_apply in ["y", "yes"] else False

    if exclude_title:
        logging.info("[FILTER] Exclude Title (invisible browser)")

    if exclude_easy_apply:
        logging.info("[FILTER] Exclude Easy Apply jobs")

    obj = Ziprecruiter(
        headless=headless,
        except_titles=True,
        exclude_easy_apply=exclude_easy_apply,
    )

    logger.info("Initialized Ziprecruiter scraper object.")
    logger.info(f"start time {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    start_time = datetime.datetime.now()
    obj.scraper_zip_recruiter(
        search=title,
        location=location,
        zip_apply_only=zipapply_only,
        mode_of_work=mode_of_work,
        radius=distance,
        days=days,
        min_salary=min_salary,
        max_salary=max_salary,
        employment_type=employment_type,
        experience_level=experience_level,
        max_jobs=max_jobs,
    )
    endtime = datetime.datetime.now() - start_time
    logger.info(f"total time taken {endtime}")
