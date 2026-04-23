from django.conf import settings
from django.db import models
from ckeditor.fields import RichTextField
from django.utils import timezone
from django.utils.text import slugify
from main.utils.translit import TranslitFileSystemStorage


# ===========================
# СУЩЕСТВУЮЩИЕ МОДЕЛИ
# ===========================

class Animal(models.Model):
    name = models.CharField(max_length=100, verbose_name="Имя животного")
    species = models.CharField(max_length=50, verbose_name="Вид (например, собака, кошка)")
    breed = models.CharField(max_length=50, verbose_name="Порода", blank=True)
    birthday = models.DateField(verbose_name="Дата рождения", blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="animals",
        verbose_name="Владелец"
    )
    photo = models.ImageField(
        upload_to="animals/photos/",
        verbose_name="Фотография",
        blank=True,
        null=True,
        storage=TranslitFileSystemStorage()
    )

    def __str__(self):
        return f"{self.name} ({self.species})"


class Pedigree(models.Model):
    animal = models.OneToOneField(Animal, on_delete=models.CASCADE, related_name="pedigree", verbose_name="Животное")
    info = models.TextField(verbose_name="Родословная", blank=True)

    def __str__(self):
        return f"Родословная {self.animal.name}"


class Vaccination(models.Model):
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name="vaccinations", verbose_name="Животное")
    name = models.CharField(max_length=100, verbose_name="Название вакцины")
    date = models.DateField(verbose_name="Дата вакцинации")
    notes = models.TextField(verbose_name="Заметки", blank=True)

    def __str__(self):
        return f"{self.name} - {self.animal.name} ({self.date.strftime('%d.%m.%Y')})"


# ===========================
# СПРАВОЧНИКИ/УСЛУГИ
# ===========================

class Service(models.Model):
    """
    Справочник услуг (глобальный). Внимание: поле 'date' удалено, т.к. дата проведения относится к конкретному оказанию.
    """
    name = models.CharField(max_length=100, verbose_name="Название услуги")
    description = models.TextField(verbose_name="Описание услуги", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кто создал",
        related_name="services_created"
    )

    def __str__(self):
        return self.name


# ===========================
# НОВЫЕ МОДЕЛИ ДЛЯ КЛИНИК
# ===========================

class Clinic(models.Model):
    """
    Партнерская клиника (или ваша собственная).
    """
    name = models.CharField(max_length=200, verbose_name="Название клиники")
    slug = models.SlugField(max_length=220, unique=True, verbose_name="Слаг")
    description = models.TextField(verbose_name="Описание", blank=True)
    address = models.CharField(max_length=300, verbose_name="Адрес", blank=True)
    phone = models.CharField(max_length=50, verbose_name="Телефон", blank=True)
    email = models.EmailField(verbose_name="Email", blank=True)
    website = models.URLField(verbose_name="Сайт", blank=True)
    timezone = models.CharField(max_length=50, verbose_name="Часовой пояс", default="Europe/Moscow")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_clinics",
        verbose_name="Владелец кабинета клиники"
    )
    is_demo = models.BooleanField(default=False, verbose_name="Демонстрационная клиника")

    class Meta:
        verbose_name = "Клиника"
        verbose_name_plural = "Клиники"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class VetProfile(models.Model):
    """
    Профиль врача (опционально связывается с пользователем).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vet_profiles",
        verbose_name="Пользователь-врач"
    )
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="vets", verbose_name="Клиника")
    full_name = models.CharField(max_length=150, verbose_name="ФИО врача")
    specialties = models.CharField(max_length=200, verbose_name="Специализация", blank=True)
    bio = models.TextField(verbose_name="Био", blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Врач"
        verbose_name_plural = "Врачи"

    def __str__(self):
        return f"{self.full_name} — {self.clinic.name}"


class AppointmentStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Запланирована"
    CANCELLED = "cancelled", "Отменена"
    COMPLETED = "completed", "Завершена"
    RESCHEDULED = "rescheduled", "Перенесена"


class Appointment(models.Model):
    """
    Запись на прием.
    """
    clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, related_name="appointments", verbose_name="Клиника")
    animal = models.ForeignKey(
        Animal, on_delete=models.PROTECT, related_name="appointments", verbose_name="Животное"
    )
    booker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments_booked",
        verbose_name="Кто записал"
    )
    vet = models.ForeignKey(
        VetProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name="Врач"
    )

    start_at = models.DateTimeField(verbose_name="Начало")
    end_at = models.DateTimeField(verbose_name="Окончание")
    timezone = models.CharField(max_length=50, default="Europe/Moscow", verbose_name="Часовой пояс")

    status = models.CharField(max_length=20, choices=AppointmentStatus.choices, default=AppointmentStatus.SCHEDULED)
    notes = models.TextField(verbose_name="Заметки", blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        ordering = ["-start_at"]
        verbose_name = "Запись"
        verbose_name_plural = "Записи"

    def __str__(self):
        return f"{self.clinic.name} — {self.start_at} [{self.status}]"


# ===========================
# ОКАЗАННЫЕ УСЛУГИ
# ===========================

class AnimalService(models.Model):
    animal = models.ForeignKey(
        Animal,
        on_delete=models.CASCADE,
        related_name="provided_services",
        verbose_name="Животное"
    )
    # Может быть null, если услуга кастомная
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        verbose_name="Вид услуги",
        blank=True,
        null=True
    )
    # Имя услуги, если она не из справочника
    custom_service_name = models.CharField(
        max_length=100,
        verbose_name="Своя услуга (название)",
        blank=True
    )
    # Скопированное описание из Service (на момент оказания) или ручное для кастомной услуги
    service_description = models.TextField(
        verbose_name="Описание услуги",
        blank=True
    )
    date = models.DateTimeField(
        verbose_name="Дата и время услуги",
        default=timezone.now
    )
    performer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performed_services",
        verbose_name="Исполнитель"
    )
    cost = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        verbose_name="Стоимость",
        blank=True,
        null=True
    )
    custom_description = models.TextField(
        verbose_name="Комментарий/детали (необязательно)",
        blank=True
    )
    is_custom = models.BooleanField(
        default=False,
        verbose_name="Кастомная услуга (только для этого пользователя)"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Кто добавил",
        related_name="animal_services_created"
    )
    clinic = models.ForeignKey(  # Новое: куда услуга относится
        Clinic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="animal_services",
        verbose_name="Клиника"
    )

    def __str__(self):
        if self.is_custom:
            return f"{self.custom_service_name or 'Своя услуга'} для {self.animal.name} от {self.date.strftime('%d.%m.%Y')}"
        elif self.service:
            return f"{self.service.name} для {self.animal.name} от {self.date.strftime('%d.%m.%Y')}"
        else:
            return f"Услуга для {self.animal.name} от {self.date.strftime('%d.%m.%Y')}"


# ===========================
# УСЛУГИ КЛИНИК С ЦЕНАМИ (НОВОЕ)
# ===========================

class Currency(models.TextChoices):
    RUB = "RUB", "₽ Российский рубль"
    USD = "USD", "$ Доллар США"
    EUR = "EUR", "€ Евро"


class ClinicService(models.Model):
    """
    Привязка глобальной услуги к конкретной клинике с ценой и активностью.
    """
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="clinic_services", verbose_name="Клиника")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="clinic_services", verbose_name="Услуга")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.RUB, verbose_name="Валюта")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    # Опционально: длительность по умолчанию
    default_duration_minutes = models.PositiveIntegerField(null=True, blank=True, verbose_name="Длительность по умолчанию, мин")
    # Для сортировки на витрине
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Порядок сортировки")

    class Meta:
        verbose_name = "Услуга клиники"
        verbose_name_plural = "Услуги клиники"
        unique_together = (("clinic", "service"),)
        ordering = ["sort_order", "service__name"]
        indexes = [
            models.Index(fields=["clinic", "is_active"]),
        ]

    def __str__(self):
        return f"{self.clinic.name}: {self.service.name} — {self.price} {self.currency}"


# ===========================
# ДОСТУПНОСТЬ ВРАЧЕЙ (НОВОЕ)
# ===========================

class Weekday(models.IntegerChoices):
    MONDAY = 0, "Понедельник"
    TUESDAY = 1, "Вторник"
    WEDNESDAY = 2, "Среда"
    THURSDAY = 3, "Четверг"
    FRIDAY = 4, "Пятница"
    SATURDAY = 5, "Суббота"
    SUNDAY = 6, "Воскресенье"


class VetAvailability(models.Model):
    """
    Базовая модель окна доступности врача.
    Можно задавать как повторяющиеся окна по дням недели, так и одноразовые конкретные даты.
    Свободные слоты вычисляются: availability - занятые Appointment.
    """
    vet = models.ForeignKey(VetProfile, on_delete=models.CASCADE, related_name="availabilities", verbose_name="Врач")
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="availabilities", verbose_name="Клиника")

    # Повторяющееся окно по дню недели:
    weekday = models.IntegerField(choices=Weekday.choices, null=True, blank=True, verbose_name="День недели")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Начало (локальное время клиники)")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Окончание (локальное время клиники)")

    # Одноразовое окно по конкретной дате:
    date = models.DateField(null=True, blank=True, verbose_name="Конкретная дата (локальная)")

    # Параметры слотов:
    slot_minutes = models.PositiveIntegerField(default=30, verbose_name="Длительность слота, мин")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Окно доступности врача"
        verbose_name_plural = "Окна доступности врачей"
        indexes = [
            models.Index(fields=["clinic", "vet", "is_active"]),
            models.Index(fields=["weekday"]),
            models.Index(fields=["date"]),
        ]

    def clean(self):
        # Валидация: должно быть либо окно по дню недели, либо конкретная дата.
        if not self.weekday and not self.date:
            raise ValueError("Укажите weekday или date")
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time должен быть меньше end_time")
        if self.slot_minutes == 0:
            raise ValueError("slot_minutes должен быть > 0")

    def __str__(self):
        base = f"{self.vet.full_name} @ {self.clinic.name}"
        if self.date:
            return f"{base} — {self.date} {self.start_time}-{self.end_time}"
        else:
            wd = Weekday(self.weekday).label if self.weekday is not None else "—"
            return f"{base} — {wd} {self.start_time}-{self.end_time}"


# ===========================
# БЛОГ (как было)
# ===========================

class BlogCategory(models.Model):
    name = models.CharField("Категория", max_length=50, unique=True)
    slug = models.SlugField("Слаг", max_length=60, unique=True)

    class Meta:
        verbose_name = "Категория блога"
        verbose_name_plural = "Категории блога"

    def __str__(self):
        return self.name


class BlogArticle(models.Model):
    category = models.ForeignKey(BlogCategory, on_delete=models.PROTECT, related_name="articles", verbose_name="Категория")
    title = models.CharField("Заголовок", max_length=200)
    slug = models.SlugField("Слаг (URL)", unique=True)
    preview = models.ImageField(
        "Превью-изображение",
        upload_to="blog/previews/",
        blank=True,
        null=True,
        storage=TranslitFileSystemStorage()
    )
    content = RichTextField("Текст статьи")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Автор")
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    is_published = models.BooleanField("Опубликовано", default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"

    def __str__(self):
        return self.title

