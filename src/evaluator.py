import json
import os
import re
import time
from typing import List, Dict, Any
import requests


class JobEvaluator:
    def __init__(self, profile_path: str = "profile.json", api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.profile = self._load_profile(profile_path)

    def _load_profile(self, profile_path: str) -> Dict[str, Any]:
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f).get("candidate", {})
            except Exception as e:
                print(f"[Warning] Failed to load profile: {e}")
        return {}

    def _heuristic_evaluate(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback evaluation using smart keyword heuristics when API key is missing."""
        title_lower = job.get("title", "").lower()
        desc_lower = job.get("description", "").lower()
        combined = f"{title_lower} {desc_lower}"
        
        # 1. Disqualify if title indicates senior/lead or non-tech role
        senior_title_keywords = ["senior", "sr.", "sr ", "lead", "staff", "principal", "architect", "director", "head of", "manager", "vp "]
        for dis in senior_title_keywords:
            if dis in title_lower:
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 2,
                    "match_summary": f"Disqualified: Title indicates senior role ('{dis}').",
                    "key_skills": []
                }

        non_tech_keywords = ["legal", "marketing", "sales", "hr", "recruiter", "telecaller", "finance", "accountant", "business development", "bpo", "cleaning", "maintenance", "maid", "nurse", "store"]
        for non_tech in non_tech_keywords:
            pattern = r"\b" + re.escape(non_tech) + r"\b"
            if re.search(pattern, title_lower):
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 1,
                    "match_summary": f"Disqualified: Non-tech field ('{non_tech}').",
                    "key_skills": []
                }

        # Disqualify high years of experience in description
        for exp in ["5+ years", "6+ years", "7+ years", "8+ years", "10+ years"]:
            if exp in desc_lower:
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 3,
                    "match_summary": f"Disqualified: Requires extensive experience ('{exp}').",
                    "key_skills": []
                }

        # 2. Check technical skills with word boundaries
        tech_keywords = [
            "react", "next.js", "nextjs", "mern", "node", "nodejs", "typescript",
            "javascript", "express", "mongodb", "postgresql", "redis", "genai",
            "generative ai", "ai", "llm", "c++", "full stack", "fullstack", "backend", "frontend", "web development"
        ]
        matched_skills = []
        for kw in tech_keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            if re.search(pattern, combined):
                matched_skills.append(kw.upper() if len(kw) <= 4 else kw.title())

        # 3. Check for intern / junior / entry level signals
        intern_keywords = ["intern", "internship", "trainee", "fresher", "junior", "entry level", "graduate", "student", "2027"]
        is_early_career = any(re.search(r"\b" + re.escape(w) + r"\b", combined) for w in intern_keywords)
        is_tech_title = any(w in title_lower for w in ["intern", "developer", "engineer", "software", "programmer", "fullstack", "full stack", "backend", "frontend", "sde"])

        priority_companies = self.profile.get("priority_companies", [
            "Google", "Microsoft", "Amazon", "Meta", "Apple", "Adobe", "Salesforce",
            "Atlassian", "Uber", "Oracle", "Cisco", "Goldman Sachs", "JP Morgan",
            "Flipkart", "Swiggy", "Zomato", "Razorpay"
        ])
        company_and_title = f"{job.get('company', '')} {title_lower}".lower()
        is_big_tech = any(re.search(r"\b" + re.escape(comp.lower()) + r"\b", company_and_title) for comp in priority_companies)
        is_winter = any(w in title_lower or w in desc_lower for w in ["winter intern", "winter internship", "6 month intern", "6-month intern", "winter 2026", "winter 2027"])

        if not is_tech_title and not matched_skills and not is_big_tech:
            return {
                "id": job["id"],
                "is_match": False,
                "score": 2,
                "match_summary": "Not a relevant tech engineering opportunity.",
                "key_skills": []
            }

        score = 5
        if matched_skills:
            score += min(len(matched_skills), 3)  # +1 to +3
        if is_early_career:
            score += 2  # +2 for early career / intern
        if is_tech_title:
            score += 1
        if is_big_tech:
            score += 2  # Boost for Big Tech / Tier-1
        if is_winter:
            score += 1  # Boost for Winter/Upcoming

        score = min(score, 10)
        is_match = score >= 7 and (len(matched_skills) > 0 or is_big_tech)

        summary_parts = []
        if is_big_tech:
            summary_parts.append("🏆 Big Tech / Tier-1 Company")
        if is_winter:
            summary_parts.append("❄️ Winter / Upcoming Internship")
        if matched_skills:
            summary_parts.append(f"Skills: {', '.join(matched_skills[:4])}")

        return {
            "id": job["id"],
            "is_match": is_match,
            "score": score,
            "match_summary": " | ".join(summary_parts) if summary_parts else "Relevant engineering opportunity",
            "key_skills": matched_skills
        }

    def _call_gemini_batch(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate a batch of jobs in a single Gemini API call."""
        if not self.api_key:
            return [self._heuristic_evaluate(j) for j in jobs]

        # Prepare compact job descriptions for prompt
        compact_jobs = []
        for j in jobs:
            compact_jobs.append({
                "id": j["id"],
                "title": j["title"],
                "company": j["company"],
                "location": j.get("location", ""),
                "description_snippet": j.get("description", "")[:500]
            })

        prompt = f"""
You are an expert AI tech recruiter and career advisor reviewing job opportunities for:
Candidate: {self.profile.get('name', 'Anuj Acharjee')}
Education: {self.profile.get('education', 'B.Tech CSE, Narula Institute of Technology, expected graduation May 2027')}
Status: Looking for Winter 2026/2027 internships, Big Tech & startup SDE/Web/GenAI internships, and 2027 graduate/fresher roles.
Technical Skills: {json.dumps(self.profile.get('skills', {}))}
Priority Companies: {json.dumps(self.profile.get('priority_companies', []))}
SPECIAL HIGH PRIORITY:
1. Winter 2026/2027 internships & 6-month internships (give highest scores 9-10/10).
2. Big Tech & Tier-1 companies (Google, Microsoft, Amazon, Adobe, Atlassian, Uber, Salesforce, Goldman Sachs, Flipkart, Swiggy, etc.) (give highest scores 9-10/10).
3. Web Dev (MERN, React, Next.js, Node.js, TypeScript) and Generative AI internships.

Disqualifiers: Exclude jobs requiring 3+ years experience, senior/lead/manager roles, non-tech roles (telecalling, marketing, sales).

Carefully evaluate the following {len(compact_jobs)} job listings:
{json.dumps(compact_jobs, indent=2)}

For EACH job, return:
- "id": exact job id provided
- "is_match": boolean (true if role is suitable for an intern/fresher with MERN / TypeScript / Web Dev / GenAI background or Big Tech intern; false if senior, irrelevant, or spam)
- "score": integer 1 to 10 (10 = dream match like Google/Amazon winter intern or perfect MERN stack role, 1 = completely irrelevant)
- "match_summary": 1-2 punchy sentences explaining why it fits Anuj's specific profile (mention if it's Big Tech or Winter internship)
- "key_skills": list of matched skills (e.g. ["Next.js", "TypeScript", "Node.js"])

OUTPUT FORMAT: Return ONLY a valid JSON array of objects. Do not include markdown code block formatting or explanation outside JSON.
"""

        # Supported Gemini models in order of preference (gemini-flash-lite-latest is fast & stable on free tier)
        models = ["gemini-flash-lite-latest", "gemini-flash-latest", "gemini-pro-latest"]
        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        clean_text = re.sub(r"^```json\s*", "", text_content.strip(), flags=re.IGNORECASE)
                        clean_text = re.sub(r"\s*```$", "", clean_text.strip())
                        evaluations = json.loads(clean_text)
                        if isinstance(evaluations, list):
                            return evaluations
                else:
                    print(f"[Evaluator] Gemini {model} API returned status {resp.status_code}: {resp.text[:150]}")
            except Exception as e:
                print(f"[Evaluator] Error calling Gemini {model}: {e}")

        # Fallback if Gemini calls fail
        print("[Evaluator] Falling back to heuristic evaluation for this batch.")
        return [self._heuristic_evaluate(j) for j in jobs]

    def evaluate_all(self, jobs: List[Dict[str, Any]], batch_size: int = 15) -> List[Dict[str, Any]]:
        """Evaluate all jobs: pre-filters clear non-matches, then uses Gemini on candidates."""
        if not jobs:
            return []

        # 1. Fast pre-filter: identify strong tech candidates vs obvious non-matches
        evaluated_results = []
        prospective_jobs = []

        for job in jobs:
            h_eval = self._heuristic_evaluate(job)
            # If disqualified or low score (< 6) with no tech skills, don't waste Gemini quota
            if h_eval.get("score", 0) < 6 and not h_eval.get("is_match"):
                job.update(h_eval)
                evaluated_results.append(job)
            else:
                prospective_jobs.append(job)

        print(f"[Evaluator] Pre-filtered {len(jobs)} jobs -> {len(prospective_jobs)} prospective candidates for Gemini review.")

        eval_map = {}
        if self.api_key and prospective_jobs:
            for i in range(0, len(prospective_jobs), batch_size):
                batch = prospective_jobs[i : i + batch_size]
                batch_evals = self._call_gemini_batch(batch)
                for item in batch_evals:
                    if isinstance(item, dict) and "id" in item:
                        eval_map[item["id"]] = item
                if i + batch_size < len(prospective_jobs):
                    time.sleep(4)  # Respect free tier rate limits (15 RPM)

        # Merge results for candidates
        for job in prospective_jobs:
            job_eval = eval_map.get(job["id"], self._heuristic_evaluate(job))
            job["is_match"] = job_eval.get("is_match", False)
            job["score"] = job_eval.get("score", 0)
            job["match_summary"] = job_eval.get("match_summary", "")
            job["key_skills"] = job_eval.get("key_skills", [])
            evaluated_results.append(job)

        # Sort by score descending
        evaluated_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return evaluated_results
