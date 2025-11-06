from django.core.management.base import BaseCommand
from django.utils.text import slugify

from medanit.main.models import Clinic, CalProfileType, CalEventType


class Command(BaseCommand):
    help = "Создает 4 демонстрационных клиники и типы событий Cal."

    def handle(self, *args, **options):
        base_url = "https://cal.com"

        demos = [
            {"name": "Ветклиника Лапушка", "cal_type": CalProfileType.USER, "cal_slug": "demo-vet-1"},
            {"name": "Кот и Пес", "cal_type": CalProfileType.TEAM, "cal_slug": "demo-team-2"},
            {"name": "Айболит+", "cal_type": CalProfileType.ORG, "cal_slug": "demo-org-3"},
            {"name": "ЗооДок", "cal_type": CalProfileType.USER, "cal_slug": "demo-vet-4"},
        ]

        created_count = 0
        for d in demos:
            clinic, created = Clinic.objects.get_or_create(
                slug=slugify(d["name"]),
                defaults={
                    "name": d["name"],
                    "description": "Демонстрационная клиника",
                    "is_demo": True,
                    "cal_profile_type": d["cal_type"],
                    "cal_profile_slug": d["cal_slug"],
                    "cal_base_url": base_url,
                }
            )
            if created:
                created_count += 1

            # Добавим типы событий
            ets = [
                ("Первичный прием", "consultation-15min", 15),
                ("Вакцинация", "vaccination-30min", 30),
                ("Повторный прием", "followup-20min", 20),
            ]
            for name, slug, dur in ets:
                CalEventType.objects.get_or_create(
                    clinic=clinic,
                    event_type_slug=slug,
                    defaults={"name": name, "duration_minutes": dur, "is_active": True}
                )

        self.stdout.write(self.style.SUCCESS(f"Готово. Создано новых клиник: {created_count}"))