from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, date, time
from typing import Optional, Tuple, List

import pytz
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from main.models import (
    Clinic,
    VetProfile,
    VetAvailability,
    Appointment,
    AppointmentStatus,
    ClinicService,
)


class BookingError(Exception):
    pass


@dataclass(frozen=True)
class BookingInput:
    clinic_id: int
    vet_id: int
    service_id: Optional[int]  # Можно сделать обязательным, если требуется
    start_at: datetime          # naive или aware; будет приведено к TZ клиники
    end_at: datetime            # naive или aware
    booker_id: Optional[int]    # пользователь, если авторизован
    animal_id: Optional[int]    # питомец, если есть
    timezone_name: Optional[str] = None  # если передали, будет проверено с TZ клиники


def _to_clinic_tz(dt: datetime, tzname: str) -> datetime:
    tz = pytz.timezone(tzname)
    if timezone.is_naive(dt):
        return tz.localize(dt)
    else:
        return dt.astimezone(tz)


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def _slot_fits_availability(day: date, start_t: time, end_t: time, start_at: datetime, end_at: datetime) -> bool:
    return (start_at.time() >= start_t) and (end_at.time() <= end_t) and (start_at.date() == day == end_at.date())


def _is_multiple_of(duration: timedelta, slot_minutes: int) -> bool:
    return (duration.total_seconds() / 60) % slot_minutes == 0


@transaction.atomic
def create_local_appointment(data: BookingInput) -> Appointment:
    """
    Создает локальную запись без внешних сервисов.
    Правила:
      - Клиника и врач должны существовать и быть связаны.
      - Слот должен попадать в активные окна VetAvailability.
      - Слот не должен пересекаться с уже существующими Appointment (SCHEDULED/RESCHEDULED).
      - При наличии service_id — услуга должна быть активной в этой клинике.
      - Если clinic.is_demo=True — просто создаем запись (тоже с валидацией).
    Возвращает созданный объект Appointment.
    """
    clinic = Clinic.objects.select_for_update().get(id=data.clinic_id)
    vet = VetProfile.objects.select_for_update().get(id=data.vet_id, clinic=clinic)

    # TZ проверка/приведение
    tzname = clinic.timezone or "Europe/Moscow"
    if data.timezone_name and data.timezone_name != tzname:
        # Не крэшить, но нормализовать в TZ клиники
        pass

    start_local = _to_clinic_tz(data.start_at, tzname)
    end_local = _to_clinic_tz(data.end_at, tzname)
    if end_local <= start_local:
        raise BookingError("Окончание должно быть позже начала")

    # Проверка услуги
    svc_obj: Optional[ClinicService] = None
    if data.service_id:
        try:
            svc_obj = ClinicService.objects.select_related("service").get(
                clinic=clinic, service_id=data.service_id, is_active=True
            )
        except ClinicService.DoesNotExist:
            raise BookingError("Услуга недоступна в выбранной клинике")

    # Найти подходящее окно доступности на дату
    day = start_local.date()
    avails = list(
        VetAvailability.objects.filter(
            clinic=clinic,
            vet=vet,
            is_active=True
        ).filter(
            Q(date=day) |
            Q(date__isnull=True, weekday=day.weekday())
        )
    )
    if not avails:
        raise BookingError("На эту дату врач не принимает")

    duration = end_local - start_local
    fits_any = False
    slot_step_ok = True
    for a in avails:
        if a.start_time and a.end_time and _slot_fits_availability(day, a.start_time, a.end_time, start_local, end_local):
            fits_any = True
            if a.slot_minutes and not _is_multiple_of(duration, a.slot_minutes):
                slot_step_ok = False
                break
    if not fits_any:
        raise BookingError("Выбранное время вне графика врача")
    if not slot_step_ok:
        raise BookingError("Длительность слота должна быть кратна шагу расписания врача")

    # Проверка пересечений с занятыми визитами
    busy_qs = Appointment.objects.select_for_update().filter(
        clinic=clinic,
        vet=vet,
        status__in=[AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED],
        start_at__date=day
    ).only("id", "start_at", "end_at")

    for ap in busy_qs:
        if _overlaps(start_local, end_local, ap.start_at, ap.end_at):
            raise BookingError("Слот уже занят")

    # Создаем запись
    appt = Appointment.objects.create(
        clinic=clinic,
        vet=vet,
        animal_id=data.animal_id,
        booker_id=data.booker_id,
        event_type=None,  # поле можно удалить из модели; оставлено на случай миграции поэтапно
        start_at=start_local.astimezone(timezone.utc),
        end_at=end_local.astimezone(timezone.utc),
        timezone=tzname,
        status=AppointmentStatus.SCHEDULED,
        notes=f"Заявка через API; {'демо' if clinic.is_demo else 'боевой'} режим",
        payload={
            "source": "local_api",
            "clinic_is_demo": clinic.is_demo,
            "service_id": data.service_id,
        }
    )
    return appt