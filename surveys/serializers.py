from rest_framework import serializers

from .models import SurveyQuestion, SurveyAttempt


class SurveyQuestionPublicSerializer(serializers.ModelSerializer):
    """Deliberately excludes correct_option — never sent to the frontend before submission."""

    class Meta:
        model = SurveyQuestion
        fields = ["id", "text", "options"]


class SurveyAttemptResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyAttempt
        fields = ["id", "date", "score", "credited_amount", "currency_code", "submitted_at"]