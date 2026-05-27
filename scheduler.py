import time
import random
import schedule
from slack_sdk.errors import SlackApiError
from config import CHANNEL, PAPER_SEARCH_URLS, RANDOM_PAPER_URLS
from services.job_service import check_new_jobs, load_seen_jobs, save_seen_jobs
from services.paper_service import fetch_scholar_results, load_seen_papers, save_seen_papers, fetch_random_paper
from slack_handlers import send_job_message, create_paper_blocks

def job_check_task(client):
    seen_jobs = load_seen_jobs()
    new_jobs = check_new_jobs(seen_jobs)
    for job in new_jobs:
        send_job_message(client, job)
    if new_jobs:
        save_seen_jobs(seen_jobs)

def paper_check_task(client):
    print("Checking for new papers...")
    seen_papers = load_seen_papers()
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
            client.chat_postMessage(channel=CHANNEL, blocks=all_blocks, text="New papers found!")
        except SlackApiError as e:
            print(f"Error sending paper message: {e.response['error']}")
    else:
        print("No new papers.")

def random_paper_task(client):
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
            client.chat_postMessage(channel=CHANNEL, blocks=blocks, text=f"Random Paper: {paper['title']}")
        except SlackApiError as e:
            print(f"Error sending random paper: {e.response['error']}")
        time.sleep(random.uniform(3, 7))

def run_scheduler(client):
    schedule.every(1).minutes.do(job_check_task, client)
    schedule.every(6).hours.do(paper_check_task, client)
    schedule.every().monday.at("09:00").do(random_paper_task, client)

    while True:
        schedule.run_pending()
        time.sleep(30)
