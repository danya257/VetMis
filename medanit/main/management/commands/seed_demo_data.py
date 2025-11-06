import random
from datetime import datetime, timedelta, time, date

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify
from django.db import transaction

from main.models import (
    Clinic, VetProfile, Service, ClinicService, Animal, Appointment, AnimalService,
    VetAvailability, Weekday, AppointmentStatus, Currency
)

User = get_user_model()


class Command(BaseCommand):
    help = "Load demo data: creates 5 demo clinics with vets, services, clinic services, animals, appointments, and availabilities."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Re-create demo data (deletes existing demo clinics)")
        parser.add_argument("--tz", default="Europe/Moscow", help="Default timezone for demo clinics")

    @transaction.atomic
    def handle(self, *args, **options):
        tzname = options["tz"]
        force = options["force"]

        if force:
            self.stdout.write(self.style.WARNING("Deleting existing demo clinics and related data..."))
            clinics = Clinic.objects.filter(is_demo=True)
            # Delete related through cascading
            AnimalService.objects.filter(clinic__in=clinics).delete()
            Appointment.objects.filter(clinic__in=clinics).delete()
            VetAvailability.objects.filter(clinic__in=clinics).delete()
            VetProfile.objects.filter(clinic__in=clinics).delete()
            ClinicService.objects.filter(clinic__in=clinics).delete()
            clinics.delete()

        # Ensure some demo users exist (owners, vets link, animal owners)
        owner_users = self._ensure_users(prefix="demo_owner", count=5)
        vet_users = self._ensure_users(prefix="demo_vet", count=10)
        pet_owners = self._ensure_users(prefix="demo_client", count=8)

        # Global service catalog (idempotent)
        services = self._ensure_global_services()

        clinics_data = [
            {
                "name": "ВетКлиника Здоровье",
                "description": "Полный спектр ветеринарных услуг: терапия, хирургия, стоматология.",
                "address": "Москва, ул. Пушкина, д. 10",
                "phone": "+7 (495) 000-10-10",
                "email": "info@zdorovie-vet.ru",
                "website": "https://zdorovie-vet.ru",
            },
            {
                "name": "Добрый Хвост",
                "description": "Клиника дружественная животным. Профилактика и вакцинация.",
                "address": "Санкт-Петербург, Невский пр., д. 120",
                "phone": "+7 (812) 111-22-33",
                "email": "hello@dobryhvost.ru",
                "website": "https://dobryhvost.ru",
            },
            {
                "name": "Айболит Премиум",
                "description": "Круглосуточная ветеринарная помощь премиум-класса.",
                "address": "Казань, ул. Баумана, д. 5",
                "phone": "+7 (843) 222-33-44",
                "email": "contact@aibolit-premium.ru",
                "website": "https://aibolit-premium.ru",
            },
            {
                "name": "Лапа+",
                "description": "Диагностика, рентген, УЗИ. Экстренные операции.",
                "address": "Екатеринбург, пр. Ленина, д. 25",
                "phone": "+7 (343) 555-66-77",
                "email": "admin@lapa-plus.ru",
                "website": "https://lapa-plus.ru",
            },
            {
                "name": "Зоодоктор",
                "description": "Ветеринарная клиника у дома. Выезд врача.",
                "address": "Новосибирск, Красный пр., д. 48",
                "phone": "+7 (383) 777-88-99",
                "email": "mail@zoodoctor.ru",
                "website": "https://zoodoctor.ru",
            },
        ]

        created_clinics = []

        self.stdout.write(self.style.NOTICE("Creating demo clinics..."))
        for i, cd in enumerate(clinics_data):
            owner = owner_users[i % len(owner_users)]
            clinic, created = Clinic.objects.get_or_create(
                slug=slugify(cd["name"]),
                defaults=dict(
                    name=cd["name"],
                    description=cd["description"],
                    address=cd["address"],
                    phone=cd["phone"],
                    email=cd["email"],
                    website=cd["website"],
                    timezone=tzname,
                    owner=owner,
                    is_demo=True,
                ),
            )
            if not created:
                # Update core fields if clinic exists but ensure is_demo
                clinic.description = cd["description"]
                clinic.address = cd["address"]
                clinic.phone = cd["phone"]
                clinic.email = cd["email"]
                clinic.website = cd["website"]
                clinic.timezone = tzname
                clinic.owner = owner
                clinic.is_demo = True
                clinic.save()
            created_clinics.append(clinic)
            self.stdout.write(f" - {clinic.name} ({'created' if created else 'updated'})")

        # Create vets per clinic
        self.stdout.write(self.style.NOTICE("Creating vet profiles and availabilities..."))
        vet_names = [
            ("Иванов Иван Иванович", "Терапевт"),
            ("Петров Петр Петрович", "Хирург"),
            ("Сидорова Анна Сергеевна", "Стоматолог"),
            ("Кузнецова Ольга Дмитриевна", "Офтальмолог"),
            ("Александров Дмитрий Игоревич", "Кардиолог"),
        ]
        all_vets = []
        for idx, clinic in enumerate(created_clinics):
            count = 2 + (idx % 2)  # 2 или 3 врача
            for j in range(count):
                full_name, spec = vet_names[(idx + j) % len(vet_names)]
                user = vet_users[(idx * 2 + j) % len(vet_users)]
                vp, _ = VetProfile.objects.get_or_create(
                    clinic=clinic,
                    full_name=full_name,
                    defaults=dict(
                        user=user,
                        specialties=spec,
                        bio=f"Опыт работы более {3 + ((idx + j) % 10)} лет. Специализация: {spec}.",
                        is_active=True,
                    ),
                )
                all_vets.append(vp)
                # Weekday availability: Mon-Fri 10:00-18:00, 30-min slots
                for wd in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY]:
                    VetAvailability.objects.get_or_create(
                        vet=vp,
                        clinic=clinic,
                        weekday=wd,
                        start_time=time(10, 0),
                        end_time=time(18, 0),
                        defaults=dict(slot_minutes=30, is_active=True),
                    )

                # One-off availability next Saturday 11:00-15:00
                next_sat = self._next_weekday(date.today(), Weekday.SATURDAY)
                VetAvailability.objects.get_or_create(
                    vet=vp,
                    clinic=clinic,
                    date=next_sat,
                    start_time=time(11, 0),
                    end_time=time(15, 0),
                    defaults=dict(slot_minutes=30, is_active=True),
                )

        # Attach clinic services (prices)
        self.stdout.write(self.style.NOTICE("Attaching clinic services with prices..."))
        for clinic in created_clinics:
            for order, service in enumerate(services, start=1):
                price = self._price_for_service(service.name)
                ClinicService.objects.update_or_create(
                    clinic=clinic,
                    service=service,
                    defaults=dict(
                        price=price,
                        currency=Currency.RUB,
                        is_active=True,
                        default_duration_minutes=self._duration_for_service(service.name),
                        sort_order=order,
                    ),
                )

        # Create animals and appointments
        self.stdout.write(self.style.NOTICE("Creating animals, appointments, and provided services..."))
        species_breeds = [
            ("собака", "Лабрадор"),
            ("кошка", "Британская короткошёрстная"),
            ("собака", "Корги"),
            ("кошка", "Сфинкс"),
            ("кролик", "Рекс"),
            ("морская свинка", "Альпака"),
        ]
        animals = []
        for i in range(12):
            owner = pet_owners[i % len(pet_owners)]
            name = random.choice(["Барсик", "Мурка", "Шарик", "Рыжик", "Лаки", "Тоша", "Граф", "Снежок", "Боня"])
            species, breed = species_breeds[i % len(species_breeds)]
            birthday = date.today() - timedelta(days=365 * random.randint(1, 12))
            a, _ = Animal.objects.get_or_create(
                name=f"{name} {i+1}",
                owner=owner,
                defaults=dict(
                    species=species,
                    breed=breed,
                    birthday=birthday,
                ),
            )
            animals.append(a)

        # Appointments in next 7 days for random vets/clinics/animals
        now = timezone.now()
        for i in range(20):
            clinic = random.choice(created_clinics)
            vets = list(VetProfile.objects.filter(clinic=clinic, is_active=True))
            if not vets:
                continue
            vet = random.choice(vets)
            animal = random.choice(animals)
            start = (now + timedelta(days=random.randint(0, 7))).replace(minute=0, second=0, microsecond=0) + timedelta(hours=random.choice([9, 10, 11, 12, 14, 15, 16]))
            end = start + timedelta(minutes=random.choice([30, 45, 60]))
            status = random.choice([AppointmentStatus.SCHEDULED, AppointmentStatus.COMPLETED, AppointmentStatus.RESCHEDULED])
            appt, _ = Appointment.objects.get_or_create(
                clinic=clinic,
                animal=animal,
                start_at=start,
                defaults=dict(
                    end_at=end,
                    timezone=clinic.timezone or tzname,
                    status=status,
                    booker=clinic.owner,
                    vet=vet,
                    notes="Демо запись.",
                ),
            )

            # For completed appointments, add provided service
            if appt.status == AppointmentStatus.COMPLETED:
                svc = random.choice(services)
                AnimalService.objects.get_or_create(
                    animal=animal,
                    service=svc,
                    date=appt.end_at,
                    created_by=clinic.owner or random.choice(vet_users),
                    defaults=dict(
                        performer=vet.user,
                        cost=self._price_for_service(svc.name),
                        service_description=svc.description,
                        clinic=clinic,
                        is_custom=False,
                    ),
                )

        self.stdout.write(self.style.SUCCESS("Demo data loaded successfully."))

    def _ensure_users(self, prefix: str, count: int):
        users = []
        for i in range(count):
            username = f"{prefix}{i+1}"
            email = f"{username}@example.com"
            user, created = User.objects.get_or_create(
                username=username,
                defaults=dict(
                    email=email,
                    is_active=True,
                ),
            )
            if created:
                # Set a default password
                user.set_password("demo12345")
                user.save()
            users.append(user)
        return users

    def _ensure_global_services(self):
        catalog = [
            ("Первичный прием", "Первичный осмотр животного, сбор анамнеза, назначение обследований."),
            ("Повторный прием", "Повторная консультация по результатам обследований."),
            ("Вакцинация", "Введение вакцины согласно календарю прививок."),
            ("Стерилизация/Кастрация", "Плановая хирургическая операция."),
            ("УЗИ", "Ультразвуковое исследование внутренних органов."),
            ("Рентген", "Рентгенологическое исследование."),
            ("Чистка зубов", "Профессиональная гигиена полости рта."),
        ]
        services = []
        for name, desc in catalog:
            svc, _ = Service.objects.get_or_create(
                name=name,
                defaults=dict(description=desc),
            )
            services.append(svc)
        return services

    def _price_for_service(self, name: str) -> float:
        base = {
            "Первичный прием": 1500,
            "Повторный прием": 1000,
            "Вакцинация": 1200,
            "Стерилизация/Кастрация": 8000,
            "УЗИ": 2500,
            "Рентген": 2300,
            "Чистка зубов": 3000,
        }
        return float(base.get(name, 2000))

    def _duration_for_service(self, name: str) -> int:
        durations = {
            "Первичный прием": 40,
            "Повторный прием": 20,
            "Вакцинация": 15,
            "Стерилизация/Кастрация": 90,
            "УЗИ": 30,
            "Рентген": 25,
            "Чистка зубов": 50,
        }
        return durations.get(name, 30)

    def _next_weekday(self, d: date, weekday_choice: Weekday) -> date:
        # weekday(): Monday=0,... Sunday=6
        target = int(weekday_choice)
        days_ahead = (target - d.weekday() + 7) % 7
        days_ahead = 7 if days_ahead == 0 else days_ahead
        return d + timedelta(days=days_ahead)