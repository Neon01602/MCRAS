# scoring.py
import re
import numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer

# Load embedding model once
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# ----------------- Skill Tokenization -----------------
def tokenize_skills(text: str):
    """
    Tokenize a text into candidate skills.
    Filters out tokens that are too short/long (1-4 words).
    """
    if not text:
        return []
    tokens = re.split(r"[\n,;•\-\|]+", text.lower())
    return [t.strip() for t in tokens if 1 <= len(t.split()) <= 4 and t.strip()]

# ----------------- Hard Skill Matching -----------------
def hard_skill_score(jd_skills, resume_text: str):
    """
    Compare JD skills vs resume text using fuzzy matching.
    Returns score (0-100) and list of missing skills.
    """
    resume = (resume_text or "").lower()
    missing = []
    present = []

    if not jd_skills:
        return 50.0, []

    for s in jd_skills:
        s_norm = s.lower().strip()
        try:
            # check substring or fuzzy match
            if s_norm in resume or fuzz.partial_ratio(s_norm, resume) > 75:
                present.append(s)
            else:
                missing.append(s)
        except Exception:
            missing.append(s)

    score = (len(present) / len(jd_skills)) * 100
    return round(score, 2), missing

# ----------------- Semantic Matching -----------------
def semantic_score(jd_text: str, resume_text: str):
    """
    Compute semantic similarity between JD text and resume text using embeddings.
    Returns score mapped to 0-100.
    """
    if not jd_text or not resume_text:
        return 50.0
    try:
        emb = MODEL.encode([jd_text, resume_text], convert_to_numpy=True)
        sim = np.dot(emb[0], emb[1]) / (np.linalg.norm(emb[0]) * np.linalg.norm(emb[1]) + 1e-12)
        return round(((sim + 1) / 2) * 100, 2)
    except Exception:
        return 50.0

# ----------------- Combined Final Score -----------------
def final_score(hard: float, semantic: float, hard_weight=0.6, semantic_weight=0.4):
    """
    Weighted combination of hard and semantic scores.
    """
    try:
        return round(hard_weight * float(hard) + semantic_weight * float(semantic), 2)
    except Exception:
        return None

# ----------------- Verdict -----------------
def verdict(score: float):
    """
    Map score to categorical verdict: High / Medium / Low.
    """
    if score is None:
        return "Unknown"
    if score >= 80:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"

# ----------------- Full Resume Analysis -----------------
def analyze_resume(jd_text: str, resume_text: str, jd_skills=None):
    """
    Convenience function: compute hard, semantic, final scores, missing skills, and verdict.
    """
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
