import html
import json
import re
import urllib.parse
from typing import List, Dict, Any
import requests
from src.storage import JobStorage

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean_html(raw_html: str) -> str:
    """Strip HTML tags and unescape entities."""
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    return " ".join(clean.split())


def matches_keywords(text: str, keywords: List[str]) -> bool:
    """Check if any keyword appears as a distinct word/phrase in text."""
    lowered = text.lower()
    for kw in keywords:
        pattern = r"\b" + re.escape(kw.lower()) + r"\b"
        if re.search(pattern, lowered):
            return True
    return False


def fetch_jobicy() -> List[Dict[str, Any]]:
    """Fetch tech roles from Jobicy public API."""
    jobs = []
    try:
        url = "https://jobicy.com/api/v2/remote-jobs?count=50"
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json().get("jobs", [])
            for item in data:
                title = item.get("jobTitle", "")
                company = item.get("companyName", "")
                link = item.get("url", "")
                desc = clean_html(item.get("jobDescription", ""))
                loc = item.get("jobGeo", "Remote")
                job_id = JobStorage.generate_job_id(title, company, link)
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": loc,
                    "url": link,
                    "description": desc[:1000],
                    "source": "Jobicy"
                })
    except Exception as e:
        print(f"[Fetchers] Jobicy fetch error: {e}")
    return jobs


def fetch_remoteok() -> List[Dict[str, Any]]:
    """Fetch tech roles from RemoteOK public API."""
    jobs = []
    try:
        url = "https://remoteok.com/api"
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            # First item in RemoteOK response is metadata/legal
            items = data[1:] if len(data) > 1 and isinstance(data[0], dict) and "legal" in data[0] else data
            target_keywords = ["react", "node", "mern", "typescript", "javascript", "fullstack", "frontend", "backend", "intern", "junior", "ai", "next.js"]
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = item.get("position", "")
                company = item.get("company", "")
                tags = " ".join(item.get("tags", []))
                text_to_check = f"{title} {tags}"
                if not matches_keywords(text_to_check, target_keywords):
                    continue
                link = item.get("url", "")
                desc = clean_html(item.get("description", ""))
                loc = item.get("location", "Remote")
                job_id = JobStorage.generate_job_id(title, company, link)
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": loc or "Remote",
                    "url": link,
                    "description": desc[:1000],
                    "source": "RemoteOK"
                })
    except Exception as e:
        print(f"[Fetchers] RemoteOK fetch error: {e}")
    return jobs


def fetch_arbeitnow() -> List[Dict[str, Any]]:
    """Fetch tech roles from Arbeitnow API."""
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            target_keywords = ["react", "node", "typescript", "javascript", "full stack", "fullstack", "backend", "frontend", "intern", "junior", "ai", "next"]
            for item in data:
                title = item.get("title", "")
                tags = " ".join(item.get("tags", []))
                if not matches_keywords(f"{title} {tags}", target_keywords):
                    continue
                company = item.get("company_name", "")
                link = item.get("url", "")
                desc = clean_html(item.get("description", ""))
                loc = item.get("location", "Remote")
                job_id = JobStorage.generate_job_id(title, company, link)
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": loc,
                    "url": link,
                    "description": desc[:1000],
                    "source": "Arbeitnow"
                })
    except Exception as e:
        print(f"[Fetchers] Arbeitnow fetch error: {e}")
    return jobs


def fetch_duckduckgo_search(query: str, source_label: str = "Web Search", max_results: int = 15) -> List[Dict[str, Any]]:
    """Search for fresh job/internship postings via DuckDuckGo HTML search."""
    jobs = []
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        resp = requests.get(search_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            # Parse results from HTML using regex (no extra lxml/bs4 dependency required)
            # DDG result links look like <a class="result__url" href="..."> or <a class="result__snippet" ...>
            blocks = re.findall(r'<div class="result__body">(.*?)</div>\s*</div>', resp.text, re.DOTALL)
            for block in blocks[:max_results]:
                title_match = re.search(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
                snippet_match = re.search(r'<a class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)
                if not title_match:
                    continue
                raw_url = title_match.group(1)
                # Unpack DDG redirect url (uddg parameter)
                if "uddg=" in raw_url:
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                    actual_url = parsed.get("uddg", [raw_url])[0]
                else:
                    actual_url = raw_url

                raw_title = clean_html(title_match.group(2))
                snippet = clean_html(snippet_match.group(1)) if snippet_match else ""

                # Extract company or clean title
                company = "Company"
                clean_title = raw_title
                if " - " in raw_title:
                    parts = raw_title.split(" - ")
                    clean_title = parts[0].strip()
                    company = parts[1].strip()
                elif " | " in raw_title:
                    parts = raw_title.split(" | ")
                    clean_title = parts[0].strip()
                    company = parts[1].strip()

                job_id = JobStorage.generate_job_id(clean_title, company, actual_url)
                jobs.append({
                    "id": job_id,
                    "title": clean_title,
                    "company": company,
                    "location": "India / Remote",
                    "url": actual_url,
                    "description": snippet,
                    "source": source_label
                })
    except Exception as e:
        print(f"[Fetchers] DuckDuckGo search error ({query[:30]}...): {e}")
    return jobs


def fetch_linkedin_india(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Directly fetch fresh job and internship postings from LinkedIn Guest API for India."""
    jobs = []
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_query}&location=India&start=0"
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            cards = re.findall(r'<div class="[^"]*base-search-card[^"]*".*?</div>\s*</li>', resp.text, re.DOTALL)
            if not cards:
                cards = re.findall(r'<li[^>]*>(.*?)</li>', resp.text, re.DOTALL)

            for card in cards[:max_results]:
                u_match = re.search(r'href="(https://[^"]+)"', card)
                t_match = re.search(r'base-search-card__title[^>]*>\s*([\s\S]*?)\s*</h3>', card)
                c_match = re.search(r'base-search-card__subtitle[^>]*>[\s\S]*?<a[^>]*>\s*([\s\S]*?)\s*</a>', card)
                l_match = re.search(r'job-search-card__location[^>]*>\s*([\s\S]*?)\s*</span>', card)

                if t_match and u_match:
                    title = re.sub(r'<[^>]+>', '', t_match.group(1)).strip()
                    comp = re.sub(r'<[^>]+>', '', c_match.group(1)).strip() if c_match else "Company"
                    loc = re.sub(r'<[^>]+>', '', l_match.group(1)).strip() if l_match else "India"
                    job_url = u_match.group(1).split("?")[0]

                    clean_title = html.unescape(title)
                    clean_comp = html.unescape(comp)
                    clean_loc = html.unescape(loc)

                    job_id = JobStorage.generate_job_id(clean_title, clean_comp, job_url)
                    jobs.append({
                        "id": job_id,
                        "title": clean_title,
                        "company": clean_comp,
                        "location": clean_loc,
                        "url": job_url,
                        "description": f"LinkedIn opportunity in {clean_loc} at {clean_comp} ({clean_title})",
                        "source": "LinkedIn (India)"
                    })
    except Exception as e:
        print(f"[Fetchers] LinkedIn fetch error ({query}): {e}")
    return jobs


def fetch_all_jobs(storage: JobStorage) -> List[Dict[str, Any]]:
    """Fetch and aggregate jobs, prioritizing LinkedIn India and Indian platforms."""
    all_raw_jobs = []

    # 1. PRIORITY: Direct LinkedIn Job Postings in India
    linkedin_queries = [
        "mern internship",
        "full stack developer intern",
        "backend developer intern",
        "react node internship",
        "genai internship",
        "sde intern winter"
    ]
    for q in linkedin_queries:
        print(f"[Fetchers] Querying LinkedIn India ({q})...")
        all_raw_jobs.extend(fetch_linkedin_india(q, max_results=10))

    # 2. Targeted search queries for Indian internships & fresher web dev / GenAI roles
    search_queries = [
        ('("winter internship" OR "winter intern" OR "6 month intern" OR "2026 intern") ("software" OR "web" OR "SDE" OR "react" OR "node" OR "full stack") India', "Winter Internships (India)"),
        ('(Google OR Microsoft OR Amazon OR Adobe OR Salesforce OR Atlassian OR Uber OR Oracle OR Cisco OR Intuit) ("intern" OR "internship" OR "SDE intern") India', "Big Tech India"),
        ('site:internshala.com/internships ("MERN" OR "React" OR "Node" OR "Full Stack" OR "Generative AI")', "Internshala"),
        ('site:unstop.com/internships ("software development" OR "web development" OR "mern")', "Unstop (India)"),
        ('site:myworkdayjobs.com ("software intern" OR "SDE intern" OR "engineering intern") India', "Workday India Portals"),
        ('site:wellfound.com/jobs ("Full Stack" OR "MERN" OR "GenAI" OR "Backend") ("intern" OR "fresher") India', "Wellfound Startups (India)"),
        ('("Generative AI" OR "LLM") ("intern" OR "internship") India', "GenAI Opportunities (India)")
    ]

    for q, label in search_queries:
        print(f"[Fetchers] Querying {label}...")
        results = fetch_duckduckgo_search(q, source_label=label, max_results=8)
        all_raw_jobs.extend(results)

    # 3. Global Remote Tech Boards (Supplementary)
    print("[Fetchers] Querying RemoteOK...")
    all_raw_jobs.extend(fetch_remoteok())

    print("[Fetchers] Querying Jobicy...")
    all_raw_jobs.extend(fetch_jobicy())

    print("[Fetchers] Querying Arbeitnow...")
    all_raw_jobs.extend(fetch_arbeitnow())

    # Deduplicate against current run and seen storage
    unseen_jobs = []
    seen_in_batch = set()

    for job in all_raw_jobs:
        job_id = job["id"]
        if job_id in seen_in_batch or storage.is_seen(job_id):
            continue
        seen_in_batch.add(job_id)
        unseen_jobs.append(job)

    print(f"[Fetchers] Fetched {len(all_raw_jobs)} total listings. Found {len(unseen_jobs)} new unseen jobs.")
    return unseen_jobs
