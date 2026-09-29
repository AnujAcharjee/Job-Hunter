# AGENTS.md - Antigravity Agent & Automation Blueprint

This document maintains architectural specifications, operational commands, and guidelines for **Antigravity** and future AI agents maintaining or extending the **Job Hunter** system.

---

## 1. System Mission & Scope
The agent automates daily search, evaluation, and Telegram notifications. By default, it operates in strict **Internship Mode** (`search_mode: "internship"` in `profile.json`), but supports dynamic switching to `"full_time"` or `"both"`.

- **Search Mode:** `"internship"` (Default: strictly internships; full-time roles disqualified)
- **Candidate Profile:** B.Tech Computer Science & Engineering (Expected graduation 2027)
- **Role Targets:**
  - MERN Stack Developer Intern
  - PostgreSQL (PG) & Full Stack Developer Intern
  - Agentic AI / AI Agent Developer Intern (LangChain, Tool Calling, RAG, LLM APIs)
  - Python / Backend Developer Intern (FastAPI, Django, PostgreSQL)
  - Software Development Engineer (SDE) Intern
  - Winter 2026/2027, Summer 2027, and 6-Month Internships
- **Target Portals:**
  1. **Internshala** (Direct scraping of MERN, Full Stack, Python, Backend, AI/GenAI, and Software Dev categories)
  2. **LinkedIn (India)** (Direct guest jobs API with `f_JT=I` for India)
  3. **AICTE Internship Portal** (Corporate partner programs & tech initiatives)
  4. **Naukri (India)** (Monitored tech internship feeds & portals)
- **Strict Disqualifiers:**
  - **NO Java / Spring / Spring Boot / Hibernate / J2EE**
  - **NO Machine Learning / Data Science / Model Training / Deep Learning / Computer Vision**
  - **NO Full-Time / Non-Internship Roles** (Must strictly be an internship/trainee role)
  - **NO Foreign-Restricted Roles** (Must be accessible from India or Remote in India)
  - **NO Stale Postings (> 7 days)** (Must be published strictly within the last week)
  - **NO Expired Postings** (Must not be closed, expired, or past the apply-by deadline)

---

## 2. Evaluation & Scoring Philosophy
- **Strict Scoring Threshold:** Only internships with a score of **8/10 or higher** are dispatched.
- **Uncapped Dispatch:** There is no arbitrary daily limit. **All** internships meeting the `>= 8/10` quality criteria are sent.
- **Freshness & Active Deadline Guarantee:**
  - Only postings published within the **last 7 days (last week)** and not yet sent are dispatched.
  - Automatically verifies and drops expired listings or applications that have closed.
- **Big Tech Priority & Highlighting:**
  - Companies like Google, Microsoft, Amazon, Meta, Apple, Adobe, Salesforce, Atlassian, Uber, Oracle, Cisco, Goldman Sachs, JP Morgan, Morgan Stanley, DE Shaw, Intuit, Flipkart, Swiggy, Zomato, Razorpay, CRED, PhonePe, NVIDIA, Snowflake, Databricks receive top priority scoring (9–10/10).
  - In Telegram, Big Tech listings are highlighted with a prominent **`🌟 BIG TECH INTERNSHIP SPOTLIGHT 🌟`** badge and special formatting.

---

## 3. Telegram Message Structure
Every job alert dispatched to Telegram adheres strictly to this format:
```html
🌟🌟🌟 BIG TECH INTERNSHIP SPOTLIGHT 🌟🌟🌟 (If Big Tech)
🏆 (n/10) match: Title
🏢 Company: Company Name [Tier-1 / Big Tech]
📍 Location: Full Location (prefer in India)
💡 Skills: Key Skills Matched (e.g. MERN, PostgreSQL, Agentic AI)
🌐 Source: Internshala / LinkedIn / AICTE / Naukri
📅 Posted Date: Relative or exact date (within past 7 days)
⏰ Last Date to Apply: Deadline date or Open / Rolling
🔗 Link: https://...
🧠 Insights: Gemini AI / Heuristic Analysis
```
Accompanied by an inline 1-tap apply button.

---

## 4. Scheduling
- **Primary Scheduler (Cloud):** Configured in `.github/workflows/daily_job_hunter.yml` running daily at **9:00 AM IST** (cron `30 3 * * *`).
- **Local Daemon (`scheduler.py`):** Retained but disabled by default (`ENABLED = False`) in favor of GitHub Actions. Can be toggled on if local Windows background scheduling is needed.

---

## 5. Repository File Map
| File | Responsibility |
|---|---|
| `main.py` | Entry point: orchestrates fetch, evaluate, filter, notify, and state persistence |
| `profile.json` | Candidate profile, target stack, priority companies, and disqualifiers |
| `src/date_utils.py` | Freshness and expiration validator (strict 7-day publication window & deadline checks) |
| `src/fetchers.py` | Direct scraping & API queries for Internshala, LinkedIn India, AICTE Portal, and Naukri |
| `src/evaluator.py` | Dual-mode strict evaluation (Gemini 2.5/Flash AI + smart heuristic fallback) |
| `src/notifier.py` | Telegram Bot API client, HTML card formatting with Posted & Last Date, Big Tech highlighting |
| `src/storage.py` | Deduplication engine using SHA-256 job IDs persisted in `data/seen_jobs.json` |
| `scheduler.py` | Standalone local scheduler running daily at 9:00 AM IST |
| `.github/workflows/daily_job_hunter.yml` | Automated cloud runner scheduled daily at 9:00 AM IST |

---

## 6. Commands Reference for Future Agents
- **Test Telegram Connectivity:**
  ```powershell
  python main.py --test-telegram
  ```
- **Run Dry-Run (No alerts sent, no state altered):**
  ```powershell
  python main.py --dry-run
  ```
- **Run Live Hunt Manually:**
  ```powershell
  python main.py
  ```
- **Run Local 9:00 AM IST Daemon:**
  ```powershell
  python scheduler.py
  ```
