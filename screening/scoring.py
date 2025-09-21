import re
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer


MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def tokenize_skills(text: str):
    if not text:
        return []
    tokens = re.split(r"[\n,;•\-\|]+", text.lower())
    return [t.strip() for t in tokens if 1 <= len(t.split()) <= 4 and t.strip()]


def hard_skill_score(jd_skills, resume_text: str):
    resume = (resume_text or "").lower()
    missing = []
    present = []

    if not jd_skills:
        return 50.0, []

    for s in jd_skills:
        s_norm = s.lower().strip()
        try:
           
            if s_norm in resume or fuzz.partial_ratio(s_norm, resume) > 75:
                present.append(s)
            else:
                missing.append(s)
        except Exception:
            missing.append(s)

    score = (len(present) / len(jd_skills)) * 100
    return round(score, 2), missing

def semantic_score(jd_text: str, resume_text: str):
    if not jd_text or not resume_text:
        return 50.0
    try:
        emb = MODEL.encode([jd_text, resume_text], convert_to_numpy=True)
        sim = np.dot(emb[0], emb[1]) / (np.linalg.norm(emb[0]) * np.linalg.norm(emb[1]) + 1e-12)
        return round(((sim + 1) / 2) * 100, 2)
    except Exception:
        return 50.0

def final_score(hard: float, semantic: float, hard_weight=0.6, semantic_weight=0.4):
    """
    Weighted combination of hard and semantic scores.
    """
    try:
        return round(hard_weight * float(hard) + semantic_weight * float(semantic), 2)
    except Exception:
        return None

def verdict(score: float):
    if score is None:
        return "Unknown"
    if score >= 80:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"

def analyze_resume(jd_text: str, resume_text: str, jd_skills=None):
    jd_skills = jd_skills or tokenize_skills(jd_text)
    hard, missing = hard_skill_score(jd_skills, resume_text)
    semantic = semantic_score(jd_text, resume_text)
    final = final_score(hard, semantic)
    return {
        "hard_score": hard,
        "semantic_score": semantic,
        "final_score": final,
        "missing_skills": missing,
        "verdict": verdict(final)
    }

