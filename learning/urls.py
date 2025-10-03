from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("lessons/<int:pk>/", views.lesson_detail, name="lesson_detail"),
    path("glossary/", views.glossary_view, name="glossary"),

    # APIs
    path("api/translate-and-add/", views.api_translate_and_add, name="api_translate_and_add"),
    path("api/glossary/add/", views.api_add_glossary_entry, name="api_add_glossary_entry"),
    path("api/exercises/fillblank/", views.api_submit_fillblank, name="api_submit_fillblank"),
    path("api/exercises/mcq/", views.api_submit_mcq, name="api_submit_mcq"),
    path("api/exercises/matching/", views.api_submit_matching, name="api_submit_matching"),
    path("api/pronunciation/attempt/", views.api_save_pronunciation_attempt, name="api_save_pronunciation_attempt"),
    path("api/azure/token/", views.api_azure_token, name="api_azure_token"),

    # SRS (AI)
    path("srs/study/", views.srs_study_view, name="srs_study"),
    path("api/srs/sync/", views.api_srs_sync, name="api_srs_sync"),
    path("api/srs/next/", views.api_srs_next, name="api_srs_next"),
    path("api/srs/grade/", views.api_srs_grade, name="api_srs_grade"),

    path("api/glossary/bulk-add/", views.api_glossary_bulk_add, name="api_glossary_bulk_add"),

    # SRS state/mode
path("api/srs/state/", views.api_srs_state, name="api_srs_state"),
path("api/srs/set-mode/", views.api_srs_set_mode, name="api_srs_set_mode"),

    path("exercises/", views.exercises_view, name="exercises"),
    path("lessons/", views.lessons_overview, name="lessons_overview"),
    
    path("api/exercises/dragdrop/", views.api_submit_dragdrop, name="api_submit_dragdrop"),
path("api/exercises/listening/", views.api_submit_listening, name="api_submit_listening"),
path("api/exercises/translation/", views.api_submit_translation, name="api_submit_translation"),

path("api/glossary/<int:pk>/upload-audio/", views.api_glossary_upload_audio, name="api_glossary_upload_audio"),
path("api/tts/", views.tts_view, name="tts"),

# AI-Powered Features
path("api/ai-translate/", views.api_ai_translate, name="api_ai_translate"),
path("api/ai-pronunciation-analysis/", views.api_ai_pronunciation_analysis, name="api_ai_pronunciation_analysis"),
path("api/ai-generate-exercise/", views.api_ai_generate_exercise, name="api_ai_generate_exercise"),

# Enhanced Gamification APIs
path("api/user-profile/", views.api_user_profile, name="api_user_profile"),
path("api/pet-interact/", views.api_pet_interact, name="api_pet_interact"),
path("api/daily-challenges/", views.api_daily_challenges, name="api_daily_challenges"),
path("api/update-daily-challenge/", views.api_update_daily_challenge, name="api_update_daily_challenge"),
path("api/leaderboard/", views.api_leaderboard, name="api_leaderboard"),
path("api/award-achievement/", views.api_award_achievement, name="api_award_achievement"),

# AI Lesson Creation
path("create-lesson-ai/", views.create_lesson_ai, name="create_lesson_ai"),
]
