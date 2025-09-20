import io, pdfplumber
from docx import Document
import ffmpeg, wave, os, json, requests

# Vosk speech recognition
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False

VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "models/vosk-model-small-en-us-0.15")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDHYLmJVPAPV9hj722jgSWgsEMg3EqU1R0")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# ---------------- Resume / Document extraction ----------------

def extract_text(file_field):
    """
    Extracts plain text from uploaded PDF or DOCX resume files.
    """
    file_field.open()
    content = file_field.read()
    name = file_field.name.lower()
    bio = io.BytesIO(content)

    if name.endswith(".pdf"):
        with pdfplumber.open(bio) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    elif name.endswith(".docx"):
        doc = Document(bio)
        return "\n".join([p.text for p in doc.paragraphs])
    
    # fallback for txt or other files
    return content.decode("utf8", errors="ignore")

# ---------------- Video transcription ----------------

def transcribe_video(file_path):
    """
    Transcribes speech from a video file to text using Vosk.
    """
    if not VOSK_AVAILABLE or not os.path.exists(VOSK_MODEL_PATH):
        return ""

    # Convert video to WAV
    wav_path = file_path + ".wav"
    (
        ffmpeg
        .input(file_path)
        .output(wav_path, ac=1, ar=16000, format="wav")
        .overwrite_output()
        .run(quiet=True)
    )

    wf = wave.open(wav_path, "rb")
    rec = KaldiRecognizer(Model(VOSK_MODEL_PATH), wf.getframerate())
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

    return " ".join(text_chunks)

# ---------------- Gemini API Integration ----------------

def analyze_resume_with_gemini(jd_text, resume_text):
    import requests, json

def analyze_resume_with_gemini(jd_text, resume_text, api_key):
    """
    Analyze a resume vs JD using Gemini 2.0 Flash REST API.
    Returns a dict with match_score, missing_skills, feedback.
    """
    try:
        prompt_text = f"""
Analyze this resume against the job description.

Job Description:
{jd_text}

Resume:
{resume_text}

Summarize:
- match_score (0-100)
- missing_skills (skills in JD missing from resume)
- feedback (improvements)
Respond in plain text that can be parsed as JSON.
"""

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateMessage?key=AIzaSyDaiMvswMhiX-DKHbTNN4iZnKO-ZgXz8WI"

        payload = {
            "messages": [
                {"author": "user", "content": [{"type": "text", "text": prompt_text}]}
            ]
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract model output
        text_output = data.get("candidates", [{}])[0].get("content", [{}])[0].get("text", "")

        # Attempt to parse as JSON
        try:
            result = json.loads(text_output)
        except:
            # Fallback: return plain text as feedback
            result = {"match_score": None, "missing_skills": [], "feedback": text_output}

        return result

    except Exception as e:
        return {"match_score": 0, "missing_skills": [], "feedback": f"Gemini API error: {e}"}



