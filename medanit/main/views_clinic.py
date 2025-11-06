from datetime import timedelta
from typing import Optional, Dict, Any, List, Tuple

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from .models import Clinic, Appointment, AppointmentStatus

SESSION_CLINIC_KEY = "current_clinic_id"


def _get_user_clinics(user) -> List[Clinic]:
    # Владелец кабинета: Clinic.owner = user
    return list(Clinic.objects.filter(owner=user).order_by("name"))


def _get_current_clinic(request: HttpRequest) -> Optional[Clinic]:
    clinic_id = request.session.get(SESSION_CLINIC_KEY)
    if clinic_id:
        clinic = Clinic.objects.filter(id=clinic_id).first()
        # Защитимся на случай, если клиника не принадлежит пользователю
        if clinic and clinic.owner_id == request.user.id:
            return clinic
        # Сбросим некорректный clinic_id
        request.session.pop(SESSION_CLINIC_KEY, None)

    clinics = _get_user_clinics(request.user)
    if clinics:
        request.session[SESSION_CLINIC_KEY] = clinics[0].id
        return clinics[0]
    return None


@login_required
def clinic_switch(request: HttpRequest) -> HttpResponse:
    """Смена текущей клиники в сессии."""
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")
    clinic_id = request.POST.get("clinic_id")
    if not clinic_id:
        return HttpResponseBadRequest("clinic_id required")

    # Разрешаем выбирать только среди своих клиник
    if not Clinic.objects.filter(id=clinic_id, owner=request.user).exists():
        return HttpResponseBadRequest("clinic not allowed")

    request.session[SESSION_CLINIC_KEY] = int(clinic_id)
    return redirect(request.POST.get("next") or reverse("clinic_dashboard"))


def _period_bounds(preset: str) -> Tuple[timezone.datetime, timezone.datetime]:
    now = timezone.now()
    preset = (preset or "").lower()
    if preset in ("7d", "7"):
        start = now - timedelta(days=7)
    elif preset in ("90d", "90"):
        start = now - timedelta(days=90)
    elif preset in ("all", "∞", "inf"):
        # ограничим "всё время" условным годом 2000, чтобы избегать проблем с MINYEAR
        start = now.replace(year=max(2000, now.year - 25))
    else:
        # дефолт 30 дней
        start = now - timedelta(days=30)
    return start, now


def _compute_metrics(clinic: Clinic, period: str) -> Dict[str, Any]:
    start, now = _period_bounds(period)
    today = timezone.localdate()

    base_qs = Appointment.objects.filter(clinic=clinic)
    period_qs = base_qs.filter(start_at__gte=start, start_at__lte=now)

    total = period_qs.count()
    upcoming = base_qs.filter(status=AppointmentStatus.SCHEDULED, start_at__gte=now).count()
    today_count = base_qs.filter(start_at__date=today).count()
    cancelled = period_qs.filter(status=AppointmentStatus.CANCELLED).count()
    completed = period_qs.filter(status=AppointmentStatus.COMPLETED).count()
    rescheduled = period_qs.filter(status=AppointmentStatus.RESCHEDULED).count()

    # По дням за период
    by_day_qs = (
        period_qs.annotate(day=TruncDate("start_at"))
        .values("day")
        .annotate(c=Count("id"))
        .order_by("day")
    )
    by_day = [{"day": item["day"].strftime("%Y-%m-%d"), "count": item["c"]} for item in by_day_qs if item["day"]]

    # Топ типов событий
    top_event_types = (
        period_qs.values("event_type__name")
        .annotate(c=Count("id"))
        .order_by("-c")[:5]
    )

    # Топ врачей
    top_vets = (
        period_qs.values("vet__full_name")
        .annotate(c=Count("id"))
        .order_by("-c")[:5]
    )

    # Последние записи
    recent_appts = (
        base_qs.select_related("animal", "booker", "vet", "event_type")
        .order_by("-start_at")[:10]
    )

    # Ближайшие записи (на 7 дней вперед)
    next_7_days = now + timedelta(days=7)
    upcoming_list = (
        base_qs.select_related("animal", "booker", "vet", "event_type")
        .filter(status=AppointmentStatus.SCHEDULED, start_at__gte=now, start_at__lte=next_7_days)
        .order_by("start_at")[:10]
    )

    return {
        "period": period,
        "total": total,
        "upcoming": upcoming,
        "today": today_count,
        "cancelled": cancelled,
        "completed": completed,
        "rescheduled": rescheduled,
        "by_day": by_day,
        "top_event_types": list(top_event_types),
        "top_vets": list(top_vets),
        "recent_appts": recent_appts,
        "upcoming_list": upcoming_list,
        "start_at": start,
        "end_at": now,
    }


class ClinicDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "clinic/dashboard.html"

    def get(self, request: HttpRequest, *args, **kwargs):
        clinics = _get_user_clinics(request.user)
        current = _get_current_clinic(request)

        # Если у пользователя нет клиник — покажем заглушку
        if not clinics or not current:
            return render(request, self.template_name, {
                "clinics": clinics,
                "current_clinic": None,
                "metrics": None,
                "no_clinics": True,
            })

        period = request.GET.get("period") or "30d"
        metrics = _compute_metrics(current, period)

        return render(request, self.template_name, {
            "clinics": clinics,
            "current_clinic": current,
            "metrics": metrics,
        })