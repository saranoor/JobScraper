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

# LinkedIn unauthenticate scraping script
1. [Limitation] in this mode the script can only scrape a max_jobs=1000
2. [Limitation] easy apply jobs may appear with apply Tags
3. [Recommendations] To get more result from max_jobs=1000
    # Split queries:
    # by f_WT (1,2,3)
    # by location granularity (state/city)
    # by time filters (f_TPR)
    # distance filters

# Linkedin Authenticate scraping script

1. [Necessary] For LinkedIn Authentication, you need to have credentials of a LinkedIn account. 
I suggest creating a new accoutn for scraping. There are chances that your account may be blocked, 
black listed, therefore, based upon my technical experience I do not recommedn using your professional 
linkedIn account. 

2. While creating your new account, I recommend sign up using email and password. Do not sing up using 
google. As the script only accepts email and password to avoid unncessary complexity of signing up with 
google.

3. [Necessary] Set email and password in .env file

3. [Necessary] Use high speed vpn. This is important as other many jobs scraping will result in timeout error. 

4. [Recommendation] Use VPN, please please do not use your ip directly. There is a chance of your IP being blocked if 
Linkedin/Glassdoor/Zip recruiter finds out a script/bot is being used.

5. [Recommendation] Create a folder for chrome profile directory. Set CHROME_PROFILE_DIR in .env . Use this folder as your browser profile instead of a fresh, temporary one. Using a custom Chrome user data directory is beneficall as the browser keeps cookies and stays logged in to LinkedIn. This would help avoid frequent Recaptcah and security questions.

6. [Necessary] Use non headless mode for the first time as while logging in there will be captcha, security question and a need to input a verification code(that you will receive on gmail)

7. [Recommendation] If everything runs perfectly one time and you have HROME_PROFILE_DIR i recommend commenting out linkedin_login(driver, EMAIL, PASSWORD)
