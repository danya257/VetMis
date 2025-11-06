from datetime import datetime, timedelta, time, date
from typing import List, Tuple, Dict, Optional

import pytz
from django.db.models import Q

from main.models import Clinic, VetProfile, VetAvailability, Appointment, AppointmentStatus, Weekday


def daterange(start_date: date, end_date: date):
    cur = start_date
    while cur <= end_date:
        yield cur
        cur += timedelta(days=1)


def build_time_slots(day: date, start_t: time, end_t: time, slot_minutes: int, tzinfo) -> List[Tuple[datetime, datetime]]:
    start_dt = tzinfo.localize(datetime.combine(day, start_t))
    end_dt = tzinfo.localize(datetime.combine(day, end_t))
    slots = []
    cur = start_dt
    delta = timedelta(minutes=slot_minutes)
    while cur + delta <= end_dt:
        slots.append((cur, cur + delta))
        cur += delta
    return slots


def subtract_busy(slots: List[Tuple[datetime, datetime]], busy: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    """
    Убираем из слотов те, что пересекаются с занятыми интервалами.
    Считаем, что пересечение по времени делает слот недоступным.
    """
    if not busy:
        return slots
    result = []
    for s_start, s_end in slots:
        overlapped = False
        for b_start, b_end in busy:
            if max(s_start, b_start) < min(s_end, b_end):
                overlapped = True
                break
        if not overlapped:
            result.append((s_start, s_end))
    return result


def get_free_slots_for_vet(
    clinic: Clinic,
    vet: VetProfile,
    start_date: date,
    end_date: date,
    only_days: bool = False
) -> Dict[date, List[Tuple[datetime, datetime]]]:
    """
    Возвращает словарь: {дата: [списки свободных слотов (start_dt, end_dt) в TZ клиники]}.
    Если only_days=True — вернёт только дни, где есть хотя бы 1 свободный слот (значения — пустые списки).
    """
    tz = pytz.timezone(clinic.timezone or "Europe/Moscow")

    # Загружаем активные окна доступности врача.
    avails = VetAvailability.objects.filter(
        clinic=clinic,
        vet=vet,
        is_active=True
    )

    # Предзагружаем занятые интервалы по Appointment (только активные статусы).
    busy_qs = Appointment.objects.filter(
        clinic=clinic,
        vet=vet,
        status__in=[AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED],
        start_at__date__lte=end_date,
        end_at__date__gte=start_date,
    ).values_list("start_at", "end_at")

    busy = list(busy_qs)

    result: Dict[date, List[Tuple[datetime, datetime]]] = {}

    for day in daterange(start_date, end_date):
        day_wd = day.weekday()  # 0-6
        day_slots: List[Tuple[datetime, datetime]] = []

        # Окна повторяющиеся по дню недели
        for a in avails.filter(weekday=day_wd, date__isnull=True):
            if a.start_time and a.end_time:
                day_slots.extend(build_time_slots(day, a.start_time, a.end_time, a.slot_minutes, tz))

        # Окна конкретной датой
        for a in avails.filter(date=day):
            if a.start_time and a.end_time:
                day_slots.extend(build_time_slots(day, a.start_time, a.end_time, a.slot_minutes, tz))

        if not day_slots:
            continue

        # Переводим busy интервалы в TZ клиники (если они naive/UTC)
        busy_local: List[Tuple[datetime, datetime]] = []
        for b_start, b_end in busy:
            # Django хранит в UTC; .astimezone в TZ клиники
            busy_local.append((b_start.astimezone(tz), b_end.astimezone(tz)))

        free = subtract_busy(day_slots, busy_local)

        if free or not only_days:
            result[day] = free if not only_days else []

    return result