import os
import re
import json
import time
import random
import threading
import requests
import schedule
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
JOB_CHANNEL = os.getenv("SLACK_JOB_CHANNEL_ID") or "C04N51UG7DY"
PAPER_CHANNEL = os.getenv("SLACK_CHANNEL_ID") or "C04J1LKCK1S"

app = App(token=SLACK_BOT_TOKEN)
client = WebClient(token=SLACK_BOT_TOKEN)

# -------------------------------------------------------------------------
# KAIST Job Checking
# -------------------------------------------------------------------------

TARGET_URL = (
    "https://career.kaist.ac.kr/recruit_info/lists/sc_sorting/end_date"
    "/sc_asc_desc/desc/sc_paging/20/sc_recruit_field/005%7C/sc_recruit_form/01%7C"
)
STATE_FILE = "seen_jobs.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.114 Safari/537.36"
    )
}


def load_seen_jobs():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_seen_jobs(seen_jobs):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen_jobs), f)


def send_job_message(job):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*<{job['link']}|{job['title']}>*\n\n"
                    f"*Company:* {job['company']}\n"
                    f"*Region:* {job['region']}\n"
                    f"*Dates:* {job['start_date']} ~ {job['end_date']}"
                ),
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "Click the title to view details (Login required)."}],
        },
        {"type": "divider"},
    ]
    try:
        client.chat_postMessage(channel=JOB_CHANNEL, blocks=blocks, text=f"New Job: {job['title']}")
    except SlackApiError as e:
        print(f"Error sending job message: {e.response['error']}")


def check_jobs(seen_jobs, first_run=False):
    print(f"Checking for new jobs... (seen: {len(seen_jobs)})")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS)
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

        if first_run:
            print(f"First run: marking {len(new_jobs)} jobs as seen.")
            if new_jobs:
                send_job_message(new_jobs[-1])
            save_seen_jobs(seen_jobs)
            return

        for job in new_jobs:
            send_job_message(job)
        if new_jobs:
            save_seen_jobs(seen_jobs)

    except Exception as e:
        print(f"Error checking jobs: {e}")


# -------------------------------------------------------------------------
# Google Scholar Paper Alerts
# -------------------------------------------------------------------------

PAPER_SEARCH_URLS = [
    {
        "name": "MSOM",
        "url": "https://scholar.google.com/scholar?hl=ko&as_sdt=0,5&q=source:%22Manufacturing+%26+Service+Operations+Management%22&scisbd=1",
    },
    {
        "name": "Management Science (OM)",
        "url": "https://scholar.google.com/scholar?hl=ko&scisbd=1&as_sdt=0%2C5&q=%22operations+management%22+source%3A%22Management+Science%22+source%3A%2C+source%3A%22informs%22&btnG=",
    },
    {
        "name": "Management Science (Healthcare)",
        "url": "https://scholar.google.com/scholar?hl=ko&as_sdt=0,5&q=%22healthcare+management%22+source:%22Management+Science%22+source:,+source:%22informs%22&scisbd=1",
    },
]

RANDOM_PAPER_URLS = [
    {
        "name": "Game Theory (MSOM)",
        "url": "https://scholar.google.com/scholar?start=0&q=%22game+theory%22+source:%22Manufacturing+%26+Service+Operations+Management%22&hl=ko&as_sdt=0,5",
    },
    {
        "name": "Game Theory (MS/OM)",
        "url": "https://scholar.google.com/scholar?as_q=&as_epq=%22game+theory%22%2C+%22operations+management%22&as_oq=&as_eq=&as_occt=any&as_sauthors=&as_publication=%22Management+Science%22+%2C+%22informs%22&as_ylo=&as_yhi=&hl=ko&as_sdt=0%2C5",
    },
    {
        "name": "Game Theory (Healthcare)",
        "url": "https://scholar.google.com/scholar?as_q=%22healthcare+management%22&as_epq=game+theory&as_oq=&as_eq=&as_occt=any&as_sauthors=&as_publication=%22Management+Science%22+%2C+%22informs%22&as_ylo=&as_yhi=&hl=ko&as_sdt=0%2C5",
    },
]

SEEN_PAPERS_FILE = "seen_papers_scholar.json"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
]


def load_seen_papers():
    if os.path.exists(SEEN_PAPERS_FILE):
        with open(SEEN_PAPERS_FILE, "r") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()


def save_seen_papers(seen_set):
    with open(SEEN_PAPERS_FILE, "w") as f:
        json.dump(list(seen_set), f)


def _parse_paper_item(item, url_config):
    title_tag = item.select_one(".gs_rt a")
    if not title_tag:
        title_tag = item.select_one(".gs_rt")
    if not title_tag:
        return None

    title = title_tag.get_text()
    link = title_tag.get("href") if title_tag.name == "a" else None

    meta_div = item.select_one(".gs_a")
    meta_text = meta_div.get_text() if meta_div else ""
    parts = re.split(r"\s+-\s+|\s+–\s+", meta_text)

    authors_str = parts[0] if parts else "Unknown Authors"
    journal_year = parts[1] if len(parts) > 1 else ""

    author_list = [a.strip() for a in authors_str.split(",")]
    formatted = []
    for auth in author_list:
        auth = auth.replace("…", "").replace("...", "").strip()
        if not auth:
            continue
        tokens = auth.split()
        if len(tokens) >= 2:
            formatted.append(f"{tokens[-1]} {''.join(t[0] for t in tokens[:-1] if t)}")
        else:
            formatted.append(auth)

    final_authors = (", ".join(formatted[:3]) + ", et al.") if len(formatted) > 3 else ", ".join(formatted)

    year = "Unknown"
    if journal_year:
        m = re.search(r"\d{4}", journal_year)
        if m:
            year = m.group(0)

    if "MSOM" in url_config["name"] or "Manufacturing" in url_config["name"]:
        journal_abbr = "MSOM"
    elif "Management Science" in url_config["name"]:
        journal_abbr = "MS"
    else:
        journal_abbr = "Unknown"

    return {
        "title": title,
        "link": link,
        "authors_display": final_authors,
        "journal_display": journal_abbr,
        "year": year,
        "category": url_config["name"],
    }


def fetch_scholar_results(url_config):
    print(f"Fetching papers: {url_config['name']}...")
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        resp = requests.get(url_config["url"], headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"Failed ({resp.status_code}): {url_config['name']}")
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select(".gs_r.gs_or.gs_scl")[:5]:
            try:
                paper = _parse_paper_item(item, url_config)
                if paper:
                    results.append(paper)
            except Exception as e:
                print(f"Error parsing paper item: {e}")
        return results
    except Exception as e:
        print(f"Error fetching {url_config['name']}: {e}")
        return []


def create_paper_blocks(paper):
    meta_line = f"{paper['authors_display']} ({paper['year']}) *{paper['journal_display']}*"
    title_line = f"<{paper['link']}|{paper['title']}>" if paper["link"] else paper["title"]
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{meta_line}\n{title_line}"}},
        {"type": "divider"},
    ]


def check_new_papers(seen_papers):
    print("Checking for new papers...")
    all_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "New Papers", "emoji": True}}
    ]
    found_any = False

    for url_config in PAPER_SEARCH_URLS:
        papers = fetch_scholar_results(url_config)
        for paper in papers:
            paper_id = paper["title"].strip().lower()
            if paper_id in seen_papers:
                continue
            seen_papers.add(paper_id)
            all_blocks.extend(create_paper_blocks(paper))
            found_any = True
        time.sleep(random.uniform(3, 7))

    if found_any:
        save_seen_papers(seen_papers)
        try:
            client.chat_postMessage(channel=PAPER_CHANNEL, blocks=all_blocks, text="New papers found!")
        except SlackApiError as e:
            print(f"Error sending paper message: {e.response['error']}")
    else:
        print("No new papers.")


def fetch_random_paper(url_config):
    print(f"Fetching random paper: {url_config['name']}...")
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    base_url = url_config["url"]
    try:
        resp = requests.get(base_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        stats_el = soup.select_one("#gs_ab_md .gs_ab_mdw") or soup.select_one(".gs_ab_mdw")
        if not stats_el:
            return None

        m = re.search(r"([\d,]+)", stats_el.get_text())
        if not m:
            return None

        total = int(m.group(1).replace(",", ""))
        if total == 0:
            return None

        effective = min(total, 980)
        rand_idx = random.randint(0, effective - 1)
        start = (rand_idx // 10) * 10
        pos = rand_idx % 10

        if "start=" in base_url:
            target_url = re.sub(r"start=\d+", f"start={start}", base_url)
        else:
            sep = "&" if "?" in base_url else "?"
            target_url = f"{base_url}{sep}start={start}"

        resp2 = requests.get(target_url, headers=headers, timeout=10)
        if resp2.status_code != 200:
            return None

        items = BeautifulSoup(resp2.text, "html.parser").select(".gs_r.gs_or.gs_scl")
        item = items[pos] if items and pos < len(items) else (items[0] if items else None)
        if not item:
            return None

        title_tag = item.select_one(".gs_rt a") or item.select_one(".gs_rt")
        if not title_tag:
            return None

        meta_div = item.select_one(".gs_a")
        return {
            "title": title_tag.get_text(),
            "link": title_tag.get("href") if title_tag.name == "a" else None,
            "meta": meta_div.get_text() if meta_div else "",
            "category": url_config["name"],
            "random_index": rand_idx,
            "total_results": total,
        }
    except Exception as e:
        print(f"Error fetching random paper: {e}")
        return None


def send_random_papers():
    print("Sending weekly random papers...")
    for url_config in RANDOM_PAPER_URLS:
        paper = fetch_random_paper(url_config)
        if not paper:
            continue
        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": f"Weekly Random Paper ({paper['category']})", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"Selected from {paper['total_results']:,} results (Index: {paper['random_index']})"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"<{paper['link']}|*{paper['title']}*>\n{paper['meta']}"}},
            {"type": "divider"},
        ]
        try:
            client.chat_postMessage(channel=PAPER_CHANNEL, blocks=blocks, text=f"Random Paper: {paper['title']}")
        except SlackApiError as e:
            print(f"Error sending random paper: {e.response['error']}")
        time.sleep(random.uniform(3, 7))


# -------------------------------------------------------------------------
# Slash Commands
# -------------------------------------------------------------------------

@app.command("/papers")
def handle_papers_command(ack, say):
    ack()
    seen = load_seen_papers()
    all_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Latest Papers", "emoji": True}}
    ]
    for url_config in PAPER_SEARCH_URLS:
        papers = fetch_scholar_results(url_config)
        for paper in papers:
            all_blocks.extend(create_paper_blocks(paper))
        time.sleep(random.uniform(2, 5))
    say(blocks=all_blocks, text="Latest papers")


@app.command("/randompaper")
def handle_random_paper_command(ack, say):
    ack()
    url_config = random.choice(RANDOM_PAPER_URLS)
    paper = fetch_random_paper(url_config)
    if not paper:
        say("Could not fetch a random paper right now.")
        return
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"Random Paper ({paper['category']})", "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"Selected from {paper['total_results']:,} results"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"<{paper['link']}|*{paper['title']}*>\n{paper['meta']}"}},
        {"type": "divider"},
    ]
    say(blocks=blocks, text=f"Random Paper: {paper['title']}")


@app.command("/jobs")
def handle_jobs_command(ack, say):
    ack()
    say("Checking for latest KAIST jobs...")
    seen = load_seen_jobs()
    check_jobs(seen, first_run=False)


# -------------------------------------------------------------------------
# Scheduler
# -------------------------------------------------------------------------

def run_scheduler(seen_jobs, seen_papers):
    schedule.every(1).minutes.do(check_jobs, seen_jobs)
    schedule.every(6).hours.do(check_new_papers, seen_papers)
    schedule.every().monday.at("09:00").do(send_random_papers)

    while True:
        schedule.run_pending()
        time.sleep(30)


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main():
    print("Starting bot (jobs + papers)...")

    seen_jobs = load_seen_jobs()
    seen_papers = load_seen_papers()

    is_first_job_run = len(seen_jobs) == 0
    check_jobs(seen_jobs, first_run=is_first_job_run)
    check_new_papers(seen_papers)

    scheduler_thread = threading.Thread(target=run_scheduler, args=(seen_jobs, seen_papers), daemon=True)
    scheduler_thread.start()

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


if __name__ == "__main__":
    main()
