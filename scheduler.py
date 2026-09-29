import datetime
import subprocess
import sys
import time


# Set to True only if you want to run the scheduler locally on your machine.
# Default is False because GitHub Actions (.github/workflows/daily_job_hunter.yml)
# handles the automated daily 9:00 AM IST cloud execution.
ENABLED = False


def get_seconds_until_next_run(target_hour=9, target_minute=0):
    """Calculate seconds until next 9:00 AM IST (system local time if in IST)."""
    now = datetime.datetime.now()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()


def run_hunter():
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launching daily internship hunt...")
    subprocess.run([sys.executable, "main.py"])


def main():
    if not ENABLED:
        print("==================================================")
        print(" [!] Local Scheduler is currently DISABLED.")
        print(" Automated daily hunts are handled in the cloud by")
        print(" GitHub Actions (.github/workflows/daily_job_hunter.yml)")
        print(" at 9:00 AM IST every day.")
        print(" To re-enable local scheduling, set ENABLED = True")
        print(" at the top of scheduler.py.")
        print("==================================================")
        return

    print("==================================================")
    print(" Daily Internship Hunter Local Daemon (ACTIVE)")
    print(" Scheduled for: 9:00 AM daily")
    print("==================================================")

    while True:
        wait_seconds = get_seconds_until_next_run(9, 0)
        hours = int(wait_seconds // 3600)
        minutes = int((wait_seconds % 3600) // 60)
        print(f"[*] Next run in ~{hours}h {minutes}m at 09:00 AM. Waiting...")
        time.sleep(wait_seconds)
        run_hunter()
        # Small sleep so it doesn't fire twice in the same minute
        time.sleep(65)


if __name__ == "__main__":
    main()
