import argparse
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
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
    parser = argparse.ArgumentParser(description="Automated Daily Internship Hunter")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and evaluate without sending alerts or saving state")
    parser.add_argument("--test-telegram", action="store_true", help="Send a test message to verify Telegram bot setup")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MAX_JOBS_PER_RUN", 0)), help="Max internships to alert (0 = unlimited / send all matches)")
    parser.add_argument("--min-score", type=int, default=int(os.getenv("MIN_MATCH_SCORE", 8)), help="Min score (1-10) to alert (strict: >= 8)")
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
    print("[*] Starting Daily Tech Internship Hunter (9:00 AM IST)")
    print(f"[*] Portals: Internshala, LinkedIn India, AICTE Portal, Naukri")
    print(f"[*] Targeting: MERN, PostgreSQL, Agentic AI, Python, Full Stack & SDE Internships")
    print(f"[*] Exclusions: STRICTLY No Java/Spring, No ML/Data Science")
    print(f"[*] Strict Threshold: Score >= {args.min_score}/10 | Big Tech Priority: Enabled")
    print(f"[*] Batch Limit: {'Unlimited (Send all matches)' if args.limit <= 0 else f'{args.limit} max'}")
    print("==================================================")

    storage = JobStorage("data/seen_jobs.json")
    evaluator = JobEvaluator("profile.json")

    # 1. Fetch fresh unseen tech opportunities from target portals
    unseen_jobs = fetch_all_jobs(storage, evaluator.profile)
    if not unseen_jobs:
        print("[Main] No new unseen internship postings found in this run. Will check again on next scheduled run.")
        return

    # 2. Evaluate with Gemini AI & strict heuristics
    evaluated_jobs = evaluator.evaluate_all(unseen_jobs)

    # 3. Filter strictly for score >= min_score (default >= 8) and is_match = True
    matched_jobs = [
        j for j in evaluated_jobs
        if j.get("is_match") and j.get("score", 0) >= args.min_score
    ]

    print(f"[Main] Evaluated {len(evaluated_jobs)} internships. Found {len(matched_jobs)} matches meeting score >= {args.min_score}/10.")

    if not matched_jobs:
        print(f"[Main] None of the new listings met the strict quality threshold (>={args.min_score}/10) today.")
        return

    # Send all matches unless a positive limit is explicitly requested
    if args.limit > 0:
        top_matches = matched_jobs[: args.limit]
    else:
        top_matches = matched_jobs

    if args.dry_run:
        print("\n--- [DRY RUN] Matched Internship Opportunities (Not Sending Alerts) ---")
        for idx, job in enumerate(top_matches, 1):
            big_tech_badge = " [🏆 BIG TECH]" if job.get("is_big_tech") else ""
            print(f"\n{idx}. [{job.get('score')}/10]{big_tech_badge} {job.get('title')}")
            print(f"   Company:  {job.get('company')} | Location: {job.get('location')}")
            print(f"   Source:   {job.get('source')}")
            print(f"   Insights: {job.get('match_summary')}")
            print(f"   Skills:   {', '.join(job.get('key_skills', []))}")
            print(f"   URL:      {job.get('url')}")
        print(f"\n[DRY RUN complete - {len(top_matches)} matches identified. seen_jobs.json was not modified]")
        return

    # 4. Dispatch Telegram alerts for ALL matching internships
    sent_count = notifier.send_batch_summary(top_matches)
    print(f"[Main] Dispatched {sent_count} alerts to Telegram.")

    # 5. Persist seen jobs so they won't be sent repeatedly
    for job in top_matches:
        storage.add(job["id"], job["title"], job["company"], job["url"])
    storage.save()

    print("[Main] Finished run successfully.")


if __name__ == "__main__":
    main()
