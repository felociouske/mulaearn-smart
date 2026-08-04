from django.urls import path

from .views import PlanListView, PurchasePlanView, MyActivePlansView

urlpatterns = [
    path("", PlanListView.as_view(), name="plan-list"),
    path("me/", MyActivePlansView.as_view(), name="my-active-plans"),
    path("<int:plan_id>/purchase/", PurchasePlanView.as_view(), name="purchase-plan"),
]