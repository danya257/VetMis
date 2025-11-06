from django.urls import path
from .views_clinic import ClinicDashboardView, clinic_switch

urlpatterns = [
    path("clinic/dashboard/", ClinicDashboardView.as_view(), name="clinic_dashboard"),
    path("clinic/switch/", clinic_switch, name="clinic_switch"),
]