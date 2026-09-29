# 🚀 Job Hunter

> An autonomous AI agent that monitors **LinkedIn, Internshala, AICTE Portal, and Naukri** daily for fresh software engineering internships and jobs matching your profile, evaluates match quality with Google Gemini AI, and dispatches structured alerts straight to Telegram.

Runs **100% free** in the cloud on **GitHub Actions**.

---

## ⚡ Step-by-Step Setup Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/job-hunter.git
cd job-hunter
```

---

### Step 2: Personalize Your Profile

Open and edit **[`profile.json`](profile.json)** to match your target stack and preferences:

```json
{
  "candidate": {
    "search_mode": "internship",
    "education": "B.Tech in Computer Science and Engineering (Expected 2027)",
    "target_roles": [
      "Full Stack Developer Intern",
      "Software Development Engineer (SDE) Intern",
      "Python / Backend Developer Intern",
      "MERN Stack Developer Intern",
      "Agentic AI / AI Agent Developer Intern"
    ],
    "skills": {
      "languages": ["TypeScript", "JavaScript", "Python", "SQL"],
      "frameworks": ["React", "Node.js", "Express", "FastAPI"],
      "databases": ["PostgreSQL", "MongoDB"]
    },
    "priority_companies": [
      "Google", "Microsoft", "Amazon", "Meta", "Apple", "Atlassian", "Uber"
    ],
    "disqualifiers": [
      "Any full-time or experienced role (Internships only)",
      "Java or Spring Boot roles",
      "Machine Learning model training"
    ]
  }
}
```

#### What to configure:
- **`search_mode`**: 
  - `"internship"` *(default)*: Strictly internships (disqualifies full-time roles).
  - `"full_time"`: Strictly full-time roles (disqualifies internships).
  - `"both"`: Evaluates both.
- **`target_roles`**: Your target titles (e.g., MERN, Python, Full Stack, SDE).
- **`skills`**: Your active languages, libraries, and databases.
- **`disqualifiers`**: Keywords or stacks automatically rejected (Score 1/10).
- **`priority_companies`**: Dream companies to highlight with a **🌟 Big Tech Spotlight** badge.
- **`priority_locations`**: Preferred cities or remote options.

---

### Step 3: Add GitHub Secrets

In your GitHub repository, go to **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret**, and add:

| Secret Name | Where to get it | Description |
|---|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | Free API key for AI match evaluation. |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/botfather) | Bot authorization token. |
| `TELEGRAM_CHAT_ID` | Telegram | Your Chat ID or Channel ID (add bot as admin). |

---

### Step 4: Commit & Push to GitHub

Save your changes and push them to your repository:

```bash
git add .
git commit -m "feat: configure personalized profile"
git push origin main
```

---

### Step 5: Run & Automate

- **Automated:** GitHub Actions runs automatically every morning at **9:00 AM IST** (`30 3 * * *` UTC).
- **Test Instantly:** Go to your repo's **Actions** tab ➔ **Daily Tech Internship Hunter** ➔ click **Run workflow**.

*(Optional local execution: `pip install -r requirements.txt` ➔ copy `.env.example` to `.env` ➔ `python main.py`)*

---

## 📬 Telegram Alert Format

Postings published strictly within the **past 7 days** meeting the quality score threshold (**`>= 8/10`**) are dispatched in this schema:

```text
🌟🌟🌟 BIG TECH INTERNSHIP SPOTLIGHT 🌟🌟🌟 (If Priority Company)
🏆 (n/10) match: Title
🏢 Company: Company Name [Tier-1 / Big Tech]
📍 Location: Full Location
💡 Skills: Key Matched Skills
🌐 Source: LinkedIn / Internshala / AICTE / Naukri
📅 Posted Date: Relative or exact date (within past 7 days)
⏰ Last Date to Apply: Deadline date or Open / Rolling
🔗 Link: https://...
🧠 Insights: AI Analysis
```
*Each alert includes an interactive 1-tap inline apply button.*

---

## 🤖 System Architecture

For architectural specifications, scraping pipelines, scoring algorithms, and autonomous agent instructions, refer to [AGENTS.md](AGENTS.md).
