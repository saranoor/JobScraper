## How to Run the Glassdoor Scraper (Python Script)

### Requirements

* Python **3.11 or newer**
* Google Chrome installed
* pip
* Internet connection

---

### Step 1: Download the files

Make sure these files are in the same folder:

```
glassdoor.py
requirements.txt
```

---

### Step 2: Install required packages

Open **Terminal / Command Prompt** in that folder and run:

```bash
pip install -r requirements.txt
```

### Step 3: Run the script

In the same terminal, run:

```bash
python glassdoor.py
```
### Step 4: Enter inputs

When prompted, enter:

* **Job title** (example: `software engineer`)
* **Location** (example: `Canada`)

The script will start scraping automatically.

---

### Step 5: Output

* Results will be saved as a **CSV file** in the same folder
* Logs will be saved to:

  ```
  scraper.log
  ```

---

### Notes

* Do **not** close the browser while the script is running
* If the script stops or fails, please share the `scraper.log` file for debugging

---

### Common Issues

* If Chrome updates, rerun the script
* If the script fails, reinstall dependencies:

  ```bash
  pip install -r requirements.txt --upgrade
  ```

---
# LinkedIn Job Scraper (Unauthenticated + Authenticated)

## LinkedIn Unauthenticated Scraping Script

### Limitations
1. **[Limitation]** In this mode, the script can scrape a maximum of **`max_jobs = 1000`**.
2. **[Limitation]** Easy Apply jobs may appear with **Apply** tags.

### 🟢 Recommendations
To get more results within the `max_jobs = 1000` limit, split queries by:
- `f_WT` (1, 2, 3)
- Location granularity (country/state/city)
- Time filters (`f_TPR`)
- Distance filters

---

## LinkedIn Authenticated Scraping Script

### 🟩 Necessary
1. **[Necessary]** For LinkedIn authentication, you need credentials of a LinkedIn account.  
   I suggest creating a **new account for scraping**. There are chances your account may be blocked/blacklisted, so I do **not** recommend using your professional LinkedIn account.

2. While creating a new account, sign up using **email and password**.  
   Do **not** sign up using Google, because the script accepts **email + password** only (to avoid unnecessary complexity).

3. **[Necessary]** Set **`LINKEDIN_EMAIL`** and **`LINKEDIN_PASSWORD`** in the `.env` file.

## Environment Configuration (.env)

Create a `.env` file in the project root with the following values:

```env
# LinkedIn credentials (use a dedicated scraping account)
EMAIL=your_linkedin_email@example.com
PASSWORD=your_linkedin_password

# Chrome profile directory (absolute path recommended)
CHROME_PROFILE_DIR=C:\<xxxxx>\linkedin_profile
```

4. **[Necessary]** Use a **high-speed VPN**. This is important because long scraping runs can otherwise result in timeout errors.

5. **[Necessary]** Use **non-headless mode** the first time.  
   During login you may face:
   - CAPTCHA
   - Security questions
   - Verification code (sent to your email)

### 🟥 Recommended
6. **[Recommendation]** Use a VPN and do **not** use your direct IP. There is a chance your IP may be blocked if LinkedIn/Glassdoor/ZipRecruiter detects bot activity.

7. **[Recommendation]** Create a folder for your Chrome profile directory and set **`CHROME_PROFILE_DIR`** in `.env`.  
   This makes Chrome reuse the same profile (cookies/session) instead of a fresh temporary one, helping reduce CAPTCHA/security prompts and keeping you logged in. Please see step 3.

8. **[Recommendation]** If everything runs perfectly once and you have `CHROME_PROFILE_DIR` set, consider commenting out:
   ```python
   linkedin_login(driver, EMAIL, PASSWORD)
