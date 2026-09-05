import argparse
import os
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return
    except ImportError:
        pass

    # Zero-dependency fallback parser for local .env files
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass

load_env()

from src.storage import JobStorage
from src.fetchers import fetch_all_jobs
from src.evaluator import JobEvaluator
from src.notifier import TelegramNotifier


def main():

    parser = argparse.ArgumentParser(description="Automated Daily Job Hunter for Anuj Acharjee")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and evaluate without sending alerts or saving state")
    parser.add_argument("--test-telegram", action="store_true", help="Send a test message to verify Telegram bot setup")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MAX_JOBS_PER_RUN", 10)), help="Max jobs to alert per run")
    parser.add_argument("--min-score", type=int, default=int(os.getenv("MIN_MATCH_SCORE", 7)), help="Min score (1-10) to alert")
    args = parser.parse_args()

    notifier = TelegramNotifier()

    if args.test_telegram:
        print("[Main] Sending test notification to Telegram...")
        success = notifier.test_alert()
        if success:
            print("[Success] Telegram message sent successfully! Check your phone.")
        else:
            print("[Error] Failed to send Telegram message. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your .env file.")
        sys.exit(0 if success else 1)

    print("==================================================")
    print("[*] Starting Daily Job Hunter")
    print(f"[*] Targeting: MERN / Next.js / Full-Stack & GenAI Internships")
    print(f"[*] Min Score Threshold: {args.min_score}/10 | Max Alerts: {args.limit}")
    print("==================================================")

    storage = JobStorage("data/seen_jobs.json")
    evaluator = JobEvaluator("profile.json")

    # 1. Fetch fresh jobs
    unseen_jobs = fetch_all_jobs(storage)
    if not unseen_jobs:
        print("[Main] No new unseen job postings found today. Will check again on next scheduled run.")
        return

    # 2. Evaluate with Gemini AI
    evaluated_jobs = evaluator.evaluate_all(unseen_jobs)

    # 3. Filter for quality matches
    matched_jobs = [
        j for j in evaluated_jobs
        if j.get("is_match") and j.get("score", 0) >= args.min_score
    ]

    print(f"[Main] Evaluated {len(evaluated_jobs)} jobs. Found {len(matched_jobs)} matches meeting score >= {args.min_score}.")

    if not matched_jobs:
        print("[Main] None of the new jobs met the quality/relevance threshold today.")
        return

    # Take top N matches
    top_matches = matched_jobs[: args.limit]

    if args.dry_run:
        print("\n--- [DRY RUN] Matched Opportunities (Not Sending Alerts) ---")
        for idx, job in enumerate(top_matches, 1):
            print(f"\n{idx}. [{job.get('score')}/10] {job.get('title')}")
            print(f"   Company:  {job.get('company')} | Location: {job.get('location')}")
            print(f"   Source:   {job.get('source')}")
            print(f"   Reason:   {job.get('match_summary')}")
            print(f"   Skills:   {', '.join(job.get('key_skills', []))}")
            print(f"   URL:      {job.get('url')}")
        print("\n[DRY RUN complete - seen_jobs.json was not modified]")
        return

    # 4. Dispatch alerts
    sent_count = notifier.send_batch_summary(top_matches)
    print(f"[Main] Dispatched {sent_count} alerts.")

    # 5. Persist seen jobs so they won't be sent again
    for job in top_matches:
        storage.add(job["id"], job["title"], job["company"], job["url"])
    storage.save()

    print("[Main] Finished run successfully.")


if __name__ == "__main__":
    main()
