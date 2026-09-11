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
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                return True
            else:
                print(f"[Notifier] Telegram API error ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            print(f"[Notifier] Failed to send Telegram message: {e}")
            return False

    def send_job_alert(self, job: Dict[str, Any]) -> bool:
        """Format and send an attractive job card to Telegram with direct Apply button."""
        title = html.escape(job.get("title", "Untitled Role"))
        company = html.escape(job.get("company", "Unknown Company"))
        location = html.escape(job.get("location", "India"))
        source = html.escape(job.get("source", "LinkedIn (India)"))
        score = job.get("score", 7)
        summary = html.escape(job.get("match_summary", ""))
        skills = ", ".join(job.get("key_skills", [])) or "MERN / GenAI"
        apply_url = job.get("url", "")
        is_india = job.get("is_india", False)

        score_emoji = "🔥" if score >= 9 else ("✨" if score >= 8 else "⭐")
        loc_icon = "🇮🇳" if is_india else "📍"
        india_tag = " [India]" if is_india else ""

        card = (
            f"{score_emoji} <b>New Match ({score}/10){india_tag}</b>: <b>{title}</b>\n\n"
            f"🏢 <b>Company:</b> {company}\n"
            f"{loc_icon} <b>Location:</b> {location}\n"
            f"💼 <b>Source:</b> {source}\n"
            f"💡 <b>Skills:</b> <code>{html.escape(skills)}</code>\n\n"
            f"🤖 <b>Gemini Insight:</b>\n<i>{summary}</i>\n\n"
            f"🔗 <a href=\"{apply_url}\"><b>Tap to View & Apply</b></a>"
        )

        button_text = "🚀 Apply on LinkedIn" if "linkedin" in source.lower() else "🚀 Apply Now"
        reply_markup = {
            "inline_keyboard": [
                [{"text": button_text, "url": apply_url}]
            ]
        }

        return self.send_message(card, reply_markup=reply_markup)

    def send_batch_summary(self, matched_jobs: List[Dict[str, Any]]) -> int:
        """Send alerts for a list of matched jobs with polite delay between messages."""
        if not self.is_configured():
            print("[Notifier] Telegram not configured. Printing jobs to console instead:")
            for j in matched_jobs:
                print(f" -> [{j.get('score')}/10] {j.get('title')} at {j.get('company')} ({j.get('url')})")
            return len(matched_jobs)

        sent_count = 0
        header_text = (
            f"🚀 <b>Daily Job Hunter Update</b>\n"
            f"Found <b>{len(matched_jobs)}</b> strong matches tailored to your profile today!\n"
            f"<i>Targeting: MERN Stack, Full-Stack, Web Dev & GenAI Internships</i>"
        )
        self.send_message(header_text)
        time.sleep(1)

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
            "You will receive daily curated internship and job updates right here!"
        )
        return self.send_message(test_msg)
