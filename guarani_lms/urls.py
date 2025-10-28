from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from learning import views as learning_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/signup/", learning_views.signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("learning/", include("learning.urls")), 
     # include the app urls
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)