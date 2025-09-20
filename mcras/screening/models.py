from django.db import models

class JobDescription(models.Model):
    title = models.CharField(max_length=255)
    raw_text = models.TextField()
    parsed_keywords = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Candidate(models.Model):
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    resume = models.FileField(upload_to="resumes/")
    video = models.FileField(upload_to="videos/", null=True, blank=True)
    applied_to = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name="candidates")
    parsed_text = models.TextField(blank=True)
    score = models.FloatField(null=True, blank=True)
    verdict = models.CharField(max_length=20, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
