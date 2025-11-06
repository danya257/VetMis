from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import *

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),

    path('animals/', AnimalListView.as_view(), name='animal-list'),
    path('animals/create/', AnimalCreateView.as_view(), name='animal-create'),
    path('animals/<int:pk>/', AnimalDetailView.as_view(), name='animal-detail'),
    path('animals/<int:pk>/update/', AnimalUpdateView.as_view(), name='animal-update'),
    path('services/add-ajax/', views.add_service_ajax, name='add_service_ajax'),
    
    path('clinics/', views.clinics_list, name='clinics_list'),
    path('book-appointment/<int:clinic_id>/', book_appointment, name='book_appointment'),
    
    path('animals/<int:pk>/services/', MedicalServiceListView.as_view(), name='service-list'),
    path('animals/<int:pk>/services/create/', MedicalServiceCreateView.as_view(), name='service-create'),
    path('', BlogArticleListView.as_view(), name='blog-list'),
    path('blog/<slug:slug>/', BlogArticleDetailView.as_view(), name='blog-article'),
    path('services/<int:pk>/update/',MedicalServiceUpdateView.as_view(),name='service-update'),
    path('services/<int:pk>/delete/', MedicalServiceDeleteView.as_view(), name='service-delete'),
]