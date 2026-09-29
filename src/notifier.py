import html
import json
import os
import time
from typing import Dict, Any, List
import requests


class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str, reply_markup: Dict[str, Any] = None) -> bool:
        """Send an HTML-formatted message via Telegram Bot API."""
        if not self.is_configured():
            print("[Notifier] Telegram credentials not configured. Skipping alert.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)

        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.status_code == 200:
                return True
            else:
                print(f"[Notifier] Telegram API error ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            print(f"[Notifier] Failed to send Telegram message: {e}")
            return False

    def send_job_alert(self, job: Dict[str, Any]) -> bool:
        """
        Format and send job card adhering strictly to requested format:
        (n/10) match
        company name
        location: full (prefer in india)
        Skills
        src
        link
        insigths
        Highlights Big Tech companies prominently.
        """
        score = job.get("score", 8)
        title = html.escape(job.get("title", "Tech Intern"))
        company = html.escape(job.get("company", "Company"))
        location = html.escape(job.get("location", "India"))
        source = html.escape(job.get("source", "Internship Portal"))
        summary = html.escape(job.get("match_summary", "Strong match for your tech stack."))
        posted_date = html.escape(job.get("posted_date", "Recently Posted"))
        last_date = html.escape(job.get("last_date", "Apply ASAP / Open"))
        
        raw_skills = job.get("key_skills", [])
        skills_str = ", ".join(raw_skills) if raw_skills else "MERN / Python / Full Stack / Agentic AI"
        skills = html.escape(skills_str)
        
        apply_url = job.get("url", "")
        is_big_tech = job.get("is_big_tech", False)

        if is_big_tech:
            header = "🌟🌟🌟 <b>BIG TECH INTERNSHIP SPOTLIGHT</b> 🌟🌟🌟\n\n"
            match_line = f"🏆 <b>({score}/10) match:</b> <b>{title}</b>"
            company_line = f"🏢 <b>Company:</b> <b>{company}</b> 🏆 [Tier-1 / Big Tech]"
        else:
            header = ""
            match_line = f"🎯 <b>({score}/10) match:</b> <b>{title}</b>"
            company_line = f"🏢 <b>Company:</b> <b>{company}</b>"

        card = (
            f"{header}"
            f"{match_line}\n"
            f"{company_line}\n"
            f"📍 <b>Location:</b> {location}\n"
            f"💡 <b>Skills:</b> <code>{skills}</code>\n"
            f"🌐 <b>Source:</b> {source}\n"
            f"📅 <b>Posted Date:</b> {posted_date}\n"
            f"⏰ <b>Last Date to Apply:</b> {last_date}\n"
            f"🔗 <b>Link:</b> <a href=\"{apply_url}\">{apply_url}</a>\n"
            f"🧠 <b>Insights:</b> <i>{summary}</i>"
        )

        button_text = f"🚀 Apply on {source}" if len(source) < 20 else "🚀 Tap to Apply"
        reply_markup = {
            "inline_keyboard": [
                [{"text": button_text, "url": apply_url}]
            ]
        }

        return self.send_message(card, reply_markup=reply_markup)

    def send_batch_summary(self, matched_jobs: List[Dict[str, Any]]) -> int:
        """Send alerts for ALL matched internships (no artificial cap), highlighting Big Tech."""
        if not self.is_configured():
            print("[Notifier] Telegram not configured. Printing matched internships to console:")
            for j in matched_jobs:
                print(f" -> [{j.get('score')}/10] {j.get('title')} at {j.get('company')} ({j.get('url')})")
            return len(matched_jobs)

        big_tech_count = sum(1 for j in matched_jobs if j.get("is_big_tech"))
        sent_count = 0

        header_text = (
            f"🚀 <b>Daily Internship Hunter Update (9:00 AM IST)</b>\n\n"
            f"Found <b>{len(matched_jobs)}</b> verified internship opportunities matching your profile (Score 8+/10)!\n"
            f"🏆 <b>Big Tech Opportunities:</b> {big_tech_count}\n"
            f"🎯 <b>Target Stack:</b> <i>MERN, PostgreSQL (PG), Agentic AI, Python, Full Stack & SDE</i>\n"
            f"<i>Strict filtering applied: No ML model training, No Java/Spring.</i>"
        )
        self.send_message(header_text)
        time.sleep(1.2)

        for job in matched_jobs:
            success = self.send_job_alert(job)
            if success:
                sent_count += 1
            time.sleep(1.2)  # Avoid Telegram rate limits

        return sent_count

    def test_alert(self) -> bool:
        """Send a test message to verify the bot setup."""
        if not self.is_configured():
            print("[Notifier] Cannot test: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
            return False

        test_msg = (
            "🎉 <b>Job Hunter Bot is Online!</b>\n\n"
            "Your Telegram alerts are properly configured.\n"
            "You will receive daily curated internship updates right here at 9:00 AM IST!\n"
            "<i>Filter: Score 8+/10 | Strictly Internships | Big Tech Highlighted</i>"
        )
        return self.send_message(test_msg)
