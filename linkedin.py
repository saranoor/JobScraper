# Import relevant packages
import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import random
import math
import re

time_posted_dict = {
    'ALL': '',
    'MONTH': 'r2592000',
    'WEEK': 'r604800',
    'DAY': 'r86400'
}
remote_dict = {
    'ALL': '',
    'ON-SITE': '1',
    'REMOTE': '2',
    'HYBRID': '3'
}

def get_random_user_agent():

    headers = [
        {'User-Agent': 'Mozilla/5.0'},
        {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36'},
        {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36'},
        {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36'},
        {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36'}
    ]

    selected_header = random.choice(headers)
    return selected_header

def generate_main_linkedin_url(position, location, distance=10, time_posted='ALL', remote='ALL'):
   
    # Base URL for LinkedIn job search
    base_url = 'https://www.linkedin.com/jobs/search/'
    
    # Replace spaces in position with URL encoding
    url_friendly_position = position.replace(" ", "%20")
    
    # Construct the query parameters
    query_params = f'?keywords={url_friendly_position}&location={location}'
    
    if distance:
        query_params += f'&distance={distance}'
    if time_posted:
        time_posted_value = time_posted_dict.get(time_posted, '')
        query_params += f'&f_TPR={time_posted_value}'
    if remote:
        remote_value = remote_dict.get(remote, '')
        query_params += f'&f_WT={remote_value}'
    
    # Combine base URL with query parameters
    url_search = base_url + query_params
    print(f"url search: {url_search}")
    return url_search
    
position = 'Data Scientist'
location = 'Canada'
time_posted = 'ALL'
remote = 'ALL'

header = get_random_user_agent()

main_url = generate_main_linkedin_url(position, location,time_posted=time_posted, remote=remote)

def fetch_jobs_until_success(url):
    got_200 = False
    # while not got_200:
    response = requests.get(url, headers=get_random_user_agent())
        # got_200 = response.status_code == 200
    return response

response = fetch_jobs_until_success(main_url)
print(response)
soup = BeautifulSoup(response.text, 'html.parser')
raw_text = soup.find(
    'span',
    {'class': 'results-context-header__job-count'}
).get_text(strip=True)

all_jobs = int(re.sub(r'[^\d]', '', raw_text))
# all_jobs = int(soup.find('span', {'class': 'results-context-header__job-count'}).text)
print(f'There are a total of {all_jobs} jobs that will be scraped based on the given conditions.')

def get_url_next_10_positions(position, location,start_position, distance=10, time_posted='ALL', remote='ALL'):
   
    # Base URL for LinkedIn job search
    base_url = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
    
    # Replace spaces in position with URL encoding
    url_friendly_position = position.replace(" ", "%20")
    
    # Construct the query parameters
    query_params = f'?keywords={url_friendly_position}&location={location}'
    
    if distance:
        query_params += f'&distance={distance}'
    if time_posted:
        time_posted_value = time_posted_dict.get(time_posted, '')
        query_params += f'&f_TPR={time_posted_value}'
    if remote:
        remote_value = remote_dict.get(remote, '')
        query_params += f'&f_WT={remote_value}'
    query_params += f'&position=1&pageNum=0&start={start_position}'
    
    # Combine base URL with query parameters
    url_search = base_url + query_params
    
    return url_search

jobs = []
total_pages = math.ceil(all_jobs/10)
for i in range(0,all_jobs, 10):
    
    current_page = i/10+1
    target_url = get_url_next_10_positions(position, location,i,time_posted=time_posted,remote=remote)
    print(f"taget url: {target_url}")
    response = fetch_jobs_until_success(target_url)
    print(f"response status: {response.status_code}")
    print(f"Parsing data for page: {int(current_page)}/{total_pages}")
    
    soup = BeautifulSoup(response.content, 'html.parser')
    alljobs = soup.find_all('li')

    for job in alljobs:
        try:
            info = job.find('div', class_="base-search-card__info")
            title = info.find('h3', class_="base-search-card__title").text.strip() if info else 'N/A'
            company = info.find('h4', class_="base-search-card__subtitle").text.strip() if info else 'N/A'

            metadata = job.find('div', class_="base-search-card__metadata")
            location_element = metadata.find('span', class_="job-search-card__location") if metadata else None
            location_job = location_element.text.strip() if location_element else 'N/A'

            joburl_element = job.find('a', class_="base-card__full-link")
            joburl = joburl_element['href'] if joburl_element else 'N/A'

            job_info = {
                'Location': location_job,
                'Title': title,
                'Company': company,
                'Url': joburl
            }

            jobs.append(job_info)

        except Exception as e:
            print(f"Error processing job: {e}")
            continue

df_jobs = pd.DataFrame(jobs, columns=['Location', 'Title', 'Company', 'Url'])
df_jobs.replace("N/A", pd.NA, inplace=True)
df_jobs = df_jobs.dropna()

# Export DataFrame to CSV
date = datetime.datetime.now().strftime('%Y-%m-%d')
position = position.replace(" ", "_")
# Start with the base file name
file_name = f'LinkedIn_Jobs_{position}_{location}'

if time_posted != 'ALL':
    file_name += f'_LAST_{time_posted}'

# Append remote if it's not 'ALL'
if remote != 'ALL':
    file_name += f'_{remote}'

# Append the date to the file name
file_name += f'_{date}.csv'

# Export DataFrame to CSV
df_jobs.to_csv(file_name, index=False)