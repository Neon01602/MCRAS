from rest_framework import generics
from .models import JobDescription, Candidate
from .serializers import JobDescriptionSerializer, CandidateSerializer
from .utils import extract_text, transcribe_video
from .scoring import tokenize_skills, hard_skill_score, semantic_score, final_score, verdict
# screening/frontend_views.py
from django.shortcuts import render

def home(request):
    return render(request, "home.html")

def job_create_page(request):
    return render(request, "job_create.html")

def candidate_create_page(request):
    return render(request, "candidate_create.html")

def dashboard_page(request):
    return render(request, "dashboard.html")


class JobCreateView(generics.CreateAPIView):
    queryset = JobDescription.objects.all()
    serializer_class = JobDescriptionSerializer
    def perform_create(self, serializer):
        jd_text = serializer.validated_data.get("raw_text", "")
        serializer.save(parsed_keywords=tokenize_skills(jd_text))

class JobListView(generics.ListAPIView):
    queryset = JobDescription.objects.all()
    serializer_class = JobDescriptionSerializer

from .utils import analyze_resume_with_gemini

class CandidateCreateView(generics.CreateAPIView):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

    def perform_create(self, serializer):
        candidate = serializer.save()

        # Extract resume text
        resume_text = extract_text(candidate.resume)

        # Optional: transcribe video
        if candidate.video:
            video_text = transcribe_video(candidate.video.path)
            resume_text += "\n" + video_text

        # Analyze with Gemini
        jd = candidate.applied_to
        analysis = analyze_resume_with_gemini(jd.raw_text, resume_text)

        # Save results
        candidate.score = analysis.get("match_score", 0)
        candidate.missing_skills = analysis.get("missing_skills", [])
        candidate.feedback = analysis.get("feedback", "")
        candidate.save()



class CandidateListView(generics.ListAPIView):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

class CandidateDetailView(generics.RetrieveAPIView):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
