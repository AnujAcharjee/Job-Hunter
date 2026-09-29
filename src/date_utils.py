import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


def is_posted_within_last_week(posted_str: str, now: Optional[datetime] = None) -> bool:
    """
    Returns True if the internship was posted within the past 7 days (last week),
    or represents an active cohort. Returns False if posted over 7 days ago.
    """
    if not posted_str:
        return False
    if now is None:
        now = datetime.now()

    s = posted_str.lower().strip()

    # Relative recent keywords (under 24-48 hours)
    fresh_keywords = [
        "just now", "today", "yesterday", "hour", "hours",
        "minute", "minutes", "few hours", "recent", "moments ago",
        "new"
    ]
    if any(k in s for k in fresh_keywords):
        return True

    # "X days ago"
    days_m = re.search(r'(\d+)\s*day', s)
    if days_m:
        days = int(days_m.group(1))
        return days <= 7

    # "1 week ago" is acceptable (<= 7 days). "2 weeks ago", "3 weeks ago" etc. are NOT
    weeks_m = re.search(r'(\d+)\s*week', s)
    if weeks_m:
        weeks = int(weeks_m.group(1))
        return weeks <= 1

    # Months or years are strictly older than 1 week
    if any(k in s for k in ["month", "months", "year", "years"]):
        return False

    # Active cohort program (e.g. AICTE corporate initiatives)
    if "active cohort" in s:
        return True

    # Parse standard date string e.g. "29 Sep 2026", "24 Sep 2026", "2026-09-28"
    date_m = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})(?:\s+(\d{4}))?', posted_str)
    if date_m:
        day = int(date_m.group(1))
        month_str = date_m.group(2)[:3].capitalize()
        year = int(date_m.group(3)) if date_m.group(3) else now.year
        try:
            parsed = datetime.strptime(f"{day} {month_str} {year}", "%d %b %Y")
            diff = (now.date() - parsed.date()).days
            return 0 <= diff <= 7
        except Exception:
            pass

    iso_m = re.search(r'(\d{4})-(\d{2})-(\d{2})', posted_str)
    if iso_m:
        try:
            parsed = datetime.strptime(iso_m.group(0), "%Y-%m-%d")
            diff = (now.date() - parsed.date()).days
            return 0 <= diff <= 7
        except Exception:
            pass

    # If it's a generic "Recently Posted" placeholder from a pre-filtered 7-day query
    if "recently posted" in s:
        return True

    return False


def is_job_expired(job: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """
    Returns True if the internship application is expired, closed, or past its deadline.
    """
    if now is None:
        now = datetime.now()

    last_date_str = str(job.get("last_date", "")).lower().strip()
    desc_str = str(job.get("description", "")).lower()
    title_str = str(job.get("title", "")).lower()

    # Closed or inactive indicators
    expired_keywords = [
        "closed", "expired", "applications closed", "application closed",
        "no longer accepting", "position filled", "inactive", "deadline passed"
    ]
    if any(k in last_date_str for k in expired_keywords):
        return True
    if any(k in title_str for k in ["closed", "expired", "archived"]):
        return True
    if any(k in desc_str for k in ["applications are closed", "no longer accepting applications"]):
        return True

    # Parse deadline if formatted as e.g. "15 Sep 2026", "15 Sep' 26", "25 Sep"
    date_m = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})\'?\s*(\d{2,4})?', job.get("last_date", ""))
    if date_m:
        day = int(date_m.group(1))
        month_str = date_m.group(2)[:3].capitalize()
        year_str = date_m.group(3)
        if year_str:
            year = int("20" + year_str) if len(year_str) == 2 else int(year_str)
        else:
            year = now.year
        try:
            deadline = datetime.strptime(f"{day} {month_str} {year}", "%d %b %Y")
            # If deadline was before today
            if deadline.date() < now.date():
                return True
        except Exception:
            pass

    iso_m = re.search(r'(\d{4})-(\d{2})-(\d{2})', job.get("last_date", ""))
    if iso_m:
        try:
            deadline = datetime.strptime(iso_m.group(0), "%Y-%m-%d")
            if deadline.date() < now.date():
                return True
        except Exception:
            pass

    return False
