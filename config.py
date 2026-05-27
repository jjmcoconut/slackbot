import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Slack Config
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
# bot.py uses SLACK_JOB_CHANNEL_ID and falls back to "C04N51UG7DY"
# paper.py uses SLACK_CHANNEL_ID. We will standardize on a single channel variable.
CHANNEL = os.getenv("SLACK_JOB_CHANNEL_ID") or os.getenv("SLACK_CHANNEL_ID") or "C04N51UG7DY"

# Shared Constants
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
]

# Job Checking Config
KAIST_JOB_URL = (
    "https://career.kaist.ac.kr/recruit_info/lists/sc_sorting/end_date"
    "/sc_asc_desc/desc/sc_paging/20/sc_recruit_field/005%7C/sc_recruit_form/01%7C"
)
JOB_STATE_FILE = "seen_jobs.json"

# Scholar Paper Config
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

PAPER_STATE_FILE = "seen_papers_scholar.json"
