# Guaraní LMS (Django)

Learn Guaraní with lessons, exercises, speaking practice, a personal glossary, and an AI‑powered spaced‑repetition (SRS) review system. Designed to run fully offline by default.

## Highlights
- Auth + Admin
  - Login/logout, Django Admin with CRUDL for lessons and content.
- Lessons
  - Sections with text/audio, written exercises: Fill‑in‑the‑blank, Multiple‑choice, Matching.
- Speaking practice
  - Works out of the box with the browser’s mic (Web Speech API fallback).
  - Optional Azure Speech token endpoint if you add keys later.
- Personal Glossary
  - Manual add (ES → GN). No keys needed.
  - Optional translator integration (keep disabled if your network blocks API calls).
- AI Feature (local, no cloud)
  - Adaptive Spaced Repetition (SRS) with an online learning scheduler:
    - Learner ability (θ) and per‑card difficulty learned from your 0–5 ratings.
    - Memory half‑life updated per review; next interval scheduled to hit ~85% recall.
- Zero required external services
  - Everything runs locally. Optional integrations are documented below.

## Tech
- Django 4.2, DRF for JSON endpoints
- HTML/CSS/vanilla JS
- SQLite (dev)
- Optional: Azure Speech (Pronunciation token), Remote translation APIs (disabled by default)

## Quick Start (local)
1) Create venv and install deps
   - Windows PowerShell
     - py -3 -m venv .venv
     - .\.venv\Scripts\Activate.ps1
     - python -m pip install --upgrade pip
     - pip install -r requirements.txt
   - macOS/Linux
     - python3 -m venv .venv
     - source .venv/bin/activate
     - python -m pip install --upgrade pip
     - pip install -r requirements.txt

2) Environment
   - cp .env.example .env
   - Set DJANGO_SECRET_KEY to any random string
   - Leave external API vars empty unless you plan to use them.

3) Migrate + superuser
   - python manage.py makemigrations learning
   - python manage.py migrate
   - python manage.py createsuperuser

4) Run
   - python manage.py runserver
   - http://127.0.0.1:8000/

## Using the App
- Add content: /admin/
  - Create Lessons, Sections, Exercises
  - Add Glossary entries (or via UI)
- Learner flow
  - Register/Login
  - Dashboard → pick a lesson
  - Written exercises: instant scoring
  - Speaking practice: click “Grabar” (browser mic). If you later add Azure keys, the app will use them automatically.
- Glossary
  - /learning/glossary/ → use “Agregar manual”
  - Optional: “Traducir y Agregar” requires a translator backend; by default it’s safe‑disabled.
- AI SRS (offline)
  - /learning/srs/study/
  - Show answer → rate 0–5
  - The scheduler updates per‑card difficulty, your ability, and next interval.

## Multiple-choice data format
In Admin, enter choices_json as:
```json
[
  {"key":"A","text":"Opción A"},
  {"key":"B","text":"Opción B"},
  {"key":"C","text":"Opción C"}
]