from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main.views_cal import *


urlpatterns = [
    path('admin/', admin.site.urls),
    path("appointments/", AppointmentCreateView.as_view(), name="appointments-create"),
    path("", include("main.urls_auth")), 
    path('', include('main.urls')),  
    path("", include("main.urls_clinic"))
]

# Раздача медиа-файлов для DEBUG=True и production
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Для production режима (DEBUG=False)
    from django.views.static import serve
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]