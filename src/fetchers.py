import html
import json
import re
import urllib.parse
from typing import List, Dict, Any
import requests
from src.storage import JobStorage
from src.date_utils import is_posted_within_last_week, is_job_expired

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


def is_strict_disqualified(title: str, description: str = "") -> bool:
    """Immediately reject ML-based roles, Java/Spring roles, and non-tech titles."""
    text = f"{title} {description}".lower()

    # 1. Reject Java / Spring / Spring Boot
    if re.search(r"\b(java|spring|springboot|spring boot|j2ee|hibernate)\b", text):
        # Allow JavaScript / TypeScript
        if not re.search(r"\b(javascript|typescript)\b", text) or re.search(r"\b(spring|springboot|spring boot|hibernate|j2ee)\b", text):
            return True

    # 2. Reject Machine Learning / Deep Learning / Data Science model training
    ml_keywords = [
        "machine learning", "deep learning", "data science", "data scientist",
        "computer vision", "nlp researcher", "ml engineer", "model training",
        "scikit-learn", "tensorflow", "pytorch"
    ]
    for kw in ml_keywords:
        if kw in text:
            return True
    # If ML appears as isolated word in title
    if re.search(r"\bml\b", title.lower()):
        return True

    # 3. Reject non-tech roles
    non_tech = [
        "video edit", "content writ", "seo", "sales", "telecall", "marketing",
        "human resources", "hr intern", "recruiter", "graphic design",
        "business development", "teaching", "tutor", "accountant", "bpo"
    ]
    for nt in non_tech:
        if nt in text:
            return True

    return False


def load_profile_search_mode(profile_path: str = "profile.json") -> str:
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("candidate", {}).get("search_mode", "internship").lower()
    except Exception:
        return "internship"


def fetch_internshala(search_mode: str = "internship") -> List[Dict[str, Any]]:
    """Fetch tech opportunities directly from Internshala portal based on search_mode."""
    categories = [
        ("mern-stack-development-internship", "MERN Stack"),
        ("full-stack-development-internship", "Full Stack"),
        ("python-django-internship", "Python / Backend"),
        ("software-development-internship", "Software Engineering"),
        ("node-js-development,reactjs-development-internship", "React & Node"),
        ("artificial-intelligence-ai-internship", "AI & GenAI"),
        ("backend-development-internship", "Backend / PostgreSQL")
    ]

    target_tech = [
        "developer", "engineer", "software", "mern", "react", "node",
        "python", "full stack", "fullstack", "backend", "frontend",
        "web", "sde", "api", "ai", "database", "programmer", "postgres"
    ]

    jobs = []
    seen_urls = set()

    for cat_slug, tag in categories:
        if search_mode == "full_time":
            job_slug = cat_slug.replace("-internship", "-jobs")
            url = f"https://internshala.com/jobs/{job_slug}/"
        else:
            url = f"https://internshala.com/internships/{cat_slug}/"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue

            blocks = re.split(r'id="individual_internship_', resp.text)[1:]
            for b in blocks:
                title_m = re.search(r'<a class="job-title-href"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b)
                comp_m = re.search(r'<p class="company-name">\s*(.*?)\s*</p>', b)
                if not title_m or not comp_m:
                    continue

                raw_title = clean_html(title_m.group(2))
                raw_company = clean_html(comp_m.group(1))
                rel_url = title_m.group(1)
                full_url = f"https://internshala.com{rel_url}"

                if full_url in seen_urls:
                    continue

                # Filter out obvious non-tech or disqualified ML/Java
                if is_strict_disqualified(raw_title):
                    continue
                if not any(tt in raw_title.lower() for tt in target_tech):
                    continue

                # Location & Stipend extraction
                loc_match = re.search(r'<!-- location -->([\s\S]*?)<!-- /location -->', b)
                if loc_match:
                    loc_text = clean_html(loc_match.group(1))
                else:
                    loc_text = "Work from home" if "work from home" in b.lower() else "India"
                if not loc_text:
                    loc_text = "India / Work from home"

                stipend_m = re.search(r'<span class="stipend">\s*([\s\S]*?)\s*</span>', b)
                stipend = clean_html(stipend_m.group(1)) if stipend_m else ""

                # Extract dates (posted date & deadline)
                posted_m = re.search(r'<div class="status-inactive"[^>]*>.*?<span>(.*?)</span>', b, re.DOTALL)
                if not posted_m:
                    posted_m = re.search(r'<div class="status-success"[^>]*>.*?<span>(.*?)</span>', b, re.DOTALL)
                if not posted_m:
                    posted_m = re.search(r'<i class="ic-16-reschedule"></i>\s*<span>(.*?)</span>', b)
                posted_date = clean_html(posted_m.group(1)) if posted_m else "Recently Posted"

                apply_by_m = re.search(r'Apply by\s*([0-9]{1,2}\s+[A-Za-z]+\'?\s*[0-9]{2,4})', b, re.IGNORECASE)
                if not apply_by_m:
                    apply_by_m = re.search(r'<!-- apply_by -->([\s\S]*?)<!-- /apply_by -->', b)
                last_date = clean_html(apply_by_m.group(1)) if apply_by_m else "Apply ASAP / Open"

                # Filter: Must be strictly published within the last week and not expired
                if not is_posted_within_last_week(posted_date):
                    continue
                if is_job_expired({"last_date": last_date, "title": raw_title, "description": b}):
                    continue

                job_id = JobStorage.generate_job_id(raw_title, raw_company, full_url)
                seen_urls.add(full_url)

                desc = (
                    f"Internshala {tag} Internship opportunity at {raw_company}. "
                    f"Role: {raw_title}. Location: {loc_text}. Stipend: {stipend}. "
                    f"Posted: {posted_date}. Apply by: {last_date}. "
                    f"Candidate focus: MERN, PostgreSQL, Agentic AI, Python, Full Stack."
                )

                jobs.append({
                    "id": job_id,
                    "title": raw_title,
                    "company": raw_company,
                    "location": f"{loc_text}, India" if "India" not in loc_text else loc_text,
                    "url": full_url,
                    "description": desc,
                    "source": "Internshala",
                    "posted_date": posted_date,
                    "last_date": last_date
                })
        except Exception as e:
            print(f"[Fetchers] Internshala ({cat_slug}) fetch error: {e}")

    return jobs


def fetch_linkedin_india(query: str, max_results: int = 15, search_mode: str = "internship") -> List[Dict[str, Any]]:
    """Directly fetch fresh tech opportunities from LinkedIn Guest API for India based on search_mode."""
    jobs = []
    try:
        encoded_query = urllib.parse.quote(query)
        if search_mode == "internship":
            jt_param = "&f_JT=I"
        elif search_mode == "full_time":
            jt_param = "&f_JT=F"
        else:
            jt_param = ""

        # f_TPR=r604800 forces Past 1 Week (7 days)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_query}&location=India{jt_param}&f_TPR=r604800&start=0"
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
                    title = clean_html(t_match.group(1))
                    comp = clean_html(c_match.group(1)) if c_match else "Company"
                    loc = clean_html(l_match.group(1)) if l_match else "India"
                    job_url = u_match.group(1).split("?")[0]

                    # Filter out disqualified ML / Java Spring roles
                    if is_strict_disqualified(title):
                        continue

                    # Role-type filtering based on search_mode
                    if search_mode == "internship":
                        if not any(k in title.lower() for k in ["intern", "internship", "trainee", "student"]):
                            if "intern" not in query.lower():
                                continue
                    elif search_mode == "full_time":
                        if any(k in title.lower() for k in ["intern", "internship", "trainee"]):
                            continue

                    # Extract posted date from time tag
                    date_m = re.search(r'<time[^>]*class="[^"]*job-search-card__listdate[^"]*"[^>]*>([\s\S]*?)</time>', card)
                    if not date_m:
                        date_m = re.search(r'<time[^>]*>([\s\S]*?)</time>', card)
                    posted_date = clean_html(date_m.group(1)) if date_m else "Recently Posted"
                    last_date = "Apply ASAP / Rolling Basis"

                    # Filter: Must be strictly published within the last week and not expired
                    if not is_posted_within_last_week(posted_date):
                        continue
                    if is_job_expired({"last_date": last_date, "title": title, "description": card}):
                        continue

                    job_id = JobStorage.generate_job_id(title, comp, job_url)
                    jobs.append({
                        "id": job_id,
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "url": job_url,
                        "description": f"LinkedIn Internship in {loc} at {comp} for {title}.",
                        "source": "LinkedIn",
                        "posted_date": posted_date,
                        "last_date": last_date
                    })
    except Exception as e:
        print(f"[Fetchers] LinkedIn fetch error ({query}): {e}")
    return jobs


def fetch_aicte_portal() -> List[Dict[str, Any]]:
    """Fetch tech & corporate partner internships from AICTE Internship Portal."""
    partners = [
        ("google", "Google", "AI & Cloud Tech Internship Program"),
        ("cisco", "Cisco", "Networking & Software Developer Virtual Internship"),
        ("salesforce", "Salesforce", "Cloud & Full Stack Developer Internship"),
        ("mongodb", "MongoDB", "Modern Database & Backend Developer Internship"),
        ("servicenow", "ServiceNow", "Enterprise Software Engineering Internship"),
        ("vmware", "VMware", "Cloud Infrastructure & Software Internship"),
        ("mathworks", "MathWorks", "Engineering & Software Development Internship"),
        ("codeforgovtech", "Code For GovTech (C4GT)", "Open Source Full Stack Tech Internship")
    ]

    jobs = []
    for slug, company, title_desc in partners:
        url = f"https://internship.aicte-india.org/internships/{slug}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', resp.text)
                headline = clean_html(h1_m.group(1)) if h1_m else title_desc
                title = f"{company} Tech Internship ({headline[:50]})"

                job_id = JobStorage.generate_job_id(title, company, url)
                jobs.append({
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": "India / Remote",
                    "url": url,
                    "description": f"AICTE Official Partner Tech Internship by {company}. {title_desc}. Accessible for Indian engineering students.",
                    "source": "AICTE Internship Portal",
                    "posted_date": "Active Cohort (2026/2027)",
                    "last_date": "Limited Seats / Apply ASAP"
                })
        except Exception as e:
            print(f"[Fetchers] AICTE partner ({slug}) fetch error: {e}")

    return jobs


def fetch_naukri_and_web_internships(search_mode: str = "internship") -> List[Dict[str, Any]]:
    """Fetch fresh Indian tech opportunities from Naukri and monitored tech portals via Google RSS feeds."""
    if search_mode == "full_time":
        queries = [
            ('site:naukri.com ("full time" OR "fresher" OR "junior" OR "associate") ("MERN" OR "Full Stack" OR "Python" OR "React") when:7d', "Naukri"),
            ('site:naukri.com ("software developer" OR "backend developer" OR "postgresql" OR "fastapi") when:7d', "Naukri"),
            ('("Full Stack Developer" OR "Software Engineer") ("Google" OR "Amazon" OR "Microsoft" OR "Atlassian" OR "Uber") India when:7d', "Big Tech Portals")
        ]
    elif search_mode == "both":
        queries = [
            ('site:naukri.com ("MERN" OR "Full Stack" OR "Python" OR "React" OR "Node") when:7d', "Naukri"),
            ('site:naukri.com ("software developer" OR "backend" OR "postgresql" OR "fastapi") when:7d', "Naukri"),
            ('("Software Engineer" OR "SDE" OR "Full Stack") ("Google" OR "Amazon" OR "Microsoft" OR "Atlassian" OR "Uber") India when:7d', "Big Tech Portals")
        ]
    else:
        # Default: strict internship
        queries = [
            ('site:naukri.com ("intern" OR "internship") ("MERN" OR "Full Stack" OR "Python" OR "React" OR "Node") when:7d', "Naukri"),
            ('site:naukri.com/internship ("software developer" OR "backend" OR "postgresql" OR "fastapi") when:7d', "Naukri"),
            ('("MERN" OR "Full Stack" OR "Agentic AI") ("intern" OR "internship") site:unstop.com when:7d', "Unstop (India)"),
            ('("Software Engineer Intern" OR "SDE Intern") ("Google" OR "Amazon" OR "Microsoft" OR "Atlassian" OR "Uber") India when:7d', "Big Tech Portals")
        ]

    jobs = []
    seen_urls = set()

    for q, source_name in queries:
        try:
            rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
            resp = requests.get(rss_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                items = re.findall(r'<item>([\s\S]*?)</item>', resp.text)
                for it in items[:8]:
                    t_match = re.search(r'<title>(.*?)</title>', it)
                    l_match = re.search(r'<link>(.*?)</link>', it)
                    if not t_match or not l_match:
                        continue

                    raw_title = clean_html(t_match.group(1))
                    raw_link = l_match.group(1).strip()

                    # Extract company if formatted like "Role - Company"
                    company = source_name
                    clean_title = raw_title
                    if " - " in raw_title:
                        parts = raw_title.rsplit(" - ", 1)
                        clean_title = parts[0].strip()
                        company = parts[1].strip()

                    if raw_link in seen_urls:
                        continue

                    # Strict rejection of ML and Java Spring
                    if is_strict_disqualified(clean_title):
                        continue

                    # Role-type filtering based on search_mode
                    if search_mode == "internship":
                        if not any(w in clean_title.lower() for w in ["intern", "internship", "trainee"]):
                            continue
                    elif search_mode == "full_time":
                        if any(w in clean_title.lower() for w in ["intern", "internship", "trainee"]):
                            continue

                    # Extract posted date from pubDate
                    pub_m = re.search(r'<pubDate>(.*?)</pubDate>', it)
                    if pub_m:
                        raw_date = pub_m.group(1)
                        dm = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', raw_date)
                        posted_date = dm.group(1) if dm else clean_html(raw_date[:16])
                    else:
                        posted_date = "Recently Posted"
                    last_date = "Apply ASAP / Rolling Basis"

                    # Filter: Must be strictly published within the last week and not expired
                    if not is_posted_within_last_week(posted_date):
                        continue
                    if is_job_expired({"last_date": last_date, "title": clean_title, "description": it}):
                        continue

                    job_id = JobStorage.generate_job_id(clean_title, company, raw_link)
                    seen_urls.add(raw_link)

                    jobs.append({
                        "id": job_id,
                        "title": clean_title,
                        "company": company,
                        "location": "India",
                        "url": raw_link,
                        "description": f"{source_name} opportunity: {clean_title} at {company} in India.",
                        "source": source_name,
                        "posted_date": posted_date,
                        "last_date": last_date
                    })
        except Exception as e:
            print(f"[Fetchers] RSS query error ({q[:30]}): {e}")

    return jobs


def fetch_all_jobs(storage: JobStorage, profile: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Fetch and aggregate tech opportunities from Internshala, LinkedIn India, AICTE Portal, and Naukri."""
    if profile is None:
        search_mode = load_profile_search_mode()
    else:
        search_mode = profile.get("search_mode", "internship").lower()

    print(f"[Fetchers] Active Search Mode: '{search_mode.upper()}'")
    all_raw_jobs = []

    # 1. INTERNSHALA: Direct scraping based on search mode
    print(f"[Fetchers] Scraping Internshala ({search_mode})...")
    internshala_jobs = fetch_internshala(search_mode=search_mode)
    print(f"[Fetchers] Found {len(internshala_jobs)} listings from Internshala.")
    all_raw_jobs.extend(internshala_jobs)

    # 2. LINKEDIN INDIA: Direct guest API
    if search_mode == "full_time":
        linkedin_queries = [
            "mern developer", "full stack developer", "python developer",
            "backend developer", "software development engineer", "agentic ai engineer",
            "sde entry level", "Google software engineer India", "Amazon SDE India",
            "Microsoft software engineer India", "Uber engineer India", "Atlassian engineer India",
            "Salesforce developer India", "Flipkart SDE India", "PostgreSQL developer"
        ]
    elif search_mode == "both":
        linkedin_queries = [
            "mern developer", "full stack developer intern", "python developer",
            "backend developer intern", "software development engineer", "agentic ai developer",
            "sde intern winter", "Google software India", "Amazon SDE India",
            "Microsoft software India", "PostgreSQL developer"
        ]
    else:
        # Default: strict internship
        linkedin_queries = [
            "mern internship", "full stack developer intern", "python intern",
            "backend developer intern", "software developer intern", "agentic ai intern",
            "sde intern winter", "Google software intern India", "Amazon SDE intern India",
            "Microsoft intern India", "Uber intern India", "Atlassian intern India",
            "Salesforce developer intern India", "Flipkart intern India", "PostgreSQL developer intern"
        ]

    for q in linkedin_queries:
        print(f"[Fetchers] Querying LinkedIn India ({q})...")
        ll_jobs = fetch_linkedin_india(q, max_results=12, search_mode=search_mode)
        all_raw_jobs.extend(ll_jobs)

    # 3. AICTE INTERNSHIP PORTAL (applicable for internships or both)
    if search_mode in ["internship", "both"]:
        print("[Fetchers] Querying AICTE Internship Portal programs...")
        aicte_jobs = fetch_aicte_portal()
        print(f"[Fetchers] Found {len(aicte_jobs)} opportunities from AICTE Portal.")
        all_raw_jobs.extend(aicte_jobs)

    # 4. NAUKRI & MONITORED PORTALS (India):
    print(f"[Fetchers] Querying Naukri & tech feeds ({search_mode})...")
    naukri_jobs = fetch_naukri_and_web_internships(search_mode=search_mode)
    print(f"[Fetchers] Found {len(naukri_jobs)} opportunities from Naukri & web portals.")
    all_raw_jobs.extend(naukri_jobs)

    # Deduplicate against current run and seen storage
    unseen_jobs = []
    seen_in_batch = set()

    for job in all_raw_jobs:
        job_id = job["id"]
        if job_id in seen_in_batch or storage.is_seen(job_id):
            continue
        seen_in_batch.add(job_id)
        unseen_jobs.append(job)

    print(f"[Fetchers] Fetched {len(all_raw_jobs)} total listings. Found {len(unseen_jobs)} new unseen internships.")
    return unseen_jobs
