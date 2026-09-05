import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Set


class JobStorage:
    def __init__(self, file_path: str = "data/seen_jobs.json"):
        self.file_path = Path(file_path)
        self.seen_data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.file_path.exists():
            return {"version": 1, "last_updated": "", "seen_ids": {}}
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict) or "seen_ids" not in data:
                    return {"version": 1, "last_updated": "", "seen_ids": {}}
                return data
        except Exception as e:
            print(f"[Warning] Failed to load seen jobs from {self.file_path}: {e}")
            return {"version": 1, "last_updated": "", "seen_ids": {}}

    @staticmethod
    def generate_job_id(title: str, company: str, url: str) -> str:
        """Create a stable hash identifier for a job listing."""
        clean_title = (title or "").strip().lower()
        clean_company = (company or "").strip().lower()
        clean_url = (url or "").split("?")[0].strip().lower()  # Remove tracking params
        combined = f"{clean_title}|{clean_company}|{clean_url}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:20]

    def is_seen(self, job_id: str) -> bool:
        return job_id in self.seen_data.get("seen_ids", {})

    def add(self, job_id: str, title: str, company: str, url: str):
        now_iso = datetime.now(timezone.utc).isoformat()
        if "seen_ids" not in self.seen_data:
            self.seen_data["seen_ids"] = {}
        self.seen_data["seen_ids"][job_id] = {
            "title": title,
            "company": company,
            "url": url,
            "seen_at": now_iso
        }
        self.seen_data["last_updated"] = now_iso

    def save(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        # Cap stored history to last 2000 jobs to keep the file compact
        seen_items = list(self.seen_data.get("seen_ids", {}).items())
        if len(seen_items) > 2000:
            seen_items = seen_items[-2000:]
            self.seen_data["seen_ids"] = dict(seen_items)

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.seen_data, f, indent=2, ensure_ascii=False)
        print(f"[Storage] Saved {len(self.seen_data.get('seen_ids', {}))} recorded jobs to {self.file_path}")
