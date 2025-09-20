from rest_framework import serializers
from .models import JobDescription, Candidate

class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = "__all__"

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = "__all__"
        read_only_fields = ["parsed_text", "score", "verdict", "missing_skills", "feedback"]
