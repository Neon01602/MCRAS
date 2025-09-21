from rest_framework import serializers
from .models import JobDescription, Candidate

class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = "__all__"

from rest_framework import serializers
from .models import Candidate

class CandidateSerializer(serializers.ModelSerializer):
    # Add read-only fields for scoring/analysis
    final_score = serializers.FloatField(read_only=True)
    local_score = serializers.FloatField(read_only=True)
    gemini_score = serializers.FloatField(read_only=True)
    keyword_boost = serializers.FloatField(read_only=True)
    matched_keywords = serializers.ListField(read_only=True)

    # Add job title read-only field
    applied_to_title = serializers.CharField(source='applied_to.title', read_only=True)

    class Meta:
        model = Candidate
        fields = "__all__"
        read_only_fields = (
            "parsed_text",
            "score",
            "verdict",
            "missing_skills",
            "feedback",
            "final_score",
            "local_score",
            "gemini_score",
            "keyword_boost",
            "matched_keywords",
            "applied_to_title",  # include new field in read-only
        )
