from django.urls import path

from .views import MyReferralCommissionsView, MyReferralSummaryView, MyReferredUsersView

urlpatterns = [
    path("commissions/", MyReferralCommissionsView.as_view(), name="my-referral-commissions"),
    path("summary/", MyReferralSummaryView.as_view(), name="my-referral-summary"),
    path("referred-users/", MyReferredUsersView.as_view(), name="my-referred-users"),
]