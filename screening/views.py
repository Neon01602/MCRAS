# views.py
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.db import transaction
import logging

from .models import JobDescription, Candidate
from .serializers import JobDescriptionSerializer, CandidateSerializer
from .utils import extract_text, transcribe_video, analyze_resume_with_gemini
from .scoring import tokenize_skills, hard_skill_score, semantic_score, final_score, verdict as score_verdict

logger = logging.getLogger(__name__)

# frontend views
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
        # Get data
        jd_text = serializer.validated_data.get("raw_text", "")
        title = serializer.validated_data.get("title", "").strip() or "Untitled Job"

        # Parse keywords
        parsed = tokenize_skills(jd_text)

        # Save JobDescription
        serializer.save(title=title, raw_text=jd_text, parsed_keywords=parsed)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from .models import JobDescription
from .serializers import JobDescriptionSerializer
import PyPDF2

class UploadPDFJobView(APIView):
    def post(self, request, *args, **kwargs):
        pdf_file = request.FILES.get('pdf')
        if not pdf_file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Save temporarily
            file_path = default_storage.save('tmp/' + pdf_file.name, pdf_file)
            with default_storage.open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"

            # Extract title as first line, rest as description
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            title = lines[0][:255] if lines else "Untitled Job"
            raw_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else text

            # Use the same serializer to save and parse keywords
            serializer = JobDescriptionSerializer(data={"title": title, "raw_text": raw_text})
            serializer.is_valid(raise_exception=True)
            serializer.save(parsed_keywords=tokenize_skills(raw_text))

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class JobListView(generics.ListAPIView):
    queryset = JobDescription.objects.all().order_by("-created_at")
    serializer_class = JobDescriptionSerializer


from rest_framework import generics, status
from rest_framework.response import Response
from django.db import transaction
from .models import Candidate
from .serializers import CandidateSerializer
from .utils import extract_text, transcribe_video, analyze_resume_with_gemini
from .scoring import verdict as score_verdict
import logging

logger = logging.getLogger(__name__)

class CandidateCreateView(generics.CreateAPIView):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        email = serializer.validated_data.get('email').strip().lower()
        applied_to = serializer.validated_data.get('applied_to')

        # Check if candidate already exists for this job
        candidate = Candidate.objects.filter(email=email, applied_to=applied_to).first()
        if candidate:
            # Update existing candidate with new data
            for field, value in serializer.validated_data.items():
                setattr(candidate, field, value)
            created = False
        else:
            candidate = serializer.save()
            created = True

        # 1) Extract resume text
        resume_text = extract_text(candidate.resume) or ""
        candidate.parsed_text = resume_text

        # 2) Transcribe video if present
        if candidate.video and getattr(candidate.video, "path", None):
            try:
                video_text = transcribe_video(candidate.video.path) or ""
                resume_text += "\n" + video_text
            except Exception as e:
                logger.exception("Video transcription failed: %s", e)

        # 3) Analyze resume vs JD
        analysis = analyze_resume_with_gemini(candidate.applied_to.raw_text, resume_text)

        # 4) Save all scoring components
        candidate.final_score = analysis.get("final_score")
        candidate.local_score = analysis.get("local_score")
        candidate.gemini_score = analysis.get("gemini_score")
        candidate.keyword_boost = analysis.get("keyword_boost")
        candidate.matched_keywords = analysis.get("matched_keywords", [])
        candidate.missing_skills = analysis.get("missing_skills", [])
        candidate.feedback = analysis.get("feedback", "")

        # 5) Use final_score as main score for verdict
        candidate.score = candidate.final_score
        candidate.verdict = score_verdict(candidate.score)

        candidate.save()

        self.instance = candidate
        self.created = created


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        response_data = serializer.data
        response_data['status'] = 'created' if self.created else 'updated'
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)

class JobDetailView(generics.RetrieveAPIView):
    queryset = JobDescription.objects.all()
    serializer_class = JobDescriptionSerializer




class CandidateListView(generics.ListAPIView):
    queryset = Candidate.objects.all().order_by("-created_at")
    serializer_class = CandidateSerializer


class CandidateDetailView(generics.RetrieveAPIView):
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer

from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def job_list(request):
    jobs = JobDescription.objects.all()
    data = [{"id": job.id, "title": job.title, "raw_text": job.raw_text} for job in jobs]
    return Response(data)

class JobDetailAPIView(generics.RetrieveAPIView):
    queryset = JobDescription.objects.all()
    serializer_class = JobDescriptionSerializer
