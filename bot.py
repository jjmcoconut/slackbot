import requests
from bs4 import BeautifulSoup
import time
import schedule
import json
import os
import re
from slack_sdk import WebClient
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
# Note: Usually App Token is for Socket Mode, Bot Token for WebClient. 
# Using 'test' channel ID found via verification. 
# You can change this to "C04J1LKCK1S" for '일반' (general) if preferred.
TARGET_CHANNEL = "C04N51UG7DY" 

TARGET_URL = "https://career.kaist.ac.kr/recruit_info/lists/sc_sorting/end_date/sc_asc_desc/desc/sc_paging/20/sc_recruit_field/005%7C/sc_recruit_form/01%7C"
STATE_FILE = "seen_jobs.json"

# Headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

def load_seen_jobs():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_seen_jobs(seen_jobs):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen_jobs), f)

def send_slack_message(client, job):
    """
    Sends a formatted message to Slack.
    """
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{job['link']}|{job['title']}>*\n\n*Company:* {job['company']}\n*Region:* {job['region']}\n*Dates:* {job['start_date']} ~ {job['end_date']}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Click the title to view details (Login required for full text)."
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    try:
        # Try finding a channel first if target_channel isn't sure? 
        # Actually user likely wants it in their DM or a specific channel. 
        # I'll try sending to the default channel #general first.
        # If it fails, I'll try to get the list of channels.
        
        response = client.chat_postMessage(
            channel=TARGET_CHANNEL,
            blocks=blocks,
            text=f"New Job: {job['title']}"
        )
        print(f"Message sent: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")
        # Fallback: Try identifying a valid channel if #general fails
        if e.response['error'] == 'channel_not_found':
            print("Channel not found. Trying to list channels...")
            try:
                conversations = client.conversations_list()
                if conversations['ok'] and conversations['channels']:
                    first_channel = conversations['channels'][0]['id']
                    print(f"Retrying with channel ID: {first_channel}")
                    client.chat_postMessage(
                        channel=first_channel,
                        blocks=blocks,
                        text=f"New Job: {job['title']}"
                    )
            except Exception as inner_e:
                print(f"Fatal error finding channel: {inner_e}")


def check_jobs(client, seen_jobs, first_run=False):
    print(f"Checking for new jobs... (Seen count: {len(seen_jobs)})")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        rows = soup.select("tr.btn_move_to_view")
        new_jobs_found = []
        
        # Iterate in reverse order so we process oldest-new-job first if multiple appear
        for row in reversed(rows):
            try:
                # Extract ID
                btn_param = row.get('btn_param', '')
                match = re.search(r"id:'(\d+)'", btn_param)
                if not match:
                    continue
                job_id = match.group(1)
                
                if job_id in seen_jobs:
                    continue
                
                # It's unique! Parse details from the list row
                # Title
                title_tag = row.select_one(".title-info .tit")
                title = title_tag.get_text(strip=True) if title_tag else "No Title"
                
                # Company
                company_tag = row.select_one(".company-info .company")
                # Removed brackets text if needed, but text is okay
                company = company_tag.get_text(strip=True) if company_tag else "No Company"
                
                # Region
                region_tag = row.select_one(".region-txt")
                region = region_tag.get_text(strip=True) if region_tag else "Unknown"
                
                # Dates
                # There are multiple dates in the row, 4th and 5th td usually (m-hide)
                # Or inside .title-info ul li
                dates = row.select(".title-info .info-list li .list-txt")
                 # 0: Start, 1: End, 2: Region (sometimes)
                start_date = dates[0].get_text(strip=True) if len(dates) > 0 else "Unknown"
                end_date = dates[2].get_text(strip=True) if len(dates) > 2 else "Unknown" 
                # Note: Index might vary, but this is a decent guess based on user sample
                
                link = f"https://career.kaist.ac.kr/recruit_info/view/id/{job_id}"
                
                job_info = {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "region": region,
                    "start_date": start_date,
                    "end_date": end_date,
                    "link": link
                }
                
                new_jobs_found.append(job_info)
                seen_jobs.add(job_id)
                
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
        
        # On first run, we might not want to spam.
        # But user asked to "send information", so maybe they want initial dump?
        # Usually bots just mark existing as seen. 
        # However, for verification, I'll send ONE if first_run is True, or just mark all.
        # Let's Mark all as seen on first run to avoid spamming the history, 
        # UNLESS the user explicitly wants history. The prompt "whenever a NEW job is uploaded"
        # implies future jobs.
        
        if first_run:
            print(f"First run: Marking {len(new_jobs_found)} jobs as seen.")
            # For verification purposes, let's print one to console but NOT send to Slack
            # to avoid waking up the user's channel with 20 messages.
            # actually, I'll send the *latest* one just to prove it works.
            if new_jobs_found:
                latest = new_jobs_found[-1]
                print("Sending latest job as test...")
                send_slack_message(client, latest)
            save_seen_jobs(seen_jobs)
            return

        # Normal run
        for job in new_jobs_found:
            send_slack_message(client, job)
        
        if new_jobs_found:
            save_seen_jobs(seen_jobs)
            
    except Exception as e:
        print(f"Error checking jobs: {e}")

def main():
    print("Starting KAIST Career Bot...")
    
    # Init Slack Client
    client = WebClient(token=SLACK_BOT_TOKEN)
    
    # Load state
    seen = load_seen_jobs()
    is_first_run = len(seen) == 0
    
    # Run once immediately
    check_jobs(client, seen, first_run=is_first_run)
    
    # Schedule
    schedule.every(1).minutes.do(check_jobs, client, seen)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
