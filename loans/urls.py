from django.urls import path

from .views import (
    LoanPlanListView,
    MyLoanApplicationsView,
    MyLoanEligibilityView,
    PurchaseLoanPlanView,
    SubmitLoanApplicationView,
)

urlpatterns = [
    path("plans/", LoanPlanListView.as_view(), name="loan-plan-list"),
    path("plans/<int:plan_id>/purchase/", PurchaseLoanPlanView.as_view(), name="purchase-loan-plan"),
    path("eligibility/", MyLoanEligibilityView.as_view(), name="my-loan-eligibility"),
    path("apply/", SubmitLoanApplicationView.as_view(), name="submit-loan-application"),
    path("applications/", MyLoanApplicationsView.as_view(), name="my-loan-applications"),
]