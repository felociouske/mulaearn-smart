from django.urls import path

from .views import SubmitSurveyView, SurveyHistoryView, TodaysSurveyView

urlpatterns = [
    path("today/", TodaysSurveyView.as_view(), name="survey-today"),
    path("submit/", SubmitSurveyView.as_view(), name="survey-submit"),
    path("history/", SurveyHistoryView.as_view(), name="survey-history"),
]