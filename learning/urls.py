# learning/urls.py
from django.urls import path
from .views import (
    signup, DashboardView, lesson_detail, glossary_view,
    api_translate_and_add, api_add_glossary_entry,
    api_submit_fillblank, api_submit_mcq, api_submit_matching,
    api_save_pronunciation_attempt, api_azure_token
)

urlpatterns = [
    path("signup/", signup, name="signup"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("lessons/<int:pk>/", lesson_detail, name="lesson_detail"),
    path("glossary/", glossary_view, name="glossary"),
    path("api/translate-and-add/", api_translate_and_add, name="api_translate_and_add"),
    path("api/glossary/add/", api_add_glossary_entry, name="api_add_glossary_entry"),
    path("api/exercises/fillblank/", api_submit_fillblank, name="api_submit_fillblank"),
    path("api/exercises/mcq/", api_submit_mcq, name="api_submit_mcq"),
    path("api/exercises/matching/", api_submit_matching, name="api_submit_matching"),
    path("api/pronunciation/attempt/", api_save_pronunciation_attempt, name="api_save_pronunciation_attempt"),
    path("api/azure/token/", api_azure_token, name="api_azure_token"),
]