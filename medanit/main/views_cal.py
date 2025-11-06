from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from django.utils.dateparse import parse_datetime
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from main.models import Appointment
from main.services.booking import BookingInput, create_local_appointment, BookingError


class CreateAppointmentSerializer(serializers.Serializer):
    clinic_id = serializers.IntegerField()
    vet_id = serializers.IntegerField()
    service_id = serializers.IntegerField(required=False, allow_null=True)
    start_at = serializers.CharField()  # ISO 8601 строка от клиента
    end_at = serializers.CharField()
    animal_id = serializers.IntegerField(required=False, allow_null=True)
    booker_id = serializers.IntegerField(required=False, allow_null=True)
    timezone = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        start_at_raw = attrs.get("start_at")
        end_at_raw = attrs.get("end_at")
        start_dt: Optional[datetime] = parse_datetime(start_at_raw) if isinstance(start_at_raw, str) else start_at_raw
        end_dt: Optional[datetime] = parse_datetime(end_at_raw) if isinstance(end_at_raw, str) else end_at_raw

        if not start_dt or not end_dt:
            raise serializers.ValidationError("Поля start_at и end_at должны быть ISO-датами/временем")

        attrs["start_dt"] = start_dt
        attrs["end_dt"] = end_dt
        return attrs


class AppointmentCreateView(APIView):
    """
    Публичная точка создания записи без внешних сервисов.
    Для демо-клиник запись создается сразу.
    Для рабочих клиник — тоже создается локально (никаких Cal).
    """
    permission_classes = [AllowAny]  # при необходимости заменить на IsAuthenticated или кастом

    def post(self, request, *args, **kwargs):
        serializer = CreateAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking_input = BookingInput(
            clinic_id=data["clinic_id"],
            vet_id=data["vet_id"],
            service_id=data.get("service_id"),
            start_at=data["start_dt"],
            end_at=data["end_dt"],
            animal_id=data.get("animal_id"),
            booker_id=data.get("booker_id"),
            timezone_name=data.get("timezone") or None,
        )

        try:
            appt: Appointment = create_local_appointment(booking_input)
        except BookingError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "id": appt.id,
            "clinic_id": appt.clinic_id,
            "vet_id": appt.vet_id,
            "animal_id": appt.animal_id,
            "start_at": appt.start_at,  # UTC в БД
            "end_at": appt.end_at,
            "status": appt.status,
            "timezone": appt.timezone,
        }, status=status.HTTP_201_CREATED)