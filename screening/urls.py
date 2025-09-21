# urls.py
from django.urls import path

from .views import (
    JobCreateView, JobListView,
    CandidateCreateView, CandidateListView, CandidateDetailView, UploadPDFJobView, JobDetailAPIView,
    home, job_create_page, candidate_create_page, dashboard_page, job_list
)

api_patterns = [
    path('jobs/list/', job_list, name='job-list'),
    path("jobs/", JobListView.as_view(), name="api-jobs-list"),
    path("jobs/create/", JobCreateView.as_view(), name="api-jobs-create"),
    path("candidates/create/", CandidateCreateView.as_view(), name="api-candidates-create"),
    path("candidates/", CandidateListView.as_view(), name="api-candidates-list"),
    path("candidates/<int:pk>/", CandidateDetailView.as_view(), name="api-candidate-detail"),
    path('jobs/create/', JobCreateView.as_view(), name='job_create'),
    path('jobs/upload_pdf/', UploadPDFJobView.as_view(), name='upload_pdf_job'),
    path('jobs/<int:pk>/', JobDetailAPIView.as_view(), name='api-jobs-detail'),
]

ui_patterns = [
    path("", home, name="home"),
    
    path("ui/jobs/create/", job_create_page, name="ui-job-create"),
    path("ui/candidates/create/", candidate_create_page, name="ui-candidate-create"),
    path("ui/dashboard/", dashboard_page, name="ui-dashboard"),
]

urlpatterns = api_patterns + ui_patterns
