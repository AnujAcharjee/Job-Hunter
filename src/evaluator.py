import json
import os
import re
import time
from typing import List, Dict, Any
import requests
from src.date_utils import is_posted_within_last_week, is_job_expired


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

    def is_big_tech_company(self, company_name: str) -> bool:
        """Check if company belongs to Tier-1 / Big Tech."""
        priority_companies = self.profile.get("priority_companies", [
            "Google", "Microsoft", "Amazon", "Meta", "Apple", "Adobe", "Salesforce",
            "Atlassian", "Uber", "Oracle", "Cisco", "Goldman Sachs", "JP Morgan",
            "Morgan Stanley", "DE Shaw", "Intuit", "Flipkart", "Swiggy", "Zomato",
            "Razorpay", "CRED", "PhonePe", "Stripe", "Databricks", "Snowflake", "NVIDIA"
        ])
        comp_lower = company_name.lower()
        for p in priority_companies:
            if re.search(r"\b" + re.escape(p.lower()) + r"\b", comp_lower):
                return True
        return False

    def _heuristic_evaluate(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Strict rule-based evaluation: Internships only, no ML/Java-Spring, MERN/PG/Agentic AI/Python/SDE focus."""
        title_lower = job.get("title", "").lower()
        desc_lower = job.get("description", "").lower()
        source_lower = job.get("source", "").lower()
        combined = f"{title_lower} {desc_lower} {source_lower}"

        # 0. STRICT DISQUALIFIER: Must be published within last week and not expired
        posted_date = job.get("posted_date", "")
        if posted_date and not is_posted_within_last_week(posted_date):
            return {
                "id": job["id"],
                "is_match": False,
                "score": 1,
                "match_summary": f"Disqualified: Published over 1 week ago ({posted_date}).",
                "key_skills": [],
                "is_big_tech": False
            }
        if is_job_expired(job):
            return {
                "id": job["id"],
                "is_match": False,
                "score": 1,
                "match_summary": "Disqualified: Application deadline expired or closed.",
                "key_skills": [],
                "is_big_tech": False
            }

        # 1. Role-Type Disqualification based on search_mode
        search_mode = self.profile.get("search_mode", "internship").lower()
        intern_keywords = ["intern", "internship", "trainee", "student", "fellowship"]
        is_intern_source = any(s in source_lower for s in ["internshala", "aicte"])
        is_intern = any(re.search(r"\b" + re.escape(w) + r"\b", combined) for w in intern_keywords) or is_intern_source

        if search_mode == "internship":
            if not is_intern:
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 1,
                    "match_summary": "Disqualified: Search mode is set strictly to internships (non-internship role).",
                    "key_skills": [],
                    "is_big_tech": False
                }
        elif search_mode == "full_time":
            if is_intern:
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 1,
                    "match_summary": "Disqualified: Search mode is set strictly to full-time roles (internship role).",
                    "key_skills": [],
                    "is_big_tech": False
                }

        # 2. STRICT DISQUALIFIER: Java / Spring / Spring Boot
        if re.search(r"\b(spring|springboot|spring boot|j2ee|hibernate)\b", combined) or (
            re.search(r"\bjava\b", combined) and not re.search(r"\b(javascript|typescript)\b", combined)
        ):
            return {
                "id": job["id"],
                "is_match": False,
                "score": 1,
                "match_summary": "Disqualified: Excluded Java/Spring technology stack.",
                "key_skills": [],
                "is_big_tech": False
            }

        # 3. STRICT DISQUALIFIER: Machine Learning / Deep Learning / Data Science
        ml_patterns = [
            "machine learning", "deep learning", "data science", "data scientist",
            "computer vision", "nlp researcher", "ml engineer", "model training",
            "scikit-learn", "tensorflow", "pytorch"
        ]
        if any(kw in combined for kw in ml_patterns) or re.search(r"\bml\b", title_lower):
            # Allow Agentic AI / LLM APIs / RAG, but disqualify pure ML/Data Science model training
            if "agentic" not in combined and "prompt" not in combined and "rag" not in combined:
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 1,
                    "match_summary": "Disqualified: Excluded Machine Learning / Data Science role.",
                    "key_skills": [],
                    "is_big_tech": False
                }

        # 4. STRICT DISQUALIFIER: Senior or Non-tech roles
        senior_keywords = ["senior", "sr.", "sr ", "lead", "staff", "principal", "architect", "director", "manager", "head of"]
        for dis in senior_keywords:
            if re.search(r"\b" + re.escape(dis) + r"\b", title_lower):
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 1,
                    "match_summary": f"Disqualified: Title indicates senior role ('{dis}').",
                    "key_skills": [],
                    "is_big_tech": False
                }

        non_tech_keywords = ["video", "content writing", "seo", "sales", "telecall", "marketing", "hr ", "recruiter", "graphic", "business development", "bpo", "cleaning", "operations trainer"]
        for nt in non_tech_keywords:
            if nt in title_lower:
                return {
                    "id": job["id"],
                    "is_match": False,
                    "score": 1,
                    "match_summary": f"Disqualified: Non-tech field ('{nt}').",
                    "key_skills": [],
                    "is_big_tech": False
                }

        # 5. Technical Stack Matching
        target_skills_map = {
            "MERN": ["mern", "mongodb", "express", "react", "node"],
            "Agentic AI": ["agentic", "ai agent", "ai agents", "langchain", "llamaindex", "tool calling", "llm api", "genai", "generative ai"],
            "Python": ["python", "fastapi", "flask", "django"],
            "PostgreSQL (PG)": ["postgresql", "postgres", "sql", "prisma"],
            "Full Stack": ["full stack", "fullstack", "frontend", "backend", "web development"],
            "SDE": ["sde", "software engineer", "software development engineer", "software developer"],
            "TypeScript/React": ["typescript", "javascript", "react.js", "reactjs", "next.js", "nextjs", "node.js", "nodejs"]
        }

        matched_skills = []
        for label, keywords in target_skills_map.items():
            if any(re.search(r"\b" + re.escape(k) + r"\b", combined) for k in keywords):
                matched_skills.append(label)

        # Big Tech check
        is_big_tech = self.is_big_tech_company(job.get("company", "")) or self.is_big_tech_company(job.get("title", ""))

        # Location checks (Prefer India)
        loc_str = f"{job.get('location', '')} {job.get('source', '')}".lower()
        indian_locations = ["india", "kolkata", "bengaluru", "bangalore", "hyderabad", "pune", "delhi", "noida", "gurgaon", "gurugram", "mumbai", "chennai", "remote"]
        is_india = any(re.search(r"\b" + re.escape(c) + r"\b", loc_str) for c in indian_locations)
        job["is_india"] = is_india

        # Foreign restriction penalty (roles candidate in India cannot work)
        is_foreign_restricted = any(w in loc_str or w in combined for w in ["us only", "usa only", "uk only", "ph-based only", "europe only", "germany only"])
        if is_foreign_restricted and not is_india:
            return {
                "id": job["id"],
                "is_match": False,
                "score": 1,
                "match_summary": "Disqualified: Role restricted to foreign location.",
                "key_skills": [],
                "is_big_tech": False
            }

        # Calculate strict score (Threshold = 8+)
        # Base starting score for verified tech internship
        score = 5

        if "MERN" in matched_skills or "TypeScript/React" in matched_skills:
            score += 2
        if "Agentic AI" in matched_skills:
            score += 2
        if "Python" in matched_skills:
            score += 1
        if "PostgreSQL (PG)" in matched_skills:
            score += 1
        if "SDE" in matched_skills or "Full Stack" in matched_skills:
            score += 1

        # Big Tech boost (guarantees 9-10 if stack matches)
        if is_big_tech:
            score += 3

        # Location boost
        if is_india:
            score += 1

        # Strict score clamp
        score = max(1, min(score, 10))

        # Strict matching: Score must be >= 8 and must have relevant target skills
        is_match = (score >= 8) and (len(matched_skills) > 0 or is_big_tech)

        summary_parts = []
        if is_big_tech:
            summary_parts.append("🏆 Big Tech / Tier-1 Internship")
        if "Agentic AI" in matched_skills:
            summary_parts.append("🤖 Agentic AI / GenAI Focus")
        if "MERN" in matched_skills or "Full Stack" in matched_skills:
            summary_parts.append("💻 MERN / Full Stack Role")
        if "PostgreSQL (PG)" in matched_skills:
            summary_parts.append("🐘 PostgreSQL (PG) Stack")
        if is_india:
            summary_parts.append("🇮🇳 India / Remote")

        return {
            "id": job["id"],
            "is_match": is_match,
            "score": score,
            "match_summary": " | ".join(summary_parts) if summary_parts else "Tech internship matching your target stack",
            "key_skills": matched_skills,
            "is_big_tech": is_big_tech
        }

    def _call_gemini_batch(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate candidate internships using Google Gemini AI with strict scoring criteria."""
        if not self.api_key:
            return [self._heuristic_evaluate(j) for j in jobs]

        compact_jobs = []
        for j in jobs:
            compact_jobs.append({
                "id": j["id"],
                "title": j["title"],
                "company": j["company"],
                "location": j.get("location", ""),
                "source": j.get("source", ""),
                "posted_date": j.get("posted_date", ""),
                "last_date": j.get("last_date", ""),
                "description_snippet": j.get("description", "")[:500]
            })

        search_mode = self.profile.get("search_mode", "internship").lower()
        if search_mode == "internship":
            role_type_rule = "1. MUST BE AN INTERNSHIP. Disqualify any full-time, experienced (2+ yrs), or non-intern roles (Score: 1-3, is_match: false)."
            status_line = "Status: Candidate looking STRICTLY for INTERNSHIPS (Winter 2026/2027, Summer 2027, 6-Month Internships, SDE / MERN / Agentic AI / Python)."
            opp_label = "INTERNSHIP"
        elif search_mode == "full_time":
            role_type_rule = "1. MUST BE A FULL-TIME ROLE. Disqualify any internship or trainee roles (Score: 1-3, is_match: false)."
            status_line = "Status: Candidate looking for FULL-TIME software engineering and developer roles."
            opp_label = "FULL-TIME TECH JOB"
        else:
            role_type_rule = "1. TARGET ROLES: Accepts both internships and full-time entry-level engineering roles matching the tech stack."
            status_line = "Status: Candidate open to both Internships and Full-Time engineering roles."
            opp_label = "TECH JOB / INTERNSHIP"

        prompt = f"""
You are an expert tech hiring manager and career advisor evaluating {opp_label} opportunities for:
Candidate: Tech Student / Aspiring Software Engineer
Education: {self.profile.get('education', 'B.Tech in Computer Science and Engineering (Expected 2027)')}
{status_line}

TARGET ROLES & SKILLS:
- MERN Stack (MongoDB, Express, React, Node.js)
- PostgreSQL (PG), SQL, Prisma
- Agentic AI, AI Agents, LLM APIs (Gemini/OpenAI), LangChain, RAG, Tool Calling
- Python (FastAPI, backend development, automation)
- Full Stack Developer & Software Development Engineer (SDE) Intern
- Big Tech & Tier-1 Companies: Google, Microsoft, Amazon, Meta, Apple, Adobe, Salesforce, Atlassian, Uber, Oracle, Cisco, Goldman Sachs, JP Morgan, Morgan Stanley, DE Shaw, Intuit, Flipkart, Swiggy, Zomato, Razorpay, CRED, PhonePe, NVIDIA, Snowflake, Databricks.

CRITICAL RULES & STRICT DISQUALIFIERS:
{role_type_rule}
2. STRICTLY NO JAVA / SPRING / SPRING BOOT. Disqualify immediately if the role requires or is centered on Java/Spring (Score: 1-2, is_match: false).
3. STRICTLY NO MACHINE LEARNING / DATA SCIENCE MODEL TRAINING. Disqualify pure ML/Data Science/Deep Learning/Computer Vision roles. Note: Building Agentic AI apps or LLM API tools is WELCOME, but ML model training/data science is NOT (Score: 1-2, is_match: false).
4. LOCATION: Highest priority for India (e.g. Kolkata, Bengaluru, Hyderabad, Pune, Delhi NCR, Gurgaon, Noida, Mumbai, Remote India). Reject foreign-restricted roles.
5. STRICT RATING THRESHOLD: Only assign score >= 8 if the internship is a genuinely strong match for the candidate's skills and status.
   - 9-10/10: Big Tech SDE/Web/GenAI internship in India OR dream MERN/PostgreSQL/Agentic AI internship.
   - 8/10: Solid tech internship in India matching MERN/Full Stack/Python/Agentic AI.
   - 1-7/10: Non-internship, irrelevant stack, or low quality (set is_match: false).
6. BIG TECH PRIORITY: Highlight and score Big Tech companies 9-10.
7. TIMELINESS & FRESHNESS: Must be published within the last 7 days and must NOT be expired or closed. Disqualify any listing published over 1 week ago or with a past deadline (Score: 1, is_match: false).

Carefully evaluate the following {len(compact_jobs)} internship listings:
{json.dumps(compact_jobs, indent=2)}

For EACH job, return:
- "id": exact job id provided
- "is_match": boolean (true ONLY if score >= 8 AND is an internship matching target stack)
- "score": integer 1 to 10 (STRICT: >= 8 only for genuine high-quality matches)
- "match_summary": 1-2 punchy sentences highlighting why it matches the candidate's profile (mention if Big Tech, India location, or key stack)
- "key_skills": list of matched skills (e.g. ["MERN", "PostgreSQL", "Python", "Agentic AI", "SDE"])
- "is_big_tech": boolean (true if company is Big Tech / Tier-1)

OUTPUT FORMAT: Return ONLY a valid JSON array of objects. Do not wrap in markdown or include text outside JSON.
"""

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
                    print(f"[Evaluator] Gemini {model} API returned status {resp.status_code}")
            except Exception as e:
                print(f"[Evaluator] Error calling Gemini {model}: {e}")

        # Fallback to strict heuristics
        print("[Evaluator] Falling back to strict heuristic evaluation for this batch.")
        return [self._heuristic_evaluate(j) for j in jobs]

    def evaluate_all(self, jobs: List[Dict[str, Any]], batch_size: int = 25) -> List[Dict[str, Any]]:
        """Evaluate all internships with pre-filtering and AI scoring."""
        if not jobs:
            return []

        evaluated_results = []
        prospective_jobs = []

        # 1. Fast pre-filter: rule out non-matches (only score >= 7 or Big Tech qualify for Gemini review)
        for job in jobs:
            h_eval = self._heuristic_evaluate(job)
            if h_eval.get("score", 0) < 7 and not h_eval.get("is_big_tech"):
                job.update(h_eval)
                evaluated_results.append(job)
            else:
                prospective_jobs.append(job)

        print(f"[Evaluator] Pre-filtered {len(jobs)} jobs -> {len(prospective_jobs)} high-potential candidates for Gemini AI evaluation.")

        eval_map = {}
        if self.api_key and prospective_jobs:
            total_batches = (len(prospective_jobs) + batch_size - 1) // batch_size
            for idx, i in enumerate(range(0, len(prospective_jobs), batch_size), 1):
                batch = prospective_jobs[i : i + batch_size]
                print(f"[Evaluator] Evaluating batch {idx}/{total_batches} ({len(batch)} internships) with Gemini AI...")
                batch_evals = self._call_gemini_batch(batch)
                for item in batch_evals:
                    if isinstance(item, dict) and "id" in item:
                        eval_map[item["id"]] = item
                if i + batch_size < len(prospective_jobs):
                    time.sleep(3)

        # Merge evaluations
        for job in prospective_jobs:
            job_eval = eval_map.get(job["id"], self._heuristic_evaluate(job))
            job["is_match"] = job_eval.get("is_match", False)
            job["score"] = job_eval.get("score", 0)
            job["match_summary"] = job_eval.get("match_summary", "")
            job["key_skills"] = job_eval.get("key_skills", [])
            job["is_big_tech"] = job_eval.get("is_big_tech", False) or self.is_big_tech_company(job.get("company", ""))
            
            loc_str = f"{job.get('location', '')} {job.get('source', '')}".lower()
            job["is_india"] = any(c in loc_str for c in ["india", "bengaluru", "bangalore", "kolkata", "hyderabad", "pune", "delhi", "noida", "gurgaon", "mumbai", "chennai", "remote"])
            
            # Ensure strict adherence: only >= 8 is match
            if job["score"] < 8:
                job["is_match"] = False

            evaluated_results.append(job)

        # Sort: Big Tech first, then score descending, then India
        evaluated_results.sort(key=lambda x: (
            1 if x.get("is_big_tech") else 0,
            x.get("score", 0),
            1 if x.get("is_india") else 0
        ), reverse=True)

        return evaluated_results
