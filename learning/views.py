# learning/views.py
from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from .models import DragDropExercise, ListeningExercise, TranslationExercise
from .serializers import DragDropSubmissionSerializer, ListeningSubmissionSerializer, TranslationSubmissionSerializer
from django.views.decorators.http import require_http_methods
from django.core.files.base import ContentFile
import time
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .forms import SignUpForm
from .models import (
    Lesson, LessonSection,
    FillBlankExercise, MultipleChoiceExercise, MatchingExercise, MatchingPair,
    PronunciationExercise, GlossaryEntry, WordPhrase,
    UserExerciseResult, PronunciationAttempt, UserLessonProgress,
    SRSDeck, Flashcard, ReviewLog, SRSUserState,
)
from .serializers import (
    FillBlankSubmissionSerializer, MCQSubmissionSerializer, MatchingSubmissionSerializer,
    PronunciationAttemptSerializer, TranslationRequestSerializer, GlossaryEntrySerializer,
    SRSGradeSerializer, BulkGlossaryListSerializer,
)
from .services.translation import translate_es_to_gn
from .services.azure_speech import issue_azure_speech_token
from .services.scoring import levenshtein_ratio
from .services.ai_srs import grade_and_schedule

# learning/views.py
import os, hashlib, subprocess, shutil
from django.http import FileResponse, JsonResponse, HttpResponse
from django.conf import settings

def tts_view(request):
    """
    Devuelve audio WAV generado offline con espeak-ng.
    GET:
      text: texto a leer
      lang: 'gn' (Guaraní) o 'es' (por defecto 'gn')
    """
    text = (request.GET.get("text") or "").strip()
    lang = (request.GET.get("lang") or "gn").strip()
    if not text:
        return HttpResponse("Missing text", status=400)
    if len(text) > 240:
        text = text[:240]

    exe = getattr(settings, "ESPEAK_NG_EXE", None) or shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        return JsonResponse({"error": "espeak-ng not found"}, status=501)

    # Cache por lang+texto
    h = hashlib.sha1(f"{lang}:{text}".encode("utf-8")).hexdigest()[:16]
    cache_dir = os.path.join(settings.MEDIA_ROOT, "tts-cache")
    os.makedirs(cache_dir, exist_ok=True)
    wav_path = os.path.join(cache_dir, f"{lang}-{h}.wav")

    if not os.path.exists(wav_path):
        cmd = [exe, "-v", lang, "-s", "165", "-p", "30", "-w", wav_path, text]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            if lang.lower() != "gn":
                try:
                    subprocess.run([exe, "-v", "gn", "-s", "165", "-p", "30", "-w", wav_path, text],
                                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception:
                    return JsonResponse({"error": "TTS failed"}, status=500)
            else:
                return JsonResponse({"error": "TTS failed"}, status=500)

    return FileResponse(open(wav_path, "rb"), content_type="audio/wav")
# ------------- Auth / Basic pages ------------- #

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "learning/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # All published lessons ordered
        lessons = Lesson.objects.filter(is_published=True).order_by("order")

        # Progress map
        progress_qs = UserLessonProgress.objects.filter(user=user)
        progress_map = {lp.lesson_id: lp for lp in progress_qs}

        # Stats
        lessons_completed = sum(1 for lp in progress_map.values() if lp.completed)
        glossary_count = GlossaryEntry.objects.filter(user=user).count()

        # Next lesson: first not completed (by order), or first lesson as fallback
        not_completed_ids = [lid for lid, lp in progress_map.items() if not lp.completed]
        next_lesson = (lessons.filter(id__in=not_completed_ids).first() or lessons.first())

        # Recent lessons by last update (fallback to first 3 by order)
        recent_lessons = (
            Lesson.objects.filter(progress__user=user)
            .order_by("-progress__updated_at")
            .distinct()[:4]
        )
        if not recent_lessons:
            recent_lessons = lessons[:4]

        # SRS counters (due today and new allowed)
        due_reviews = 0
        allowed_new = 0
        try:
            deck, _ = SRSDeck.objects.get_or_create(user=user, name="Mi Glosario")
            state, _ = SRSUserState.objects.get_or_create(user=user, deck=deck)
            today = timezone.now().date()
            new_shown = state.new_shown_count if state.new_shown_on == today else 0
            default_limit = {"beginner": 10, "comfortable": 15, "aggressive": 25}.get(state.mode or "comfortable", 15)
            limit = state.new_limit or default_limit
            allowed_new = max(0, limit - new_shown)
            due_reviews = Flashcard.objects.filter(
                user=user, deck=deck, suspended=False, repetitions__gt=0, due_at__lte=timezone.now()
            ).count()
        except Exception:
            pass

        ctx.update({
            "lessons": lessons,              # still handy for small strip
            "progress_map": progress_map,
            "lessons_completed": lessons_completed,
            "glossary_count": glossary_count,
            "next_lesson": next_lesson,
            "recent_lessons": recent_lessons,
            "due_reviews": due_reviews,
            "allowed_new": allowed_new,
        })
        return ctx


@login_required
def lesson_detail(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk, is_published=True)
    ctx = {
        "lesson": lesson,
        "sections": lesson.sections.all(),
        "fillblanks": lesson.fillblanks.all(),
        "mcqs": lesson.mcqs.all(),
        "matchings": lesson.matchings.all(),
        "pronun_exercises": lesson.pronun_exercises.all(),
    }
    return render(request, "learning/lesson_detail.html", ctx)


@login_required
def glossary_view(request):
    entries = GlossaryEntry.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "learning/glossary.html", {"entries": entries})


# ------------- Glossary APIs (safe) ------------- #

@login_required
@api_view(["POST"])
def api_translate_and_add(request):
    serializer = TranslationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    text_es = serializer.validated_data["source_text_es"].strip()

    translated = ""
    try:
        translated = translate_es_to_gn(text_es).strip()
    except Exception:
        translated = ""

    fallback = (not translated) or (translated.lower() == text_es.lower())
    if fallback:
        return Response({"fallback": True, "suggestion": text_es}, status=200)

    entry = GlossaryEntry.objects.create(
        user=request.user, source_text_es=text_es, translated_text_gn=translated
    )
    return Response({"id": entry.id, "translated_text_gn": translated, "fallback": False}, status=200)


@login_required
@api_view(["POST"])
def api_add_glossary_entry(request):
    s = GlossaryEntrySerializer(data=request.data)
    s.is_valid(raise_exception=True)
    entry = GlossaryEntry.objects.create(
        user=request.user,
        source_text_es=s.validated_data["source_text_es"],
        translated_text_gn=s.validated_data["translated_text_gn"],
        notes=s.validated_data.get("notes", ""),
    )
    return Response({"id": entry.id}, status=201)


# ------------- Written Exercises APIs ------------- #

@login_required
@api_view(["POST"])
def api_submit_fillblank(request):
    s = FillBlankSubmissionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(FillBlankExercise, pk=s.validated_data["exercise_id"])
    user_answer = s.validated_data["answer"].strip()
    correct = ex.correct_answer.strip()
    score = 100.0 if user_answer.lower() == correct.lower() else levenshtein_ratio(user_answer, correct)
    is_correct = score >= 90.0
    _save_user_result(request.user, ex, score, is_correct)
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"score": score, "is_correct": is_correct}, status=200)


@login_required
@api_view(["POST"])
def api_submit_mcq(request):
    s = MCQSubmissionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(MultipleChoiceExercise, pk=s.validated_data["exercise_id"])
    selected = s.validated_data["selected_key"].strip().upper()
    is_correct = selected == ex.correct_key.strip().upper()
    score = 100.0 if is_correct else 0.0
    _save_user_result(request.user, ex, score, is_correct)
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"score": score, "is_correct": is_correct}, status=200)


@login_required
@api_view(["POST"])
def api_submit_matching(request):
    s = MatchingSubmissionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(MatchingExercise, pk=s.validated_data["exercise_id"])
    submitted_pairs = s.validated_data["pairs"]
    correct_map = {p.left_text.strip().lower(): p.right_text.strip().lower() for p in ex.pairs.all()}
    total = len(correct_map) or 1
    correct_count = 0
    for item in submitted_pairs:
        left = (item.get("left") or "").strip().lower()
        right = (item.get("right") or "").strip().lower()
        if correct_map.get(left) == right:
            correct_count += 1
    score = (correct_count / total) * 100.0
    is_correct = score >= 100.0
    _save_user_result(request.user, ex, score, is_correct)
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"score": score, "correct": correct_count, "total": total}, status=200)


# ------------- Pronunciation APIs ------------- #

@login_required
@api_view(["POST"])
def api_save_pronunciation_attempt(request):
    s = PronunciationAttemptSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(PronunciationExercise, pk=s.validated_data["exercise_id"])
    PronunciationAttempt.objects.create(
        user=request.user,
        exercise=ex,
        expected_text=s.validated_data["expected_text"],
        accuracy_score=s.validated_data["accuracy_score"],
        fluency_score=s.validated_data["fluency_score"],
        completeness_score=s.validated_data["completeness_score"],
        prosody_score=s.validated_data.get("prosody_score", 0.0),
    )
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"status": "ok"}, status=201)


@login_required
@api_view(["GET"])
def api_azure_token(request):
    try:
        token = issue_azure_speech_token()
        from django.conf import settings
        return Response({"token": token, "region": settings.AZURE_SPEECH_REGION}, status=200)
    except Exception as e:
        return Response({"detail": str(e)}, status=500)


# ------------- Internal helpers ------------- #

def _save_user_result(user, exercise_obj, score: float, is_correct: bool):
    ct = ContentType.objects.get_for_model(type(exercise_obj))
    obj, created = UserExerciseResult.objects.get_or_create(
        user=user, content_type=ct, object_id=exercise_obj.id,
        defaults={"score": score, "is_correct": is_correct, "attempts": 1},
    )
    if not created:
        obj.score = max(obj.score, score)
        obj.is_correct = obj.is_correct or is_correct
        obj.attempts += 1
        obj.save()


def _update_lesson_progress(user, lesson):
    ct_fb = ContentType.objects.get_for_model(FillBlankExercise)
    ct_mcq = ContentType.objects.get_for_model(MultipleChoiceExercise)
    ct_match = ContentType.objects.get_for_model(MatchingExercise)

    fb_ids = list(FillBlankExercise.objects.filter(lesson=lesson).values_list("id", flat=True))
    mcq_ids = list(MultipleChoiceExercise.objects.filter(lesson=lesson).values_list("id", flat=True))
    match_ids = list(MatchingExercise.objects.filter(lesson=lesson).values_list("id", flat=True))

    written_qs = UserExerciseResult.objects.filter(user=user).filter(
        Q(content_type=ct_fb, object_id__in=fb_ids) |
        Q(content_type=ct_mcq, object_id__in=mcq_ids) |
        Q(content_type=ct_match, object_id__in=match_ids)
    )
    written_avg = written_qs.aggregate(avg=Avg("score"))["avg"] or 0.0

    pronun_ex_ids = list(PronunciationExercise.objects.filter(lesson=lesson).values_list("id", flat=True))
    if pronun_ex_ids:
        best_per_ex = []
        for ex_id in pronun_ex_ids:
            avg_acc = PronunciationAttempt.objects.filter(user=user, exercise_id=ex_id).aggregate(avg=Avg("accuracy_score"))["avg"]
            if avg_acc is not None:
                best_per_ex.append(avg_acc)
        pronun_avg = sum(best_per_ex) / len(best_per_ex) if best_per_ex else 0.0
    else:
        pronun_avg = 0.0

    progress_percent = 0.5 * written_avg + 0.5 * pronun_avg

    obj, _ = UserLessonProgress.objects.get_or_create(user=user, lesson=lesson)
    obj.written_score = written_avg
    obj.pronunciation_confidence = pronun_avg
    obj.progress_percent = progress_percent
    obj.completed = progress_percent >= 90.0
    obj.save()


# ------------- SRS (AI scheduler + mode switcher) ------------- #

def _get_or_create_default_deck(user):
    deck, _ = SRSDeck.objects.get_or_create(user=user, name="Mi Glosario")
    return deck

def _get_or_create_user_state(user, deck):
    state, _ = SRSUserState.objects.get_or_create(user=user, deck=deck)
    return state

def _mode_default_limit(mode: str) -> int:
    return {"beginner": 10, "comfortable": 15, "aggressive": 25}.get(mode or "comfortable", 15)

def _apply_daily_reset_to_state(state: SRSUserState):
    today = timezone.now().date()
    if state.new_shown_on != today:
        state.new_shown_on = today
        state.new_shown_count = 0
        if not state.new_limit:
            state.new_limit = _mode_default_limit(state.mode)
        state.save(update_fields=["new_shown_on", "new_shown_count", "new_limit", "updated_at"])

@login_required
@ensure_csrf_cookie
def srs_study_view(request):
    deck = _get_or_create_default_deck(request.user)
    _sync_cards_from_glossary(request.user, deck)
    # Ensure state exists and daily reset applied
    state = _get_or_create_user_state(request.user, deck)
    _apply_daily_reset_to_state(state)
    return render(request, "learning/srs_study.html", {"deck": deck})

def _sync_cards_from_glossary(user, deck):
    existing = set(Flashcard.objects.filter(user=user, deck=deck).values_list("front_text_es", "back_text_gn"))
    to_create = []
    for e in GlossaryEntry.objects.filter(user=user):
        key = (e.source_text_es.strip(), e.translated_text_gn.strip())
        if key not in existing:
            to_create.append(Flashcard(
                user=user, deck=deck,
                front_text_es=e.source_text_es.strip(),
                back_text_gn=e.translated_text_gn.strip(),
                notes=e.notes or "",
                due_at=timezone.now(),
            ))
    if to_create:
        Flashcard.objects.bulk_create(to_create)

@login_required
@api_view(["POST"])
def api_srs_sync(request):
    deck = _get_or_create_default_deck(request.user)
    _sync_cards_from_glossary(request.user, deck)
    state = _get_or_create_user_state(request.user, deck)
    _apply_daily_reset_to_state(state)
    return Response({"status": "ok"}, status=200)

@login_required
@api_view(["GET"])
def api_srs_state(request):
    deck = _get_or_create_default_deck(request.user)
    state = _get_or_create_user_state(request.user, deck)
    _apply_daily_reset_to_state(state)
    now = timezone.now()
    due_reviews = Flashcard.objects.filter(
        user=request.user, deck=deck, suspended=False,
        repetitions__gt=0, due_at__lte=now
    ).count()
    new_available = Flashcard.objects.filter(
        user=request.user, deck=deck, suspended=False,
        repetitions=0
    ).count()
    allowed_new = max(0, (state.new_limit or _mode_default_limit(state.mode)) - state.new_shown_count)
    return Response({
        "mode": state.mode,
        "new_limit": state.new_limit,
        "new_shown_today": state.new_shown_count,
        "allowed_new_today": allowed_new,
        "due_review_count": due_reviews,
        "new_available_count": new_available,
    }, status=200)

@login_required
@api_view(["POST"])
def api_srs_set_mode(request):
    mode = (request.data.get("mode") or "").lower().strip()
    if mode not in {"beginner", "comfortable", "aggressive"}:
        return Response({"detail": "invalid mode"}, status=400)
    deck = _get_or_create_default_deck(request.user)
    state = _get_or_create_user_state(request.user, deck)
    state.mode = mode
    state.new_limit = _mode_default_limit(mode)
    state.save(update_fields=["mode", "new_limit", "updated_at"])
    _apply_daily_reset_to_state(state)
    return api_srs_state(request)

@login_required
@api_view(["POST"])
def api_srs_next(request):
    deck = _get_or_create_default_deck(request.user)
    _sync_cards_from_glossary(request.user, deck)
    state = _get_or_create_user_state(request.user, deck)
    _apply_daily_reset_to_state(state)

    now = timezone.now()

    # 1) Prefer due review cards (repetitions > 0)
    qs = Flashcard.objects.filter(
        user=request.user, deck=deck, suspended=False,
        repetitions__gt=0, due_at__lte=now
    ).order_by("due_at")
    card = qs.first()
    if not card:
        # 2) Otherwise allow new cards (repetitions == 0) within today's cap
        allowed_new = max(0, (state.new_limit or _mode_default_limit(state.mode)) - state.new_shown_count)
        if allowed_new <= 0:
            return Response({"detail": "no_cards", "reason": "new_cap_reached"}, status=200)
        card = Flashcard.objects.filter(
            user=request.user, deck=deck, suspended=False, repetitions=0
        ).order_by("created_at").first()
        if not card:
            return Response({"detail": "no_cards"}, status=200)
        # Count it as a shown new card for today
        state.new_shown_on = now.date()
        state.new_shown_count += 1
        state.save(update_fields=["new_shown_on", "new_shown_count", "updated_at"])

    data = {
        "id": card.id,
        "front_es": card.front_text_es,
        "back_gn": card.back_text_gn,
        "notes": card.notes,
        "due_at": card.due_at.isoformat(),
        "interval_days": card.interval_days,
        "repetitions": card.repetitions,
        "ease_factor": round(card.ease_factor, 2),
        "ai_difficulty": round(card.ai_difficulty, 2),
        "half_life_days": round(card.half_life_days, 2),
    }
    return Response({"card": data}, status=200)

@login_required
@api_view(["POST"])
def api_srs_grade(request):
    s = SRSGradeSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    card = get_object_or_404(Flashcard, pk=s.validated_data["card_id"], user=request.user)
    rating = s.validated_data["rating"]

    state = _get_or_create_user_state(request.user, card.deck)
    interval, half_life, p0 = grade_and_schedule(card, state, rating)

    ReviewLog.objects.create(
        user=request.user, card=card, rating=rating,
        interval_before=card.interval_days, interval_after=interval,
        ef_before=card.ease_factor, ef_after=card.ease_factor,
    )

    return Response({
        "status": "ok",
        "next_due": card.due_at.isoformat(),
        "interval_days": interval,
        "half_life": round(half_life, 2),
        "pred_mastery": round(p0, 2),
    }, status=200)

@login_required
@api_view(["POST"])
def api_glossary_bulk_add(request):
    """
    Bulk add glossary items: { "items": [ {source_text_es, translated_text_gn, notes?}, ... ] }
    Also syncs SRS cards from the glossary.
    """
    s = BulkGlossaryListSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    items = s.validated_data["items"]

    created = 0
    for it in items:
        es = it["source_text_es"].strip()
        gn = it["translated_text_gn"].strip()
        notes = (it.get("notes") or "").strip()
        obj, made = GlossaryEntry.objects.get_or_create(
            user=request.user,
            source_text_es=es,
            translated_text_gn=gn,
            defaults={"notes": notes},
        )
        if made:
            created += 1

    # Ensure SRS cards exist for the new entries
    deck = _get_or_create_default_deck(request.user)
    _sync_cards_from_glossary(request.user, deck)

    return Response({"created": created}, status=201)

@login_required
def exercises_view(request):
  return render(request, "learning/exercises.html")

@login_required
def lessons_overview(request):
  # show all lessons grouped by order (basic/intermediate)
  lessons = Lesson.objects.filter(is_published=True).order_by("order")
  progress_map = {lp.lesson_id: lp for lp in UserLessonProgress.objects.filter(user=request.user)}
  return render(request, "learning/lessons_overview.html", {"lessons": lessons, "progress_map": progress_map})

@login_required
@api_view(["POST"])
def api_submit_dragdrop(request):
    s = DragDropSubmissionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(DragDropExercise, pk=s.validated_data["exercise_id"])
    submitted = [t.strip() for t in s.validated_data["order"]]
    correct = [t.strip() for t in (ex.correct_tokens or [])]
    total = max(1, len(correct))
    correct_pos = sum(1 for i in range(min(len(submitted), len(correct))) if submitted[i].lower() == correct[i].lower())
    score = (correct_pos / total) * 100.0
    is_correct = score >= 95.0
    _save_user_result(request.user, ex, score, is_correct)
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"score": score, "correct_positions": correct_pos, "total": total}, status=200)

@login_required
@api_view(["POST"])
def api_submit_listening(request):
    s = ListeningSubmissionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(ListeningExercise, pk=s.validated_data["exercise_id"])
    selected = s.validated_data["selected_key"].strip().upper()
    is_correct = (selected == ex.correct_key.strip().upper())
    score = 100.0 if is_correct else 0.0
    _save_user_result(request.user, ex, score, is_correct)
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"score": score, "is_correct": is_correct}, status=200)

@login_required
@api_view(["POST"])
def api_submit_translation(request):
    s = TranslationSubmissionSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(TranslationExercise, pk=s.validated_data["exercise_id"])
    from .services.scoring import levenshtein_ratio
    answer = s.validated_data["answer"].strip().lower()
    answers = [a.strip().lower() for a in (ex.acceptable_answers or [])]
    exact = any(answer == a for a in answers)
    if exact:
        score = 100.0; is_correct = True
    else:
        best = max((levenshtein_ratio(answer, a) for a in answers), default=0.0)
        score = best; is_correct = best >= 90.0
    _save_user_result(request.user, ex, score, is_correct)
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"score": score, "is_correct": is_correct}, status=200)

@login_required
@require_http_methods(["POST"])
def api_glossary_upload_audio(request, pk):
    entry = get_object_or_404(GlossaryEntry, pk=pk, user=request.user)
    f = request.FILES.get("audio")
    if not f:
        return Response({"detail": "No se envió archivo 'audio'."}, status=400)

    ct = (getattr(f, "content_type", "") or "").lower()
    ext = ".webm"
    if "wav" in ct: ext = ".wav"
    elif "ogg" in ct: ext = ".ogg"
    elif "mpeg" in ct or "mp3" in ct: ext = ".mp3"

    filename = f"gloss_{entry.id}_{int(time.time())}{ext}"
    entry.audio_pronunciation.save(filename, f, save=True)
    return Response({"url": entry.audio_pronunciation.url}, status=200)

def _pick_espeak_exe():
    return getattr(settings, "ESPEAK_NG_EXE", None) or shutil.which("espeak-ng") or shutil.which("espeak")

def _clean_text_for_tts(text: str, ensure_punct=True) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    t = t.replace("“","\"").replace("”","\"").replace("’","'").replace("‘","'")
    if ensure_punct and t and t[-1] not in ".!?…":
        t += "."
    return t

def tts_view(request):
    text = (request.GET.get("text") or "").strip()
    lang = (request.GET.get("lang") or "gn").strip().lower()
    preset = (request.GET.get("preset") or "").strip().lower() or None

    if not text:
        return HttpResponse("Missing text", status=400)
    if len(text) > 300:
        text = text[:300]

    exe = _pick_espeak_exe()
    if not exe:
        return JsonResponse({"error": "espeak-ng not found"}, status=501)

    # Config/preset (si usas settings TTS_ESPEAK_CONFIG; si no, valores por defecto)
    cfg_all = getattr(settings, "TTS_ESPEAK_CONFIG", {}) or {}
    base = dict(cfg_all.get("default", {}))
    base.update((cfg_all.get("lang_overrides", {}) or {}).get(lang, {}))
    if preset:
        base.update((cfg_all.get("presets", {}) or {}).get(preset, {}).get(lang, {}))

    voice = (base.get("voice") or lang)
    variant = base.get("variant") or None
    voice_tag = f"{voice}+{variant}" if variant else voice
    cleaned = _clean_text_for_tts(text, ensure_punct=bool(base.get("ensure_punct", True)))

    sig = f"{voice_tag}:{base.get('speed')}:{base.get('pitch')}:{base.get('amplitude')}:{base.get('gap')}:{cleaned}"
    h = hashlib.sha1(sig.encode("utf-8")).hexdigest()[:16]
    cache_dir = os.path.join(settings.MEDIA_ROOT, "tts-cache")
    os.makedirs(cache_dir, exist_ok=True)
    wav_path = os.path.join(cache_dir, f"{voice_tag}-{h}.wav")

    if not os.path.exists(wav_path):
        cmd = [
            exe,
            "-v", voice_tag,
            "-s", str(base.get("speed", 155)),
            "-p", str(base.get("pitch", 45)),
            "-a", str(base.get("amplitude", 160)),
            "-g", str(base.get("gap", 6)),
            "-w", wav_path,
            cleaned,
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            if voice_tag != voice:
                try:
                    subprocess.run([
                        exe, "-v", voice,
                        "-s", str(base.get("speed", 155)),
                        "-p", str(base.get("pitch", 45)),
                        "-a", str(base.get("amplitude", 160)),
                        "-g", str(base.get("gap", 6)),
                        "-w", wav_path,
                        cleaned,
                    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception:
                    return JsonResponse({"error": "TTS failed"}, status=500)
            else:
                return JsonResponse({"error": "TTS failed"}, status=500)

    return FileResponse(open(wav_path, "rb"), content_type="audio/wav")