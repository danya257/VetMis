from django.urls import path
from .views_cal import cal_webhook

urlpatterns = [
    path("integrations/cal/webhook/", cal_webhook, name="cal_webhook"),
]