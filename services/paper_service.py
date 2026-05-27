import os
import re
import json
import random
import requests
from bs4 import BeautifulSoup
from config import PAPER_STATE_FILE, USER_AGENTS

def load_seen_papers():
    if os.path.exists(PAPER_STATE_FILE):
        with open(PAPER_STATE_FILE, "r") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()

def save_seen_papers(seen_set):
    with open(PAPER_STATE_FILE, "w") as f:
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
