import requests
from bs4 import BeautifulSoup
import re

url = "https://career.kaist.ac.kr/recruit_info/lists/sc_sorting/end_date/sc_asc_desc/desc/sc_paging/20/sc_recruit_field/005%7C/sc_recruit_form/01%7C"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

def debug_session():
    session = requests.Session()
    session.headers.update(headers)
    
    print("--- 1. Fetching List Page to init session ---")
    try:
        resp_list = session.get(url)
        print(f"List Status: {resp_list.status_code}")
        print(f"Cookies: {session.cookies.get_dict()}")
        
        soup = BeautifulSoup(resp_list.text, 'html.parser')
        rows = soup.select("tr.btn_move_to_view")
        job_id = None
        if rows:
            btn_param = rows[0].get('btn_param')
            match = re.search(r"id:'(\d+)'", btn_param)
            if match:
                job_id = match.group(1)
                print(f"Found ID: {job_id}")
        
        if not job_id:
            job_id = '2089'
            print("Using fallback ID: 2089")
            
        print(f"--- 2. Fetching Detail Page for {job_id} ---")
        detail_url = f"https://career.kaist.ac.kr/recruit_info/view/id/{job_id}"
        resp_detail = session.get(detail_url)
        
        print(f"Detail Status: {resp_detail.status_code}")
        print(f"Detail URL: {resp_detail.url}")
        print(f"Detail Content Start: {resp_detail.text[:500]}")
        
        if "login" in resp_detail.url or "로그인" in resp_detail.text:
            print("STILL REQUIRED LOGIN")
        else:
            soup_detail = BeautifulSoup(resp_detail.text, 'html.parser')
            title = soup_detail.select_one(".info-title .tit")
            main_text = soup_detail.select_one(".board-view-con .main-text")
            
            print(f"Title found: {title.get_text(strip=True) if title else 'No'}")
            print(f"Main text found: {main_text.get_text(strip=True)[:100] if main_text else 'No'}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_session()
