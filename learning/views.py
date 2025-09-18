# learning/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import TemplateView
from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Q
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .forms import SignUpForm
from .models import (
    Lesson, LessonSection,
    FillBlankExercise, MultipleChoiceExercise, MatchingExercise, MatchingPair,
    PronunciationExercise, GlossaryEntry, WordPhrase,
    UserExerciseResult, PronunciationAttempt, UserLessonProgress
)
from .serializers import (
    FillBlankSubmissionSerializer, MCQSubmissionSerializer, MatchingSubmissionSerializer,
    PronunciationAttemptSerializer, TranslationRequestSerializer, GlossaryEntrySerializer
)
from .services.translation import translate_es_to_gn
from .services.azure_speech import issue_azure_speech_token
from .services.scoring import levenshtein_ratio

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
        lessons = Lesson.objects.filter(is_published=True).order_by("order")
        progress_map = {lp.lesson_id: lp for lp in UserLessonProgress.objects.filter(user=user)}
        ctx["lessons"] = lessons
        ctx["progress_map"] = progress_map
        ctx["glossary_count"] = GlossaryEntry.objects.filter(user=user).count()
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

@login_required
@api_view(["POST"])
def api_translate_and_add(request):
    serializer = TranslationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    text_es = serializer.validated_data["source_text_es"]
    translated = translate_es_to_gn(text_es)
    entry = GlossaryEntry.objects.create(
        user=request.user, source_text_es=text_es, translated_text_gn=translated
    )
    return Response({"id": entry.id, "translated_text_gn": translated}, status=200)

@login_required
@api_view(["POST"])
def api_add_glossary_entry(request):
    serializer = GlossaryEntrySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    entry = GlossaryEntry.objects.create(
        user=request.user,
        source_text_es=serializer.validated_data["source_text_es"],
        translated_text_gn=serializer.validated_data["translated_text_gn"],
        notes=serializer.validated_data.get("notes", ""),
    )
    return Response({"id": entry.id}, status=201)

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
    is_correct = (selected == ex.correct_key.strip().upper())
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
    correct_map = {(p.left_text.strip().lower()): p.right_text.strip().lower() for p in ex.pairs.all()}
    total = len(correct_map) or 1
    correct_count = 0
    for item in submitted_pairs:
        left = item.get("left", "").strip().lower()
        right = item.get("right", "").strip().lower()
        if correct_map.get(left) == right:
            correct_count += 1
    score = (correct_count / total) * 100.0
    is_correct = score >= 100.0
    _save_user_result(request.user, ex, score, is_correct)
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"score": score, "correct": correct_count, "total": total}, status=200)

@login_required
@api_view(["POST"])
def api_save_pronunciation_attempt(request):
    s = PronunciationAttemptSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    ex = get_object_or_404(PronunciationExercise, pk=s.validated_data["exercise_id"])
    attempt = PronunciationAttempt.objects.create(
        user=request.user,
        exercise=ex,
        expected_text=s.validated_data["expected_text"],
        accuracy_score=s.validated_data["accuracy_score"],
        fluency_score=s.validated_data["fluency_score"],
        completeness_score=s.validated_data["completeness_score"],
        prosody_score=s.validated_data.get("prosody_score", 0.0),
    )
    _update_lesson_progress(request.user, ex.lesson)
    return Response({"id": attempt.id}, status=201)

@login_required
@api_view(["GET"])
def api_azure_token(request):
    try:
        token = issue_azure_speech_token()
        from django.conf import settings
        return Response({"token": token, "region": settings.AZURE_SPEECH_REGION}, status=200)
    except Exception as e:
        return Response({"detail": str(e)}, status=500)

def _save_user_result(user, exercise_obj, score: float, is_correct: bool):
    ct = ContentType.objects.get_for_model(type(exercise_obj))
    obj, created = UserExerciseResult.objects.get_or_create(
        user=user, content_type=ct, object_id=exercise_obj.id,
        defaults={"score": score, "is_correct": is_correct, "attempts": 1}
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
        pronun_avg = sum(best_per_ex)/len(best_per_ex) if best_per_ex else 0.0
    else:
        pronun_avg = 0.0

    progress_percent = 0.5 * written_avg + 0.5 * pronun_avg

    obj, _ = UserLessonProgress.objects.get_or_create(user=user, lesson=lesson)
    obj.written_score = written_avg
    obj.pronunciation_confidence = pronun_avg
    obj.progress_percent = progress_percent
    obj.completed = progress_percent >= 90.0
    obj.save()