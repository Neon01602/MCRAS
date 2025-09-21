# utils.py
import io
import os
import json
import wave
import logging
from typing import Tuple
from collections import Counter
import re

import requests
import ffmpeg
import pdfplumber
from docx import Document
import nltk
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)

# ---------------- NLTK Stopwords ----------------
try:
    STOPWORDS = set(stopwords.words("english"))
except LookupError:
    nltk.download('stopwords')
    STOPWORDS = set(stopwords.words("english"))

# ---------------- Environment Variables ----------------
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-en-us-0.15")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ---------------- Helper Functions ----------------
def extract_important_keywords(jd_text, min_words=1, max_words=4, top_n=20):
    tokens = re.split(r"[\n,;•\-]+", jd_text.lower())
    keywords = []
    for token in tokens:
        token = token.strip()
        words = token.split()
        if min_words <= len(words) <= max_words and all(w not in STOPWORDS for w in words):
            keywords.append(token)
    freq = Counter(keywords)
    return [kw for kw, _ in freq.most_common(top_n)]

def keyword_boost_dynamic(resume_text, jd_text, weight=5):
    jd_keywords = extract_important_keywords(jd_text)
    resume_lower = resume_text.lower()
    score = 0
    matched = []
    for kw in jd_keywords:
        if kw in resume_lower:
            score += weight
            matched.append(kw)
    return score, matched

# ---------------- Resume / Document extraction ----------------
def extract_text(file_field) -> str:
    if not file_field:
        return ""
    try:
        file_field.open()
    except Exception:
        pass
    content = file_field.read()
    if isinstance(content, str):
        content = content.encode("utf-8", errors="ignore")
    name = getattr(file_field, "name", "").lower()
    bio = io.BytesIO(content)
    try:
        if name.endswith(".pdf"):
            text_pages = []
            with pdfplumber.open(bio) as pdf:
                for p in pdf.pages:
                    page_text = p.extract_text()
                    if page_text:
                        text_pages.append(page_text)
            return "\n".join(text_pages)
        elif name.endswith(".docx"):
            doc = Document(bio)
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            return content.decode("utf8", errors="ignore")
    except Exception as e:
        logger.exception("Error extracting text from %s: %s", name, e)
        return content.decode("utf8", errors="ignore")

# ---------------- Video transcription ----------------
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except Exception:
    VOSK_AVAILABLE = False

def transcribe_video(file_path: str) -> str:
    if not file_path or not VOSK_AVAILABLE or not os.path.exists(VOSK_MODEL_PATH):
        return ""
    wav_path = f"{file_path}.wav"
    try:
        ffmpeg.input(file_path).output(wav_path, ac=1, ar=16000).overwrite_output().run(quiet=True)
    except Exception as e:
        logger.exception("ffmpeg extraction failed: %s", e)
        return ""
    try:
        wf = wave.open(wav_path, "rb")
        model = Model(VOSK_MODEL_PATH)
        rec = KaldiRecognizer(model, wf.getframerate())
        text_chunks = []
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text_chunks.append(result.get("text", ""))
        final_result = json.loads(rec.FinalResult())
        text_chunks.append(final_result.get("text", ""))
        return " ".join([t for t in text_chunks if t])
    except Exception as e:
        logger.exception("Vosk transcription error: %s", e)
        return ""
    finally:
        try:
            wf.close()
        except Exception:
            pass
        try:
            os.remove(wav_path)
        except Exception:
            pass

# ---------------- Gemini API Integration ----------------
def analyze_resume_with_gemini(jd_text: str, resume_text: str, api_key: str = None) -> dict:
    api_key = api_key or GEMINI_API_KEY
    jd_text = jd_text or ""
    resume_text = resume_text or ""

    # --- Local Scoring ---
    def hard_skill_score(resume, jd):
        rw, jw = set(resume.lower().split()), set(jd.lower().split())
        return round(len(rw & jw) / max(len(jw), 1) * 100, 2)
    def semantic_score(resume, jd):
        return round(min(len(resume), len(jd)) / max(len(jd), 1) * 100, 2)
    def final_local(resume, jd):
        return round(0.5 * hard_skill_score(resume, jd) + 0.5 * semantic_score(resume, jd), 2)

    gemini_result = {"match_score": None, "missing_skills": [], "feedback": ""}
    if api_key:
        try:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
            headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
            prompt = f"""
            You are an AI recruiter. Analyze the resume vs the job description.
            Return ONLY valid JSON with keys:
            - match_score (0-100 integer)
            - missing_skills (list of strings)
            - feedback (short string)

            Job Description:
            {jd_text}

            Resume:
            {resume_text}
            """
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(api_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            text_output = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            if text_output.startswith("```"):
                text_output = text_output.strip("`").replace("json\n", "").replace("json", "")
            try:
                gemini_result = json.loads(text_output)
            except Exception:
                gemini_result["feedback"] = text_output or json.dumps(data)[:1000]
        except Exception as e:
            logger.exception("Gemini API request failed: %s", e)
            gemini_result["feedback"] = f"Gemini API error: {e}"
    else:
        gemini_result["feedback"] = "No Gemini API key provided; used fallback scoring."

    local = final_local(resume_text, jd_text)
    gemini = gemini_result.get("match_score") or 0
    boost, matched_keywords = keyword_boost_dynamic(resume_text, jd_text)
    final_match = round(0.4 * local + 0.4 * gemini + 0.2 * boost, 2)

    return {
        "final_score": final_match,
        "local_score": local,
        "gemini_score": gemini,
        "keyword_boost": boost,
        "matched_keywords": matched_keywords,
        "missing_skills": gemini_result.get("missing_skills", []),
        "feedback": gemini_result.get("feedback", "")
    }
