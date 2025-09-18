# guarani_lms/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("learning/", include("learning.urls")),
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)