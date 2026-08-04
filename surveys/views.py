import random
from datetime import date

from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsActivated
from wallets.models import Transaction

from .models import (
    QUESTIONS_PER_ATTEMPT,
    SurveyAttempt,
    SurveyQuestion,
    payout_for_score,
    today_is_survey_day,
)
from .serializers import SurveyAttemptResultSerializer, SurveyQuestionPublicSerializer


class TodaysSurveyView(APIView):
    """
    GET /api/surveys/today/

    - If today isn't Mon/Wed/Fri: {"available": false, "reason": "..."}
    - If the user already submitted today: returns their result.
    - If they've opened it but not submitted (e.g. page refresh): returns
      the same 10 questions again rather than drawing a new set.
    - Otherwise: draws 10 random active questions from the pool, stores
      the attempt shell, and returns them WITHOUT correct_option.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def get(self, request):
        today = date.today()
        if not today_is_survey_day(today):
            return Response({"available": False, "reason": "Surveys run Monday, Wednesday and Friday only."})

        existing = SurveyAttempt.objects.filter(user=request.user, date=today).first()

        if existing and existing.submitted_at:
            return Response({
                "available": False,
                "reason": "You've already completed today's survey.",
                "result": SurveyAttemptResultSerializer(existing).data,
            })

        if existing:
            questions_by_id = SurveyQuestion.objects.in_bulk(existing.question_ids)
            ordered = [questions_by_id[qid] for qid in existing.question_ids if qid in questions_by_id]
            return Response({
                "available": True,
                "attempt_id": existing.id,
                "questions": SurveyQuestionPublicSerializer(ordered, many=True).data,
            })

        pool = list(SurveyQuestion.objects.filter(is_active=True).values_list("id", flat=True))
        if len(pool) < QUESTIONS_PER_ATTEMPT:
            return Response({"available": False, "reason": "Not enough survey questions configured yet."})

        selected_ids = random.sample(pool, QUESTIONS_PER_ATTEMPT)
        attempt = SurveyAttempt.objects.create(user=request.user, date=today, question_ids=selected_ids)

        questions_by_id = SurveyQuestion.objects.in_bulk(selected_ids)
        ordered = [questions_by_id[qid] for qid in selected_ids if qid in questions_by_id]

        return Response({
            "available": True,
            "attempt_id": attempt.id,
            "questions": SurveyQuestionPublicSerializer(ordered, many=True).data,
        })


class SubmitSurveyView(APIView):
    """
    POST /api/surveys/submit/  { "attempt_id": <id>, "answers": [0, 2, 1, ...] }
    Scores against SurveyQuestion.correct_option (never exposed to the
    client beforehand), credits the tiered KES payout converted to the
    user's local currency, and marks the attempt submitted.
    """
    permission_classes = [permissions.IsAuthenticated, IsActivated]

    def post(self, request):
        attempt_id = request.data.get("attempt_id")
        answers = request.data.get("answers")

        if not isinstance(answers, list):
            raise DRFValidationError({"answers": ["This field is required and must be a list."]})

        attempt = SurveyAttempt.objects.filter(id=attempt_id, user=request.user).first()
        if not attempt:
            raise DRFValidationError({"attempt_id": ["Attempt not found."]})
        if attempt.submitted_at:
            raise DRFValidationError({"attempt_id": ["This attempt was already submitted."]})
        if len(answers) != len(attempt.question_ids):
            raise DRFValidationError({"answers": [f"Expected {len(attempt.question_ids)} answers."]})

        questions_by_id = SurveyQuestion.objects.in_bulk(attempt.question_ids)
        score = 0
        for qid, given_answer in zip(attempt.question_ids, answers):
            question = questions_by_id.get(qid)
            if question is not None and given_answer == question.correct_option:
                score += 1

        payout_kes = payout_for_score(score)
        country = request.user.country
        credited_amount = country.convert_from_kes(payout_kes) if country else payout_kes
        currency_code = country.currency_code if country else "KES"

        with db_transaction.atomic():
            attempt.answers = answers
            attempt.score = score
            attempt.credited_amount = credited_amount
            attempt.currency_code = currency_code
            attempt.submitted_at = timezone.now()
            attempt.save()

            if credited_amount > 0:
                request.user.wallet.credit(
                    "account",
                    credited_amount,
                    Transaction.TransactionType.SURVEY_EARNING,
                    description=f"Survey {attempt.date}: {score}/{len(attempt.question_ids)} correct",
                )

        return Response(SurveyAttemptResultSerializer(attempt).data, status=status.HTTP_201_CREATED)


class SurveyHistoryView(generics.ListAPIView):
    serializer_class = SurveyAttemptResultSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SurveyAttempt.objects.filter(user=self.request.user, submitted_at__isnull=False)