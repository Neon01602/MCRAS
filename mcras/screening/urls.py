from django.urls import path
from .views import JobCreateView, JobListView, CandidateCreateView, CandidateListView, CandidateDetailView

urlpatterns = [
    path("jobs/", JobListView.as_view()),
    path("jobs/create/", JobCreateView.as_view()),
    path("candidates/create/", CandidateCreateView.as_view()),
    path("candidates/", CandidateListView.as_view()),
    path("candidates/<int:pk>/", CandidateDetailView.as_view()),
]

from .views import home, job_create_page, candidate_create_page, dashboard_page

urlpatterns += [
    path("", home, name="home"),
    path("ui/jobs/create/", job_create_page, name="ui-job-create"),
    path("ui/candidates/create/", candidate_create_page, name="ui-candidate-create"),
    path("ui/dashboard/", dashboard_page, name="ui-dashboard"),
]

