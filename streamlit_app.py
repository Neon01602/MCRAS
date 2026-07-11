"""
MCRAS — AI Candidate Screening (Streamlit Cloud version)

This is a standalone rewrite of streamlit_app.py. The original file imported
`mcras.model.MCRAS` and `mcras.data_loader.preprocess_input`, which do not
exist anywhere in this repo — that file was written for a different,
never-built project. This version wraps your actual, working scoring
pipeline (the same logic as screening/scoring.py + screening/utils.py) with
no Django dependency, so it runs standalone on Streamlit Community Cloud.

Note on video/Vosk transcription: it's included as best-effort and optional.
Streamlit Community Cloud has limited build time/memory, and the Vosk model
file (tens of MB, not in this repo) has to be downloaded at startup. If it's
not available, the app just skips video transcription instead of crashing —
see the try/except around vosk import below.
"""

import io
import os
import re
import json
import logging
from collections import Counter

import streamlit as st
from rapidfuzz import fuzz
import requests

from data_loader import (
    extract_text_from_upload,
    transcribe_video_upload,
    tokenize_skills,
    extract_important_keywords,
    VOSK_AVAILABLE,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Config — reads from Streamlit secrets first, falls back to env vars
# ---------------------------------------------------------------------
def get_secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key, default)

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
GEMINI_MODEL = get_secret("GEMINI_MODEL", "gemini-2.0-flash")

# ---------------------------------------------------------------------
# Optional: sentence-transformers (semantic similarity). Heavy dependency —
# guarded so the app still works (with hard-skill + Gemini scoring only)
# if it fails to load on a resource-constrained deploy.
# ---------------------------------------------------------------------
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SEMANTIC_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    SEMANTIC_AVAILABLE = True
except Exception as e:
    logger.warning("sentence-transformers unavailable, semantic scoring disabled: %s", e)
    SEMANTIC_AVAILABLE = False
    resume = (resume_text or "").lower()
    missing, present = [], []
    if not jd_skills:
        return 50.0, []
    for s in jd_skills:
        s_norm = s.lower().strip()
        if s_norm in resume or fuzz.partial_ratio(s_norm, resume) > 75:
            present.append(s)
        else:
            missing.append(s)
    return round((len(present) / len(jd_skills)) * 100, 2), missing


def semantic_score(jd_text: str, resume_text: str):
    if not SEMANTIC_AVAILABLE or not jd_text or not resume_text:
        return 50.0
    try:
        emb = SEMANTIC_MODEL.encode([jd_text, resume_text], convert_to_numpy=True)
        sim = float(np.dot(emb[0], emb[1]) / (np.linalg.norm(emb[0]) * np.linalg.norm(emb[1]) + 1e-12))
        return round(((sim + 1) / 2) * 100, 2)
    except Exception:
        return 50.0


def gemini_score(jd_text: str, resume_text: str):
    if not GEMINI_API_KEY:
        return {"match_score": None, "missing_skills": [], "feedback": "No Gemini API key configured — add GEMINI_API_KEY in Streamlit secrets."}
    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
        prompt = f"""You are an AI recruiter. Analyze the resume vs the job description.
Return ONLY valid JSON with keys: match_score (0-100 integer), missing_skills (list of strings), feedback (short string).

Job Description:
{jd_text}

Resume:
{resume_text}"""
        resp = requests.post(api_url, headers=headers, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        resp.raise_for_status()
        text_output = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text_output = text_output.strip("`").replace("json\n", "").replace("json", "")
        return json.loads(text_output)
    except Exception as e:
        logger.exception("Gemini scoring failed: %s", e)
        return {"match_score": None, "missing_skills": [], "feedback": f"Gemini API error: {e}"}


def verdict(score: float):
    if score is None:
        return "Unknown"
    if score >= 80:
        return "High"
    if score >= 55:
        return "Medium"
    return "Low"


def analyze(jd_text: str, resume_text: str):
    jd_skills = tokenize_skills(jd_text)
    hard, missing = hard_skill_score(jd_skills, resume_text)
    semantic = semantic_score(jd_text, resume_text)
    gemini = gemini_score(jd_text, resume_text)
    gemini_val = gemini.get("match_score") or 0
    final = round(0.4 * hard + 0.4 * gemini_val + 0.2 * semantic, 2)
    return {
        "final_score": final,
        "hard_score": hard,
        "semantic_score": semantic,
        "gemini_score": gemini_val,
        "missing_skills": missing or gemini.get("missing_skills", []),
        "feedback": gemini.get("feedback", ""),
        "verdict": verdict(final),
    }


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------
st.set_page_config(page_title="MCRAS — AI Candidate Screening", layout="wide")
st.title("🏆 MCRAS — AI Candidate Screening")
st.caption(
    "Standalone Streamlit version. "
    + ("Semantic scoring: ON. " if SEMANTIC_AVAILABLE else "Semantic scoring: OFF (sentence-transformers not loaded). ")
    + ("Video transcription: ON." if VOSK_AVAILABLE else "Video transcription: OFF (Vosk model not bundled).")
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Job Description")
    jd_text = st.text_area("Paste the job description", height=220)
    jd_pdf = st.file_uploader("...or upload a JD PDF", type=["pdf"], key="jd_pdf")
    if jd_pdf is not None:
        jd_text = extract_text_from_upload(jd_pdf)
        st.text_area("Extracted JD text", jd_text, height=150, key="jd_extracted")

with col2:
    st.subheader("Candidate")
    resume_file = st.file_uploader("Resume (PDF or DOCX)", type=["pdf", "docx"], key="resume")
    video_file = st.file_uploader("Video submission (optional)", type=["mp4", "mov", "webm"], key="video")

if st.button("Score Candidate", type="primary"):
    if not jd_text or not resume_file:
        st.error("Please provide a job description and a resume.")
    else:
        with st.spinner("Extracting resume text..."):
            resume_text = extract_text_from_upload(resume_file)

        if video_file is not None:
            with st.spinner("Transcribing video (best-effort)..."):
                video_text = transcribe_video_upload(video_file)
                if video_text:
                    resume_text += "\n" + video_text
                    st.info("Video transcript added to candidate text.")
                else:
                    st.warning("Video transcription unavailable in this environment — scoring on resume text only.")

        with st.spinner("Scoring candidate..."):
            result = analyze(jd_text, resume_text)

        st.subheader("Result")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Final Score", result["final_score"])
        c2.metric("Hard-Skill Score", result["hard_score"])
        c3.metric("Semantic Score", result["semantic_score"])
        c4.metric("Gemini Score", result["gemini_score"])

        st.write(f"**Verdict:** {result['verdict']}")
        if result["missing_skills"]:
            st.write("**Missing skills:**", ", ".join(result["missing_skills"]))
        if result["feedback"]:
            st.write("**Feedback:**", result["feedback"])

        with st.expander("Extracted candidate text"):
            st.text(resume_text[:3000])
