from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
import json
from django.views.decorators.http import require_POST
from .models import Animal, AnimalService, Appointment, Service, VetProfile
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm
from django.contrib import messages
from .forms import CustomUserCreationForm
from .AnimalForm import AnimalForm
from django.http import JsonResponse, HttpResponseBadRequest
from .models import BlogArticle, BlogCategory
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from .models import Clinic
from django.utils import timezone
from datetime import datetime

@login_required 
def clinics_list(request): 
    clinics = list(Clinic.objects.all().order_by('name')) 
    return render(request, 'clinic/list.html', {'clinics': clinics})
        
@login_required
def book_appointment(request, clinic_id):
    clinic = get_object_or_404(Clinic, id=clinic_id)
    user_pets = Animal.objects.filter(owner=request.user)
    clinic_vets = VetProfile.objects.filter(clinic=clinic)
    
    if request.method == "POST":
        pet_id = request.POST.get("pet", "").strip()
        vet_id = request.POST.get("vet", "").strip()
        pet_name = request.POST.get("pet_name", "").strip()
        species = request.POST.get("species", "").strip()
        contact_phone = request.POST.get("contact_phone", "").strip()
        desired_date = request.POST.get("desired_date", "").strip()
        desired_time = request.POST.get("desired_time", "").strip()
        comment = request.POST.get("comment", "").strip()
        
        errors = {}
        
        animal = None
        if pet_id:
            try:
                animal = Animal.objects.get(id=pet_id, owner=request.user)
            except Animal.DoesNotExist:
                errors["pet"] = "Выбранный питомец не найден или не принадлежит вам."
        elif pet_name and species:
            pass
        else:
            errors["pet"] = "Выберите существующего питомца или введите данные для нового."
        
        vet = None
        if vet_id:
            try:
                vet = VetProfile.objects.get(id=vet_id, clinic=clinic)
            except VetProfile.DoesNotExist:
                errors["vet"] = "Выбранный ветеринар не найден в этой клинике."
        else:
            errors["vet"] = "Выберите ветеринара."
        
        if not contact_phone:
            errors["contact_phone"] = "Укажите контактный телефон."
        
        desired_dt = None
        if not desired_date or not desired_time:
            errors["desired_datetime"] = "Укажите желаемые дату и время."
        else:
            try:
                desired_dt = datetime.strptime(f"{desired_date} {desired_time}", "%Y-%m-%d %H:%M")
                desired_dt = timezone.make_aware(desired_dt, timezone.get_current_timezone())
                if desired_dt < timezone.now():
                    errors["desired_datetime"] = "Нельзя выбрать прошедшую дату/время."
            except ValueError:
                errors["desired_datetime"] = "Неверный формат даты или времени."
        
        if errors:
            for msg in errors.values():
                messages.error(request, msg)
            context = {
                "clinic": clinic,
                "user_pets": user_pets,
                "clinic_vets": clinic_vets,
                "pet_name": pet_name,
                "species": species,
                "contact_phone": contact_phone,
                "desired_date": desired_date,
                "desired_time": desired_time,
                "comment": comment,
                "selected_pet": pet_id,
                "selected_vet": vet_id,
            }
            return render(request, "clinic/book_appointment.html", context)
        
        if not animal:
            animal = Animal.objects.create(
                name=pet_name,
                species=species,
                owner=request.user,
                contact_phone=contact_phone,
            )
        
        appointment = Appointment.objects.create(
            clinic=clinic,
            animal=animal,
            vet=vet,
            start_at=desired_dt,
            status="PENDING",
            comment=comment,
        )
        
        messages.success(request, "Запись на приём успешно создана! Мы свяжемся с вами для подтверждения.")
        return redirect("clinic_detail", clinic_id=clinic.id)
    
    context = {
        "clinic": clinic,
        "user_pets": user_pets,
        "clinic_vets": clinic_vets,
    }
    return render(request, "clinic/book_appointment.html", context)



class BlogArticleListView(ListView):
    model = BlogArticle
    template_name = "blog/article_list.html"
    context_object_name = "articles"
    paginate_by = 8
    queryset = BlogArticle.objects.filter(is_published=True).select_related("category").order_by("-created_at")

class BlogArticleDetailView(DetailView):
    model = BlogArticle
    template_name = "blog/article_detail.html"
    context_object_name = "article"
    slug_field = "slug"
    slug_url_kwarg = "slug"

@require_POST
def add_service_ajax(request):
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'Название услуги обязательно.'})
        service = Service.objects.create(name=name, description=description)
        return JsonResponse({'success': True, 'id': service.id, 'name': service.name})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'Ошибка сервера: %s' % str(e)})

ANIMAL_SPECIES = [
    ('Собака', 'Собака'),
    ('Кошка', 'Кошка'),
    ('Кролик', 'Кролик'),
]
SPECIES_BREEDS = {
    'Собака': ['Лабрадор', 'Пудель', 'Бульдог', 'Двортерьер'],
    'Кошка': ['Сиамская', 'Персидская', 'Мейн-кун'],
    'Кролик': ['Ангорский', 'Рекс', 'Карликовый'],
}

class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Вы успешно зарегистрировались!")
        return response

class CustomLoginView(LoginView):
    authentication_form = CustomAuthenticationForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(1209600)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("animal-list")

class AnimalListView(LoginRequiredMixin, ListView):
    model = Animal
    template_name = "animals/animal_list.html"
    context_object_name = "animals"

    def get_queryset(self):
        return Animal.objects.filter(owner=self.request.user)

class AnimalDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Animal
    template_name = "animals/animal_detail.html"
    context_object_name = "animal"

    def test_func(self):
        animal = self.get_object()
        return animal.owner == self.request.user

class AnimalCreateView(LoginRequiredMixin, CreateView):
    model = Animal
    form_class = AnimalForm
    template_name = "animals/animal_form.html"
    success_url = reverse_lazy("animal-list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_species = ANIMAL_SPECIES[0][0]
        selected_breed = ''
        breed_choices = SPECIES_BREEDS.get(selected_species, [])
        context["species_choices"] = ANIMAL_SPECIES
        context["breed_choices"] = breed_choices
        context["selected_species"] = selected_species
        context["custom_species"] = ""
        context["selected_breed"] = selected_breed
        context["custom_breed"] = ""
        context["breeds_by_species_json"] = json.dumps(SPECIES_BREEDS)
        return context

class AnimalUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Animal
    form_class = AnimalForm
    template_name = "animals/animal_form.html"
    success_url = reverse_lazy("animal-list")

    def test_func(self):
        animal = self.get_object()
        return animal.owner == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = self.object
        selected_species = animal.species if animal.species in dict(ANIMAL_SPECIES) else "__other__"
        selected_breed = animal.breed
        breed_choices = SPECIES_BREEDS.get(selected_species, [])
        is_species_other = selected_species == "__other__"
        is_breed_other = (selected_breed not in breed_choices) if not is_species_other else True
        context["species_choices"] = ANIMAL_SPECIES
        context["breed_choices"] = breed_choices
        context["selected_species"] = selected_species
        context["custom_species"] = animal.species if is_species_other else ""
        context["selected_breed"] = selected_breed if not is_breed_other else "__other__"
        context["custom_breed"] = animal.breed if is_breed_other else ""
        context["breeds_by_species_json"] = json.dumps(SPECIES_BREEDS)
        return context

class MedicalServiceListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = AnimalService
    template_name = "animals/service_list.html"
    context_object_name = "services"

    def get_queryset(self):
        return AnimalService.objects.filter(animal_id=self.kwargs["pk"])

    def test_func(self):
        animal = Animal.objects.get(pk=self.kwargs["pk"])
        return animal.owner == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        animal = Animal.objects.get(pk=self.kwargs["pk"])
        context['animal'] = animal
        return context

class MedicalServiceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = AnimalService
    fields = ["service", "custom_service_name", "date", "clinic", "cost", "is_custom"]
    template_name = "animals/service_form.html"
    context_object_name = "service"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.animal.owner != self.request.user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()
        return obj

    def test_func(self):
        obj = self.get_object()
        return obj.animal.owner == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['animal'] = self.object.animal
        return context

    def get_success_url(self):
        return reverse_lazy("animal-service-list", kwargs={"pk": self.object.animal.pk})

class MedicalServiceCreateView(LoginRequiredMixin, CreateView):
    model = AnimalService
    fields = ["service", "custom_service_name", "date", "clinic", "cost", "is_custom"]
    template_name = "animals/service_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.animal = Animal.objects.get(pk=kwargs["pk"])
        if self.animal.owner != request.user:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.animal = self.animal
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("animal-detail", kwargs={"pk": self.animal.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['animal'] = self.animal
        return context

class MedicalServiceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = AnimalService
    template_name = "animals/service_confirm_delete.html"
    context_object_name = "service"

    def test_func(self):
        return self.get_object().animal.owner == self.request.user

    def get_success_url(self):
        return reverse_lazy("animal-service-list", kwargs={"pk": self.object.animal.pk})