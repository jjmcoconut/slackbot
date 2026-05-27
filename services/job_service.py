import os
import re
import json
import requests
from bs4 import BeautifulSoup
from config import KAIST_JOB_URL, JOB_STATE_FILE, USER_AGENTS
import random

def load_seen_jobs():
    if os.path.exists(JOB_STATE_FILE):
        try:
            with open(JOB_STATE_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen_jobs):
    with open(JOB_STATE_FILE, "w") as f:
        json.dump(list(seen_jobs), f)

def check_new_jobs(seen_jobs):
    print(f"Checking for new jobs... (seen: {len(seen_jobs)})")
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    try:
        response = requests.get(KAIST_JOB_URL, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("tr.btn_move_to_view")
        new_jobs = []

        for row in reversed(rows):
            try:
                btn_param = row.get("btn_param", "")
                match = re.search(r"id:'(\d+)'", btn_param)
                if not match:
                    continue
                job_id = match.group(1)
                if job_id in seen_jobs:
                    continue

                title = (row.select_one(".title-info .tit") or "").get_text(strip=True) if row.select_one(".title-info .tit") else "No Title"
                company = row.select_one(".company-info .company")
                company = company.get_text(strip=True) if company else "No Company"
                region = row.select_one(".region-txt")
                region = region.get_text(strip=True) if region else "Unknown"
                dates = row.select(".title-info .info-list li .list-txt")
                start_date = dates[0].get_text(strip=True) if len(dates) > 0 else "Unknown"
                end_date = dates[2].get_text(strip=True) if len(dates) > 2 else "Unknown"

                job_info = {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "region": region,
                    "start_date": start_date,
                    "end_date": end_date,
                    "link": f"https://career.kaist.ac.kr/recruit_info/view/id/{job_id}",
                }
                new_jobs.append(job_info)
                seen_jobs.add(job_id)
            except Exception as e:
                print(f"Error parsing job row: {e}")
                
        return new_jobs
    except Exception as e:
        print(f"Error checking jobs: {e}")
        return []
