import time
import random
from slack_sdk.errors import SlackApiError
from config import CHANNEL, PAPER_SEARCH_URLS, RANDOM_PAPER_URLS
from services.job_service import check_new_jobs, load_seen_jobs, save_seen_jobs
from services.paper_service import fetch_scholar_results, fetch_random_paper

def send_job_message(client, job):
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
        client.chat_postMessage(channel=CHANNEL, blocks=blocks, text=f"New Job: {job['title']}")
    except SlackApiError as e:
        print(f"Error sending job message: {e.response['error']}")

def create_paper_blocks(paper):
    meta_line = f"{paper['authors_display']} ({paper['year']}) *{paper['journal_display']}*"
    title_line = f"<{paper['link']}|{paper['title']}>" if paper["link"] else paper["title"]
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"{meta_line}\n{title_line}"}},
        {"type": "divider"},
    ]

def register_handlers(app, client):
    @app.command("/papers")
    def handle_papers_command(ack, say):
        ack()
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
        new_jobs = check_new_jobs(seen)
        for job in new_jobs:
            send_job_message(client, job)
        if new_jobs:
            save_seen_jobs(seen)
