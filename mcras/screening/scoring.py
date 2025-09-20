import re, numpy as np
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

def tokenize_skills(text):
    tokens = re.split(r"[\n,;•\-]+", text.lower())
    return [t.strip() for t in tokens if 1 <= len(t.split()) <= 4]

def hard_skill_score(jd_skills, resume_text):
    resume = resume_text.lower()
    missing = []
    present = []
    for s in jd_skills:
        if s in resume or fuzz.partial_ratio(s, resume) > 75:
            present.append(s)
        else:
            missing.append(s)
    score = (len(present)/len(jd_skills))*100 if jd_skills else 50
    return round(score,2), missing

def semantic_score(jd_text, resume_text):
    emb = MODEL.encode([jd_text, resume_text], convert_to_numpy=True)
    sim = np.dot(emb[0], emb[1])/(np.linalg.norm(emb[0])*np.linalg.norm(emb[1]))
    return round(((sim+1)/2)*100, 2)

def final_score(hard, semantic):
    return round(0.6*hard + 0.4*semantic, 2)

def verdict(score):
    if score >= 80: return "High"
    if score >= 55: return "Medium"
    return "Low"
