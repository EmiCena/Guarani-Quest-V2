# README.md
# Guaraní Learning Platform (Django)

## Features
- Auth: login/logout, registration
- Admin CRUDL: Lessons, lesson content, exercises, words/phrases
- Oral practice with real-time pronunciation analysis (Azure Speech SDK in-browser)
- Written exercises: fill-in-the-blanks, MCQ, matching
- Progress tracking: per-lesson progress with confidence bars
- Glossary: personal word bank with Google Translate (es → gn)

## Tech stack
- Backend: Django 4.2, Django ORM, DRF for JSON endpoints
- Frontend: HTML + CSS + vanilla JS
- Pronunciation: Azure Cognitive Services Speech (Pronunciation Assessment)
- Translation: Google Cloud Translate API (v2)
- DB: SQLite by default

## Prerequisites
- Python 3.10+
- Azure Speech resource (region + key)
- Google Cloud project and service account with Translate API enabled

## Quick start
1) Clone and install dependencies
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt

2) Configure environment
   - cp .env.example .env
   - Fill AZURE_SPEECH_REGION and AZURE_SPEECH_KEY
   - Set GOOGLE_APPLICATION_CREDENTIALS to the absolute path of your service account JSON
   - For dev, leave DEBUG=True

3) Migrate and create superuser
   - python manage.py migrate
   - python manage.py createsuperuser

4) Run
   - python manage.py runserver
   - Visit http://127.0.0.1:8000/
   - Admin at /admin/

## User flows
- Register at /learning/signup/ or via default auth (/accounts/login/)
- Dashboard at /learning/dashboard/ shows progress per lesson
- Lessons at /learning/lessons/<id>/ include written and oral exercises
- Glossary at /learning/glossary/ for AI translation and personal notes

## Admin
- Use Django Admin for full CRUDL on:
  - Lessons, LessonSection, FillBlankExercise, MultipleChoiceExercise, MatchingExercise (+ MatchingPair)
  - PronunciationExercise (upload reference audio)
  - WordPhrase (dictionary seed content)

## Pronunciation (real-time)
- Frontend uses Azure Speech JavaScript SDK to stream mic audio to Azure for scoring
- Backend issues short-lived token via /learning/api/azure/token/
- Results (accuracy, fluency, completeness) update UI and are saved via /learning/api/pronunciation/attempt/

## Translation
- Backend endpoint /learning/api/translate-and-add/ calls Google Translate (es → gn)
- Stores result in user’s Glossary with ability to add notes via /learning/api/glossary/add/

## Security
- Keep secrets in .env; do not expose keys in frontend
- HTTPS recommended for mic access and tokens

## API endpoints
- POST /learning/api/translate-and-add/ { source_text_es }
- POST /learning/api/glossary/add/ { source_text_es, translated_text_gn, notes? }
- POST /learning/api/exercises/fillblank/ { exercise_id, answer }
- POST /learning/api/exercises/mcq/ { exercise_id, selected_key }
- POST /learning/api/exercises/matching/ { exercise_id, pairs: [{left, right}, ...] }
- POST /learning/api/pronunciation/attempt/ { exercise_id, expected_text, accuracy_score, fluency_score, completeness_score, prosody_score? }
- GET /learning/api/azure/token/ { token, region }

## Database schema (key tables)
- Lesson(id, title, description, order, is_published)
- LessonSection(id, lesson_id, title, body, reference_audio, order)
- FillBlankExercise(id, lesson_id, prompt_text, correct_answer, order)
- MultipleChoiceExercise(id, lesson_id, question_text, choices_json, correct_key, order)
- MatchingExercise(id, lesson_id, instructions, order)
- MatchingPair(id, exercise_id, left_text, right_text)
- PronunciationExercise(id, lesson_id, text_guarani, reference_audio, order)
- WordPhrase(id, word_guarani, translation_es, audio_pronunciation, notes)
- GlossaryEntry(id, user_id, source_text_es, translated_text_gn, notes, created_at)
- UserExerciseResult(user_id, content_type, object_id, score, is_correct, attempts, last_submitted)
- PronunciationAttempt(user_id, exercise_id, expected_text, accuracy_score, fluency_score, completeness_score, prosody_score, audio_file?, created_at)
- UserLessonProgress(user_id, lesson_id, written_score, pronunciation_confidence, progress_percent, completed, updated_at)

## Deployment notes
- Set DEBUG=False, configure ALLOWED_HOSTS
- Use WhiteNoise or a CDN for static files
- Use HTTPS