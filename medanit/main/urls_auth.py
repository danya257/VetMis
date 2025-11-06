from django.urls import path
from .views_auth import CustomLoginView

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
   # path("clinic/dashboard/", clinic_dashboard, name="clinic_dashboard"),
]