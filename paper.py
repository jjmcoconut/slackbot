import os
import time
import json
import hashlib
import random
import requests
import datetime
import threading
import sys
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Load environment variables
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN") # Required for Socket Mode
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID") or "C04J1LKCK1S"

# Initialize Bolt App
app = App(token=SLACK_BOT_TOKEN)

# Google Scholar URLs
SEARCH_URLS = [
    {
        "name": "MSOM",
        "url": "https://scholar.google.com/scholar?hl=ko&as_sdt=0,5&q=source:%22Manufacturing+%26+Service+Operations+Management%22&scisbd=1"
    },
    {
        "name": "Management Science (OM)",
        "url": "https://scholar.google.com/scholar?hl=ko&scisbd=1&as_sdt=0%2C5&q=%22operations+management%22+source%3A%22Management+Science%22+source%3A%2C+source%3A%22informs%22&btnG="
    },
    {
        "name": "Management Science (Healthcare)",
        "url": "https://scholar.google.com/scholar?hl=ko&as_sdt=0,5&q=%22healthcare+management%22+source:%22Management+Science%22+source:,+source:%22informs%22&scisbd=1"
    }
]

# Random Paper Recommendation URLs
RANDOM_PAPER_URLS = [
    {
        "name": "Game Theory (MSOM)",
        "url": "https://scholar.google.com/scholar?start=0&q=%22game+theory%22+source:%22Manufacturing+%26+Service+Operations+Management%22&hl=ko&as_sdt=0,5"
    },
    {
        "name": "Game Theory (MS/OM)",
        "url": "https://scholar.google.com/scholar?as_q=&as_epq=%22game+theory%22%2C+%22operations+management%22&as_oq=&as_eq=&as_occt=any&as_sauthors=&as_publication=%22Management+Science%22+%2C+%22informs%22&as_ylo=&as_yhi=&hl=ko&as_sdt=0%2C5"
    },
    {
        "name": "Game Theory (Healthcare)",
        "url": "https://scholar.google.com/scholar?as_q=%22healthcare+management%22&as_epq=game+theory&as_oq=&as_eq=&as_occt=any&as_sauthors=&as_publication=%22Management+Science%22+%2C+%22informs%22&as_ylo=&as_yhi=&hl=ko&as_sdt=0%2C5"
    }
]

SEEN_PAPERS_FILE = "seen_papers_scholar.json"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
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

def fetch_scholar_results(url_config):
    url = url_config["url"]
    print(f"Fetching {url_config['name']}...")
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch {url}: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Google Scholar results are usually in div.gs_r.gs_or.gs_scl
        items = soup.select(".gs_r.gs_or.gs_scl")
        
        for item in items[:5]: # Take top 5
            try:
                title_tag = item.select_one(".gs_rt a")
                if not title_tag:
                    # Sometimes title is not a link (citation only), skip or handle
                    title_tag = item.select_one(".gs_rt")
                    # If it [CITATION], it might not have a link
                    if not title_tag: continue
                
                title = title_tag.get_text()
                link = title_tag.get("href") if title_tag.name == "a" else None
                
                # Parsing meta text: "Author1, Author2... - Journal Name, Year - Publisher"
                meta_div = item.select_one(".gs_a")
                meta_text = meta_div.get_text() if meta_div else ""
                
                # Split by hyphen or en-dash, with surrounding spaces
                # Scholar uses " - " (hyphen) or " – " (en-dash)
                parts = re.split(r'\s+-\s+|\s+–\s+', meta_text)
                
                authors_str = parts[0] if len(parts) > 0 else "Unknown Authors"
                journal_year = parts[1] if len(parts) > 1 else ""
                
                # If journal_year is empty (only 2 parts, sometimes just "Authors - Publisher")
                # We might want to check if parts[1] looks like a publisher or journal
                
                # Parse Authors
                # "P Martin, D Gupta"
                author_list = [a.strip() for a in authors_str.split(",")]
                formatted_authors = []
                
                for auth in author_list:
                    # Clean up "…" or "..."
                    auth = auth.replace("…", "").replace("...", "").strip()
                    if not auth: continue
                    
                    tokens = auth.split(" ")
                    if len(tokens) >= 2:
                        # "P Martin" -> "Martin P"
                        surname = tokens[-1]
                        initials = "".join([t[0] for t in tokens[:-1] if t])
                        formatted_authors.append(f"{surname} {initials}")
                    else:
                        formatted_authors.append(auth)
                
                # Rule: > 3 authors -> et al.
                if len(formatted_authors) > 3:
                    final_authors = ", ".join(formatted_authors[:3]) + ", et al."
                else:
                    final_authors = ", ".join(formatted_authors)

                # Extract Year
                year = "Unknown"
                if journal_year:
                    year_match = re.search(r'\d{4}', journal_year)
                    if year_match:
                        year = year_match.group(0)
                
                # Journal Mapping
                # Use category name as fallback or explicit mapping if possible
                journal_abbr = "Unknown"
                
                # Mapping based on strict user request
                # If the search URL category is MSOM, label it MSOM
                # If Management Science, label MS
                if "Manufacturing" in url_config["name"] or "MSOM" in url_config["name"]:
                    journal_abbr = "MSOM"
                elif "Management Science" in url_config["name"]:
                    journal_abbr = "MS"
                else:
                    journal_abbr = "Unknown"

                results.append({
                    "title": title,
                    "link": link,
                    "authors_display": final_authors,
                    "journal_display": journal_abbr,
                    "year": year,
                    "category": url_config["name"]
                })
                
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
                
        return results
        
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def create_slack_blocks(paper):
    # Format:
    # {Authors} ({Year}) {JournalAbr}
    # {Title} (Link)
    
    meta_line = f"{paper['authors_display']} ({paper['year']}) *{paper['journal_display']}*"
    
    title_line = f"<{paper['link']}|{paper['title']}>" if paper['link'] else paper['title']
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{meta_line}\n{title_line}"
            }
        },
        {
            "type": "divider"
        }
    ]
    return blocks

# -------------------------------------------------------------------------
# Smart Menu Recommendation Feature
# -------------------------------------------------------------------------





# -------------------------------------------------------------------------
# Random Paper Recommendation Feature
# -------------------------------------------------------------------------

def fetch_random_paper(url_config):
    """
    Fetches a random paper from the given search query.
    1. Fetches first page to get total results count.
    2. Selects a random index.
    3. Fetches the specific page containing that index.
    4. Returns the paper data.
    """
    base_url = url_config["url"]
    name = url_config["name"]
    print(f"Fetching random paper for {name}...")
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        # Step 1: Get Total Results and First Page
        response = requests.get(base_url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch base URL: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Parse "About X results"
        result_stats = soup.select_one("#gs_ab_md .gs_ab_mdw")
        if not result_stats:
            result_stats = soup.select_one(".gs_ab_mdw")
            
        if not result_stats:
            print("Could not find result statistics.")
            return None
            
        stats_text = result_stats.get_text()
        match = re.search(r'([\d,]+)', stats_text)
        if not match:
            print(f"Could not parse count from: {stats_text}")
            return None
            
        total_count_str = match.group(1).replace(",", "")
        total_count = int(total_count_str)
        
        if total_count == 0:
            print("No results found.")
            return None
            
        # Cap total count at 1000 because Google Scholar usually limits access to first 1000 results
        effective_count = min(total_count, 980) 
        
        # Step 2: Pick Random Index
        random_index = random.randint(0, effective_count - 1)
        start_param = (random_index // 10) * 10
        item_index_on_page = random_index % 10
        
        print(f"Total: {total_count}, Selected Index: {random_index} (Page Start: {start_param})")
        
        # Step 3: Fetch Specific Page
        if "start=" in base_url:
            target_url = re.sub(r'start=\d+', f'start={start_param}', base_url)
        else:
            separator = "&" if "?" in base_url else "?"
            target_url = f"{base_url}{separator}start={start_param}"
            
        target_response = requests.get(target_url, headers=headers, timeout=10)
        if target_response.status_code != 200:
            return None
            
        target_soup = BeautifulSoup(target_response.text, "html.parser")
        items = target_soup.select(".gs_r.gs_or.gs_scl")
        
        if not items or item_index_on_page >= len(items):
            if items:
                item = items[0]
            else:
                return None
        else:
            item = items[item_index_on_page]
            
        title_tag = item.select_one(".gs_rt a") or item.select_one(".gs_rt")
        if not title_tag: return None
        
        title = title_tag.get_text()
        link = title_tag.get("href") if title_tag.name == "a" else None
        
        meta_div = item.select_one(".gs_a")
        meta_text = meta_div.get_text() if meta_div else ""
        
        return {
            "title": title,
            "link": link,
            "meta": meta_text,
            "category": name,
            "random_index": random_index,
            "total_results": total_count
        }
        
    except Exception as e:
        print(f"Error in fetch_random_paper: {e}")
        return None

def create_random_paper_blocks(paper):
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎲 Weekly Random Paper ({paper['category']})",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Selected from {paper['total_results']:,} results (Index: {paper['random_index']})"
            }
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<{paper['link']}|*{paper['title']}*>\n{paper['meta']}"
            }
        },
        {"type": "divider"}
    ]
    return blocks