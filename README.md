# 🚀 Automated Daily Job Hunter (GitHub Actions + Gemini AI + Telegram)

An automated cloud pipeline tailored specifically for **Anuj Acharjee** (B.Tech CSE, 2027 batch). Twice a day (8:30 AM & 4:00 PM IST), it prioritizes and fetches **Indian internships & jobs directly from LinkedIn India, Big Tech careers, Internshala, and Unstop**, uses **Google Gemini AI** to evaluate each opening against your resume (MERN, Next.js, GenAI), and pushes curated cards with 1-click apply links to your **Telegram**.

---

## ✨ Key Features
- **🇮🇳 India & LinkedIn Prioritized**: Directly queries LinkedIn India for fresh MERN, Full-Stack, Backend, SDE, and GenAI internships across Bengaluru, Hyderabad, Pune, Delhi NCR, and remote India.
- **100% Free & Cloud-Based**: Runs on GitHub Actions in the cloud. Your laptop doesn't need to be on!
- **Gemini AI Filter**: Evaluates tech stack match, experience requirements, and filters out senior roles or foreign-restricted spam.
- **Direct to Mobile**: Receive attractive cards with 1-click **"🚀 Apply on LinkedIn"** buttons on your phone via Telegram.
- **Zero Duplicate Spam**: Tracks applied/seen jobs in `data/seen_jobs.json` so you never see the same listing twice.

---

## 🛠️ Quick Setup Guide (Takes ~5 Minutes)

### Step 1: Get Free Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Sign in with your Google Account and click **"Create API key"**.
3. Copy your key.

---

### Step 2: Create Your Free Telegram Bot (2 minutes)
1. Open **Telegram** on your phone or desktop and search for `@BotFather`.
2. Tap **Start** and send the command:
   ```
   /newbot
   ```
3. Follow the prompt to name your bot (e.g. `Anuj Job Hunter`) and give it a username (e.g. `anuj_job_hunter_bot`).
4. `@BotFather` will give you a **Bot Token** (looks like `7123456789:AAF...`). Save this token!
5. Now open your new bot in Telegram and tap **Start** (or send any message like `/start` so it can message you).
6. To get your personal **Chat ID**:
   - Search for `@userinfobot` on Telegram.
   - Tap **Start**. It will immediately reply with your `Id` (e.g. `123456789`). Save this number!

---

### Step 3: Test Locally (Optional)
1. Create a `.env` file from the template:
   ```bash
   copy .env.example .env
   ```
2. Paste your keys into `.env`:
   ```env
   GEMINI_API_KEY=your_gemini_key
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```
3. Test your Telegram connection:
   ```bash
   python main.py --test-telegram
   ```
   *(You will receive an instant test message on your Telegram!)*

4. Test fetching & AI evaluation without sending real alerts:
   ```bash
   python main.py --dry-run
   ```

---

### Step 4: Push to a GitHub Repository
1. Initialize git and push this project to a **Private GitHub Repository**:
   ```bash
   git init
   git add .
   git commit -m "feat: initial daily job hunter setup"
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
   git push -u origin main
   ```

---

### Step 5: Add Your Secrets in GitHub
1. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**.
2. Under **Repository secrets**, click **New repository secret** and add:
   - `GEMINI_API_KEY`: Your Gemini API key from Step 1.
   - `TELEGRAM_BOT_TOKEN`: Your bot token from `@BotFather`.
   - `TELEGRAM_CHAT_ID`: Your numerical chat ID from `@userinfobot`.

---

### Step 6: Enable Workflow Permissions
1. In your repository, go to **Settings** > **Actions** > **General**.
2. Scroll down to **Workflow permissions**.
3. Select **"Read and write permissions"** (this allows the bot to commit `seen_jobs.json` so you never get duplicates).
4. Click **Save**.

---

## ⏰ Schedule & Manual Trigger
- **Automated Schedule**: Runs **twice every day**:
  - **Morning**: **~8:18 AM IST** (`02:48 UTC` - off-peak minute to avoid GitHub Actions delays)
  - **Afternoon**: **~3:48 PM IST** (`10:18 UTC` - off-peak minute to avoid GitHub Actions delays)
- **Manual Run**: You can trigger a run anytime!
  - Go to the **Actions** tab in your GitHub repository.
  - Click **Daily Job Hunter** on the left.
  - Click the **Run workflow** dropdown button.

---

## ⚙️ Customization
- **Change Target Roles / Skills**: Modify `profile.json`.
- **Change Score Threshold**: Set `MIN_MATCH_SCORE=8` in `.env` (or GitHub Actions env) to only get top-tier 8+/10 matches.
- **Change Daily Limit**: Set `MAX_JOBS_PER_RUN=15` to get more alerts per day.
