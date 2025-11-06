from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import resolve_url  # Правильный импорт для resolve_url
from django.urls import NoReverseMatch, reverse
from django.conf import settings

from .views_clinic import ClinicDashboardView

from .forms import CustomAuthenticationForm  # Убедитесь, что это правильно импортируется из вашего forms.py


def _safe_resolve(candidates, default="/"):
    """
    Пытается зарезолвить список кандидатов (имя маршрута или абсолютный путь).
    Возвращает первый успешно резолвленный URL, иначе default.
    """
    for name_or_url in candidates:
        if not name_or_url:
            continue
        try:
            return resolve_url(name_or_url)
        except NoReverseMatch:
            continue
        except Exception:
            continue
    return default or "/"


class CustomLoginView(LoginView):
    authentication_form = CustomAuthenticationForm
    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Прокинем роль в шаблон (для переключателя)
        role = self.request.POST.get("login_type") or self.request.GET.get("role") or "user"
        ctx["role"] = role
        return ctx

    def form_valid(self, form):
        # Логика remember_me из вашего проекта
        remember_me = form.cleaned_data.get("remember_me")
        if not remember_me:
            # Сессия стирается при закрытии браузера
            self.request.session.set_expiry(0)
        else:
            # 2 недели
            self.request.session.set_expiry(1209600)
        return super().form_valid(form)

    def get_success_url(self):
        # 1) Уважаем ?next=
        next_url = self.get_redirect_url()
        if next_url:
            return next_url

        # 2) Роль
        role = self.request.POST.get("login_type") or self.request.GET.get("role") or "user"

        if role == "clinic":
            # Можно переопределить в settings.py: CLINIC_DASHBOARD_URL_NAME = "my_clinic_home"
            return _safe_resolve(
                [
                    getattr(settings, "CLINIC_DASHBOARD_URL_NAME", None),
                    "clinic_dashboard",         # имя вашего маршрута дашборда
                    "/clinic/dashboard/",       # прямой путь
                ],
                default="/",
            )

        # Пользователь (владелец питомца)
        # Можно задать в settings.py: USER_DASHBOARD_URL_NAME = "animal-list"
        return _safe_resolve(
            [
                getattr(settings, "USER_DASHBOARD_URL_NAME", None),
                "animal-list",               # имя по вашему проекту с дефисом
                "animal_list",               # альтернативное имя с подчеркиванием
                "animals",                   # если есть такой name
                "/animals/",                 # прямой путь
            ],
            default="/",
        )


