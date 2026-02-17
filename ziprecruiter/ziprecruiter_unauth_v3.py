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
import sys
import winsound

frequency = 1000
duration = 500
current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

logging.basicConfig(
    level=logging.DEBUG,
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
    "intern",
    "internship",
}

REMOTE_PATTERN = r"(Remote(?:\s*\(([^)]+)\))?)"

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


def should_exclude_job(title: str, exclude_terms: set) -> bool:
    """Check if job title contains any excluded terms."""
    title_lower = title.lower()
    for term in exclude_terms:
        if term in title_lower:
            return True
    return False


def determine_work_mode(location_text: str, description_text: str):
    modes = []
    remote_match = re.search(REMOTE_PATTERN, location_text, re.IGNORECASE)

    if remote_match or "#li-remote" in description_text.lower():
        modes.append(remote_match.group(0) if remote_match else "Remote")

    if "hybrid" in location_text.lower() or "hybrid" in description_text.lower():
        modes.append("Hybrid")

    if (
        "onsite" in location_text.lower()
        or "on-site" in location_text.lower()
        or "onsite" in description_text.lower()
        or "on-site" in description_text.lower()
    ):
        modes.append("Onsite")

    if not modes:
        return "Onsite"

    winsound.Beep(frequency, duration)
    print(f"Determined work modes: {modes} for location text: '{location_text}'")
    return " / ".join(modes)


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

    def __init__(
        self,
        headless=True,
        except_titles=False,
        exclude_easy_apply=False,
    ):
        self.headless = headless
        self.exclude_titles = except_titles
        self.exclude_easy_apply = exclude_easy_apply
        logger.info(
            f"Initializing Ziprecruiter scraper with headless={self.headless}, exclude_titles={self.exclude_titles}, exclude_easy_apply={self.exclude_easy_apply}"
        )
        self.driver = self._setup_driver()

    def _setup_driver(self):
        """Initializes SeleniumBase UC Mode. Versioning is handled automatically."""
        logger.info("Setting up SeleniumBase driver in UC mode...")
        try:
            driver = Driver(
                uc=True,
                headless2=self.headless,
                user_data_dir=CHROME_PROFILE_DIR,
            )
            driver.maximize_window()
            logger.info("Driver successfully initialized.")
            return driver
        except Exception as e:
            logger.info(f"\n[!] Driver failed to start: {e}")
            try:
                logger.info(
                    "[!] Retrying connection with automatic version matching..."
                )
                driver = Driver(uc=True, headless=self.headless)
                driver.maximize_window()
                logger.info("[✓] Driver connected successfully on retry.")
                return driver
            except Exception as final_error:
                logger.info(f"\nCritical Failure: Could not connect to Chrome...")
                logger.info(
                    f"An error occurred while setting up the driver: {final_error}"
                )
                logger.info(
                    "Suggest: Run 'pip install -U seleniumbase' to sync drivers."
                )
                sys.exit(1)

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
                loc_element = card.find_element(
                    By.CSS_SELECTOR, "[data-testid='job-card-location']"
                )
                loc_container = loc_element.find_element(By.XPATH, "..")

                full_text = loc_container.text
                data["location"] = loc_element.text
            except Exception as e:
                loc_container = None
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
                data["description"] = ""

            # although if we work_of_model is "only_remote" ziprecuriter it is naturally expected to show remote only jobs,
            # however, we have found some jobs that are either not remote or remote as well hybrid/onsite but they are still showing up,
            # so this is also applied when the mode of work is remote, to make sure we are getting the correct mode of work for each job
            data["mode_of_work"] = determine_work_mode(full_text, data["description"])

            apply_element = self.driver.find_element("[aria-label*='Apply']")
            apply_text = apply_element.text.strip().lower()
            data["easy_apply"] = True if "quick apply" in apply_text else False

            try:
                data["link"] = apply_element.get_attribute("href")
                if not data["link"]:
                    link_selectors = [
                        (By.CSS_SELECTOR, "[data-testid='job-card-title']"),
                        (By.CSS_SELECTOR, ".job_link"),
                        (By.CSS_SELECTOR, "a[data-testid='job-card-company']"),
                    ]
                    for selector_type, selector_val in link_selectors:
                        try:
                            link_el = card.find_element(selector_type, selector_val)
                            raw_url = link_el.get_attribute("href")
                            if raw_url:
                                data["link"] = (
                                    raw_url
                                    if "http" in raw_url
                                    else f"https://www.ziprecruiter.com{raw_url}"
                                )
                                logger.info(
                                    f"Link found via {selector_val} for card #{self.card_num}"
                                )
                                break
                        except Exception:
                            logger.info(
                                f"Trying next selector for link extraction for card #{selector_val}..."
                            )
                            continue
            except Exception as e:
                logger.error(
                    f"Failed to get link from Apply button for card #{self.card_num}: {e}"
                )

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
        employment_type,
        page,
    ):
        params = {
            "search": search,
            "location": location,
        }
        params["refine_by_apply_type"] = "has_zipapply" if zip_apply_only else ""
        # params["refine_by_location_type"] = mode_of_work if mode_of_work else ""
        params["refine_by_location_type"] = (
            "only_remote" if mode_of_work == "remote" else (mode_of_work or "")
        )

        params["refine_by_employment"] = f"employment_type:{employment_type}"

        params["page"] = f"{page}"

        return f"{self.BASE_URL}?{urlencode(params, quote_via=quote_plus)}"

    def scraper_zip_recruiter(
        self,
        *,
        search: str,
        location: str,
        zip_apply_only: bool = False,
        mode_of_work: str | None,
        employment_type: str | None,
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
                if max_jobs and self.total_scraped >= max_jobs:
                    logger.info(f"Reached target goal of {max_jobs} jobs. Stopping.")
                    break
                url = self._generate_url(
                    search=search,
                    location=location,
                    zip_apply_only=zip_apply_only,
                    mode_of_work=mode_of_work,
                    employment_type=employment_type,
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
                    logger.info(
                        f"No job cards found on page {page}. Assuming end of results."
                    )
                    break

                logger.info(
                    f"Found {len(job_cards)} job cards on page {page}. Processing..."
                )
                jobs_data = []
                for card in job_cards[1:-2]:
                    if max_jobs and self.total_scraped >= max_jobs:
                        self.abort_scraping = True
                        break
                    self.card_num += 1
                    job_info = self.extract_job_data(card)

                    if job_info:
                        jobs_data.append(job_info)

                if jobs_data:
                    with open(filename, "a", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=header)
                        writer.writerows(jobs_data)
                    logger.info(
                        f"Saved {len(jobs_data)} jobs from page {page}. Total: {self.total_scraped}"
                    )
                logging.info(f"number of jobs read in this batch: {len(jobs_data)}")
                logging.info(
                    f"Total number of jobs scraped so far: {self.total_scraped}"
                )
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

    location = "USA"
    title = prompt_required("Enter job title (e.g. software engineer): ")

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

    headless_mode = (
        input("Run in headless mode (invisible browser)? (y/n, default=n): ")
        .strip()
        .lower()
    )

    headless = False  # headless_mode not in ["n", "no"]

    logging.info("\nStarting scraping...")

    exclude_title = (
        input("Do you want to exclude some titles? (y/n, default=y): ").strip().lower()
    )
    exclude_title = True if exclude_title in ["y", "yes"] else False

    exclude_easy_apply = (
        input("Exclude Easy Apply/Zip Apply jobs? (y/n, default=n): ").strip().lower()
    )
    exclude_easy_apply = True if exclude_easy_apply in ["y", "yes"] else False

    if exclude_title:
        logging.info("[FILTER] Exclude Title")

    if exclude_easy_apply:
        logging.info("[FILTER] Exclude Easy Apply jobs")

    if mode_of_work and mode_of_work.lower() == "remote":
        logger.info("[FILTER] Remote jobs only")

    obj = Ziprecruiter(
        headless=headless,
        except_titles=exclude_title,
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
        employment_type="full_time",
        max_jobs=max_jobs,
    )
    endtime = datetime.datetime.now() - start_time
    logger.info(f"total time taken {endtime}")
