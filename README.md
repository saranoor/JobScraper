# LinkedIn Jobs Scraper

A simple Selenium-based Python script that logs into LinkedIn, searches jobs by **keywords** and **location**, and extracts **job title** and **job description** from the first page only.

---

## Features
- Login via LinkedIn credentials
- Manual CAPTCHA handling
- Configurable search via CLI args
- Extracts:
  - Job title
  - Job description
- Outputs structured data (JSON)

---

## Requirements
- Python 3.9+
- Google Chrome

```bash
pip install selenium webdriver-manager python-dotenv
