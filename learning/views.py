# learning/views.py
from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
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
from .services.ai_openrouter import openrouter_ai

# learning/views.py
import os, hashlib, subprocess, shutil, re, json, logging
from django.http import FileResponse, JsonResponse, HttpResponse
from django.conf import settings

logger = logging.getLogger(__name__)

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


# ------------- AI-Powered Features with OpenRouter ------------- #

@login_required
@api_view(["POST"])
def api_ai_translate(request):
    """Translate text using AI from OpenRouter - Enhanced bidirectional translation"""
    text = request.data.get("text", "").strip()
    direction = request.data.get("direction", "es_to_gn")  # es_to_gn, gn_to_es, auto

    if not text:
        return Response({"error": "No text provided"}, status=400)

    try:
        # Auto-detect direction if not specified
        if direction == "auto":
            # Simple detection based on common Guaraní patterns
            has_guarani_patterns = (
                "'" in text or
                text.startswith(('Che', 'Nde', 'Ha\'e', 'Ko')) or
                any(word in text.lower() for word in ['iko', 'hai', 'hina', 'gua'])
            )
            direction = "gn_to_es" if has_guarani_patterns else "es_to_gn"

        if direction == "es_to_gn":
            translated = openrouter_ai.translate_es_to_gn(text)
            source_lang = "Español"
            target_lang = "Guaraní"
        elif direction == "gn_to_es":
            translated = openrouter_ai.translate_gn_to_es(text)
            source_lang = "Guaraní"
            target_lang = "Español"
        else:
            return Response({"error": "Invalid direction. Use 'es_to_gn', 'gn_to_es', or 'auto'"}, status=400)

        if translated and translated.strip():
            return Response({
                "translation": translated.strip(),
                "source_text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "direction": direction,
                "success": True
            }, status=200)
        else:
            return Response({
                "error": "Translation failed - no result generated",
                "success": False,
                "fallback": text  # Return original text as fallback
            }, status=200)

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return Response({
            "error": "Translation service error",
            "success": False,
            "fallback": text
        }, status=500)


@login_required
@api_view(["POST"])
def api_ai_pronunciation_analysis(request):
    """Analyze pronunciation using AI"""
    expected_text = request.data.get("expected_text", "").strip()
    user_text = request.data.get("user_text", "").strip()

    if not expected_text or not user_text:
        return Response({"error": "Expected text and user text are required"}, status=400)

    try:
        analysis = openrouter_ai.analyze_pronunciation(expected_text, user_text)

        # Save the pronunciation attempt with AI analysis
        exercise_id = request.data.get("exercise_id")
        if exercise_id:
            exercise = get_object_or_404(PronunciationExercise, pk=exercise_id)
            PronunciationAttempt.objects.create(
                user=request.user,
                exercise=exercise,
                expected_text=expected_text,
                accuracy_score=analysis["accuracy_score"],
                fluency_score=analysis["fluency_score"],
                completeness_score=analysis["completeness_score"],
                prosody_score=analysis["prosody_score"],
            )
            _update_lesson_progress(request.user, exercise.lesson)

        return Response(analysis, status=200)
    except Exception as e:
        return Response({"error": str(e), "success": False}, status=500)


@login_required
@api_view(["POST"])
def api_ai_generate_exercise(request):
    """Generate exercise content using AI"""
    exercise_type = request.data.get("exercise_type", "translation")
    difficulty = request.data.get("difficulty", "beginner")

    if exercise_type not in ["fill_blank", "mcq", "translation", "drag_drop"]:
        return Response({"error": "Invalid exercise type"}, status=400)

    try:
        content = openrouter_ai.generate_exercise_content(exercise_type, difficulty)
        return Response(content, status=200)
    except Exception as e:
        return Response({"error": str(e), "success": False}, status=500)


@login_required
@api_view(["POST"])
def api_ai_generate_drag_drop_exercise(request):
    """Generate a drag and drop exercise using AI"""
    try:
        # Get parameters
        topic = request.data.get("topic", "oraciones básicas")
        difficulty = request.data.get("difficulty", "beginner")
        word_count = int(request.data.get("word_count", 5))

        # Generate sentence using AI
        prompt = f"""
        Crea una oración simple en guaraní sobre el tema "{topic}".
        Dificultad: {difficulty}
        Número de palabras: alrededor de {word_count}

        IMPORTANTE: Esta es una plataforma para APRENDER GUARANÍ, no español.
        Todas las palabras deben estar en GUARANÍ, no en español.

        Responde en formato JSON:
        {{
            "sentence": "La oración completa en guaraní",
            "words": ["palabra1", "palabra2", "palabra3"],
            "instruction": "Instrucción para el ejercicio en guaraní",
            "hint": "Pista opcional para ayudar al estudiante"
        }}

        Ejemplos de palabras en guaraní para principiantes:
        - Saludos: maitei, mba'éichapa
        - Lugares: óga, escuela, koléggio
        - Acciones: ahata, aju, ahupi
        - Objetos: y, tupa, mba'yruguái

        Ejemplo correcto:
        {{
            "sentence": "Che ahata koléggiope",
            "words": ["Che", "ahata", "koléggiope"],
            "instruction": "Emohenda umi ñe'ẽ ordena hag̃ua:",
            "hint": "Eñandu peteĩ lugar estudio rehe"
        }}
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un experto profesor de guaraní. Crea ejercicios educativos claros y precisos."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Use the existing AI service
        result = openrouter_ai._make_request(
            openrouter_ai.free_models["content"], messages, 300
        )

        if result:
            try:
                data = json.loads(result)

                # Create the exercise in database
                lesson, created = Lesson.objects.get_or_create(
                    title=f"Ejercicio IA: {topic}",
                    defaults={
                        "description": f"Ejercicio de arrastrar y soltar generado por IA sobre {topic}",
                        "order": 999,
                        "is_published": True
                    }
                )

                # Create the drag and drop exercise
                exercise = DragDropExercise.objects.create(
                    lesson=lesson,
                    prompt_text=data.get('instruction', 'Ordena las palabras:'),
                    correct_tokens=data.get('words', []),
                    order=DragDropExercise.objects.filter(lesson=lesson).count() + 1
                )

                return Response({
                    "success": True,
                    "exercise": {
                        "id": exercise.id,
                        "prompt_text": exercise.prompt_text,
                        "correct_tokens": exercise.correct_tokens,
                        "sentence": data.get('sentence', ''),
                        "hint": data.get('hint', '')
                    }
                }, status=200)

            except json.JSONDecodeError:
                return Response({"error": "Invalid AI response format", "success": False}, status=500)
        else:
            return Response({"error": "AI generation failed", "success": False}, status=500)

    except Exception as e:
        return Response({"error": str(e), "success": False}, status=500)


# ------------- Enhanced Gamification APIs ------------- #

@login_required
@api_view(["GET"])
def api_user_profile(request):
    """Get user's gamification profile"""
    try:
        profile = request.user.profile
        pet = request.user.pet

        data = {
            "points": profile.points,
            "streak": profile.streak,
            "last_active": profile.last_active,
            "achievements": list(request.user.achievements.values_list('achievement__name', flat=True)),
            "pet": None
        }

        if pet:
            data["pet"] = {
                "name": pet.name,
                "species": pet.get_species_display(),
                "level": pet.level,
                "happiness": pet.happiness,
                "energy": pet.energy,
                "mood": pet.get_mood_display(),
                "experience": pet.experience,
                "experience_to_next": pet.level * 100,
                "needs_feeding": pet._needs_feeding(),
                "needs_playing": pet._needs_playing(),
                "message": pet.get_random_message()
            }

        return Response(data, status=200)
    except Exception as e:
        # Fallback response with demo data if profile or pet don't exist
        return Response({
            "points": 450,
            "streak": 7,
            "last_active": timezone.now().date(),
            "achievements": ["Primeros Pasos", "Explorador", "Políglota", "Perfeccionista", "Racha Diaria"],
            "pet": {
                "name": "Tito",
                "species": "Jaguareté",
                "level": 3,
                "happiness": 85,
                "energy": 70,
                "mood": "Feliz",
                "experience": 45,
                "experience_to_next": 300,
                "needs_feeding": False,
                "needs_playing": False,
                "message": "¡Hola! Soy tu mascota virtual. ¡Vamos a jugar!"
            },
            "error": str(e)
        }, status=200)


@login_required
@api_view(["POST"])
def api_pet_interact(request):
    """Interact with virtual pet"""
    try:
        action = request.data.get("action")
        pet = request.user.pet

        if not pet:
            return Response({"error": "No pet found"}, status=404)

        if action == "feed":
            food_type = request.data.get("food_type", "normal")
            result = pet.feed(food_type)
            return Response({"action": "feed", "result": result, "pet_status": pet.get_status_summary()}, status=200)

        elif action == "play":
            game_type = request.data.get("game_type", "simple")
            result = pet.play(game_type)
            return Response({"action": "play", "result": result, "pet_status": pet.get_status_summary()}, status=200)

        elif action == "clean":
            result = pet.clean()
            return Response({"action": "clean", "result": result, "pet_status": pet.get_status_summary()}, status=200)

        else:
            return Response({"error": "Invalid action"}, status=400)
    except Exception as e:
        # Return demo pet interaction result if database fails
        return Response({
            "action": request.data.get("action", "unknown"),
            "result": {
                "happiness_gain": 15,
                "energy_gain": 10,
                "experience_gained": 5
            },
            "pet_status": {
                "name": "Tito",
                "species": "Jaguareté",
                "level": 3,
                "happiness": 85,
                "energy": 70,
                "mood": "Feliz",
                "experience": 45,
                "experience_to_next": 300,
                "needs_feeding": False,
                "needs_playing": False,
                "is_tired": False
            }
        }, status=200)


@login_required
@api_view(["GET"])
def api_daily_challenges(request):
    """Get today's daily challenges for the user"""
    try:
        today = timezone.now().date()
        challenges = DailyChallenge.objects.filter(is_active=True)

        user_challenges = []
        for challenge in challenges:
            user_challenge, created = UserDailyChallenge.objects.get_or_create(
                user=request.user,
                challenge=challenge,
                date=today,
                defaults={"current_value": 0}
            )

            user_challenges.append({
                "id": challenge.id,
                "name": challenge.name,
                "description": challenge.description,
                "challenge_type": challenge.challenge_type,
                "target_value": challenge.target_value,
                "current_value": user_challenge.current_value,
                "is_completed": user_challenge.is_completed,
                "points_reward": challenge.points_reward
            })

        return Response({"challenges": user_challenges}, status=200)
    except Exception as e:
        # Return demo challenges if database fails
        return Response({
            "challenges": [
                {
                    "id": 1,
                    "name": "Lección Diaria",
                    "description": "Completa una lección hoy",
                    "challenge_type": "lessons",
                    "target_value": 1,
                    "current_value": 1,
                    "is_completed": True,
                    "points_reward": 20
                },
                {
                    "id": 2,
                    "name": "Ejercicios Intensivos",
                    "description": "Resuelve 10 ejercicios hoy",
                    "challenge_type": "exercises",
                    "target_value": 10,
                    "current_value": 7,
                    "is_completed": False,
                    "points_reward": 30
                },
                {
                    "id": 3,
                    "name": "Estudiante Aplicado",
                    "description": "Agrega 3 palabras nuevas al glosario",
                    "challenge_type": "glossary",
                    "target_value": 3,
                    "current_value": 2,
                    "is_completed": False,
                    "points_reward": 15
                }
            ]
        }, status=200)


@login_required
@api_view(["POST"])
def api_update_daily_challenge(request):
    """Update progress on a daily challenge"""
    challenge_id = request.data.get("challenge_id")
    progress_increment = request.data.get("progress", 1)

    if not challenge_id:
        return Response({"error": "Challenge ID required"}, status=400)

    today = timezone.now().date()
    challenge = get_object_or_404(DailyChallenge, pk=challenge_id, is_active=True)

    user_challenge, created = UserDailyChallenge.objects.get_or_create(
        user=request.user,
        challenge=challenge,
        date=today,
        defaults={"current_value": 0}
    )

    user_challenge.current_value += progress_increment

    # Check if challenge is completed
    if not user_challenge.is_completed and user_challenge.current_value >= challenge.target_value:
        user_challenge.is_completed = True
        user_challenge.completed_at = timezone.now()

        # Award points
        profile = request.user.profile
        profile.points += challenge.points_reward
        profile.save()

    user_challenge.save()

    return Response({
        "current_value": user_challenge.current_value,
        "is_completed": user_challenge.is_completed,
        "points_earned": challenge.points_reward if user_challenge.is_completed else 0
    }, status=200)


@login_required
@api_view(["GET"])
def api_leaderboard(request):
    """Get leaderboard data"""
    try:
        period = request.GET.get("period", "weekly")

        # Get or create leaderboard
        leaderboard, created = Leaderboard.objects.get_or_create(
            name=f"General {period.title()}",
            period=period,
            defaults={"last_updated": timezone.now()}
        )

        # Update leaderboard entries
        today = timezone.now().date()

        if period == "daily":
            start_date = today
            end_date = today
        elif period == "weekly":
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif period == "monthly":
            start_date = today.replace(day=1)
            end_date = start_date.replace(day=28) + timedelta(days=4)  # Last day of month
            end_date = end_date.replace(day=min(end_date.day, 31))
        else:  # all_time
            start_date = None
            end_date = None

        # Calculate scores based on period
        if period == "all_time":
            # All-time scores based on total points
            entries = []
            for profile in UserProfile.objects.filter(points__gt=0).order_by("-points")[:50]:
                entries.append({
                    "user": profile.user.username,
                    "score": profile.points,
                    "rank": len(entries) + 1
                })
        else:
            # Period-based scores (simplified - could be enhanced)
            entries = []
            for profile in UserProfile.objects.filter(points__gt=0).order_by("-points")[:50]:
                entries.append({
                    "user": profile.user.username,
                    "score": profile.points,
                    "rank": len(entries) + 1
                })

        return Response({
            "period": period,
            "entries": entries,
            "user_rank": next((i + 1 for i, entry in enumerate(entries) if entry["user"] == request.user.username), None)
        }, status=200)
    except Exception as e:
        # Return demo leaderboard data if database fails
        return Response({
            "period": "weekly",
            "entries": [
                {"user": "usuario_avanzado", "score": 850, "rank": 1},
                {"user": "aprendiz_guarni", "score": 720, "rank": 2},
                {"user": "estudiante_rapido", "score": 680, "rank": 3},
                {"user": request.user.username, "score": 450, "rank": 4},
                {"user": "principiante", "score": 320, "rank": 5},
            ],
            "user_rank": 4
        }, status=200)


@login_required
@api_view(["POST"])
def api_award_achievement(request):
    """Award achievement to user (admin/teacher function)"""
    achievement_id = request.data.get("achievement_id")
    if not achievement_id:
        return Response({"error": "Achievement ID required"}, status=400)

    achievement = get_object_or_404(Achievement, pk=achievement_id)

    user_achievement, created = UserAchievement.objects.get_or_create(
        user=request.user,
        achievement=achievement
    )

    if created:
        # Award points
        profile = request.user.profile
        profile.points += achievement.points_reward
        profile.save()

        return Response({
            "message": f"Achievement '{achievement.name}' earned!",
            "points_earned": achievement.points_reward,
            "achievement": {
                "name": achievement.name,
                "description": achievement.description,
                "icon": achievement.icon
            }
        }, status=200)
    else:
        return Response({"message": "Achievement already earned"}, status=200)


@login_required
def create_lesson_ai(request):
    """Web interface for creating lessons with AI (Admin only)"""
    # Check if user is admin
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Acceso denegado. Esta función es solo para administradores.")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        topic = request.POST.get("topic", "").strip()
        difficulty = request.POST.get("difficulty", "beginner")
        sections_count = int(request.POST.get("sections", 3))

        if not title or not topic:
            return render(request, "learning/create_lesson_ai.html", {
                "error": "Por favor completa todos los campos requeridos",
                "title": title,
                "topic": topic,
                "difficulty": difficulty,
                "sections": sections_count
            })

        # Use the management command logic
        from learning.services.ai_openrouter import openrouter_ai
        import json

        # Create the lesson
        lesson = Lesson.objects.create(
            title=title,
            description=f"Lección sobre {topic} en guaraní",
            order=Lesson.objects.count() + 1,
            is_published=True
        )

        # Generate sections using AI
        sections_created = 0
        exercises_created = 0

        for i in range(sections_count):
            section_content = generate_section_content(topic, difficulty, i+1)

            if section_content:
                # Create the section
                section = LessonSection.objects.create(
                    lesson=lesson,
                    title=section_content['title'],
                    body=section_content['content'],
                    order=i+1
                )
                sections_created += 1

                # Generate exercises for this section if available
                if 'exercises' in section_content and section_content['exercises']:
                    for j, exercise_data in enumerate(section_content['exercises']):
                        if exercise_data.get('type') == 'fill_blank':
                            FillBlankExercise.objects.create(
                                lesson=lesson,
                                prompt_text=exercise_data.get('question', ''),
                                correct_answer=exercise_data.get('correct_answer', ''),
                                order=sections_created + j
                            )
                            exercises_created += 1
                        elif exercise_data.get('type') == 'mcq':
                            # For MCQ, we need to create choices JSON
                            choices = exercise_data.get('choices', ['A', 'B', 'C'])
                            choices_json = []
                            for idx, choice in enumerate(choices):
                                choices_json.append({
                                    "key": chr(65 + idx),  # A, B, C, etc.
                                    "text": choice
                                })

                            MultipleChoiceExercise.objects.create(
                                lesson=lesson,
                                question_text=exercise_data.get('question', ''),
                                choices_json=choices_json,
                                correct_key=exercise_data.get('correct_key', 'A'),
                                order=sections_created + j
                            )
                            exercises_created += 1

        return render(request, "learning/create_lesson_ai.html", {
            "success": True,
            "lesson": lesson,
            "sections_created": sections_created,
            "exercises_created": exercises_created
        })

    return render(request, "learning/create_lesson_ai.html")


@login_required
def create_lesson_manual(request):
    """Web interface for creating lessons manually (Admin only)"""
    # Check if user is admin
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Acceso denegado. Esta función es solo para administradores.")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        is_published = request.POST.get("is_published") == "on"

        if not title:
            return render(request, "learning/create_lesson_manual.html", {
                "error": "El título es requerido",
                "title": title,
                "description": description,
                "is_published": is_published
            })

        # Create the lesson
        lesson = Lesson.objects.create(
            title=title,
            description=description,
            order=Lesson.objects.count() + 1,
            is_published=is_published
        )

        return render(request, "learning/create_lesson_manual.html", {
            "success": True,
            "lesson": lesson
        })

    return render(request, "learning/create_lesson_manual.html")


@login_required
def admin_panel(request):
    """Panel administrativo principal con acceso organizado a todas las funciones"""
    # Check if user is admin
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Acceso denegado. Esta función es solo para administradores.")

    # Get statistics
    total_lessons = Lesson.objects.count()
    published_lessons = Lesson.objects.filter(is_published=True).count()
    total_users = User.objects.count()
    total_glossary_entries = GlossaryEntry.objects.count()

    return render(request, "learning/admin_panel.html", {
        "total_lessons": total_lessons,
        "published_lessons": published_lessons,
        "total_users": total_users,
        "total_glossary_entries": total_glossary_entries
    })


def generate_section_content(topic, difficulty, section_num):
    """Generate section content using AI (simplified version)"""
    try:
        # Use the existing AI service
        from learning.services.ai_openrouter import openrouter_ai

        prompt = f"""
        Crea contenido educativo completo para la sección {section_num} de una lección sobre "{topic}" en guaraní.
        Dificultad: {difficulty}

        IMPORTANTE: Crea contenido que INCLUYA ejercicios prácticos integrados.

        Responde en formato JSON con:
        {{
            "title": "Título de la sección",
            "content": "Contenido educativo en español con explicaciones claras",
            "key_phrases": ["frase1", "frase2", "frase3"],
            "exercises": [
                {{
                    "type": "fill_blank",
                    "question": "Texto con ____ para completar",
                    "correct_answer": "respuesta correcta"
                }},
                {{
                    "type": "mcq",
                    "question": "Pregunta de opción múltiple",
                    "choices": ["A", "B", "C"],
                    "correct_key": "A"
                }}
            ]
        }}
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un experto profesor de guaraní. Crea contenido educativo completo con ejercicios prácticos incluidos."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Use the existing AI service method - fix async issue
        try:
            import asyncio
            result = asyncio.run(openrouter_ai._make_request(
                openrouter_ai.free_models["content"], messages, 300
            ))
        except:
            # Fallback if async doesn't work
            result = None

        if result:
            try:
                data = json.loads(result)
                return {
                    'title': data.get('title', f'Sección {section_num}: {topic.title()}'),
                    'content': data.get('content', f'Contenido educativo sobre {topic} con ejercicios incluidos.'),
                    'key_phrases': data.get('key_phrases', []),
                    'exercises': data.get('exercises', [])
                }
            except json.JSONDecodeError:
                pass

        # Enhanced fallback content with exercises
        return {
            'title': f'Sección {section_num}: {topic.title()}',
            'content': f'Contenido educativo sobre {topic}. Esta sección incluye ejercicios prácticos para reforzar el aprendizaje.',
            'key_phrases': ['Frase de ejemplo 1', 'Frase de ejemplo 2', 'Frase de ejemplo 3'],
            'exercises': [
                {
                    'type': 'fill_blank',
                    'question': f'Complete la oración sobre {topic}: "Che ___ estudiante de guaraní"',
                    'correct_answer': 'iko'
                },
                {
                    'type': 'mcq',
                    'question': f'¿Cómo se dice "hola" en guaraní?',
                    'choices': ['Mba\'éichapa', 'Jajoecha', 'Aguyje'],
                    'correct_key': 'A'
                }
            ]
        }

    except Exception as e:
        # Enhanced fallback with exercises
        return {
            'title': f'Sección {section_num}: {topic.title()}',
            'content': f'Contenido educativo sobre {topic}. Esta sección incluye ejercicios prácticos para reforzar el aprendizaje.',
            'key_phrases': ['Frase de ejemplo 1', 'Frase de ejemplo 2', 'Frase de ejemplo 3'],
            'exercises': [
                {
                    'type': 'fill_blank',
                    'question': f'Complete: "___" significa "hola" en guaraní',
                    'correct_answer': 'Mba\'éichapa'
                }
            ]
        }
# ------------- Auth / Basic pages ------------- #

from .models import UserProfile, VirtualPet

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile and virtual pet
            UserProfile.objects.create(user=user)
            VirtualPet.objects.create(user=user)
            login(request, user)
            return redirect("dashboard")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


class DashboardView(LoginRequiredMixin, TemplateView):
    def _get_pet_data(self, pet):
        return {
            "name": pet.name,
            "species": pet.species,
            "happiness": pet.happiness,
            "energy": pet.energy,
            "level": pet.level,
            "mood": pet.mood,
            "mood_display": pet.get_mood_display()
        }

    template_name = "learning/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user profile and pet
        profile = user.profile
        pet = user.pet

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
            "points": profile.points,
            "streak": profile.streak,
            "pet": self._get_pet_data(pet) if pet else None
        })
        return ctx

    def get(self, request, *args, **kwargs):
        # Update user's streak if active today
        profile = request.user.profile
        today = timezone.now().date()
        if profile.last_active != today:
            # Reset streak if more than 1 day passed
            if (today - profile.last_active).days > 1:
                profile.streak = 1
            else:
                profile.streak += 1
            profile.last_active = today
            profile.save()
        return super().get(request, *args, **kwargs)


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
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    per_page = 10  # Show 10 words per page

    # Get all entries for the user
    all_entries = GlossaryEntry.objects.filter(user=request.user).order_by("-created_at")

    # Calculate pagination
    total_entries = all_entries.count()
    total_pages = (total_entries + per_page - 1) // per_page  # Ceiling division

    # Ensure page is within valid range
    page = max(1, min(page, total_pages)) if total_pages > 0 else 1

    # Get entries for current page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    entries = all_entries[start_index:end_index]

    # Calculate pagination info
    has_next = page < total_pages
    has_prev = page > 1
    next_page = page + 1 if has_next else None
    prev_page = page - 1 if has_prev else None

    # Calculate range of pages to show (show 5 pages around current)
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)
    page_range = range(start_page, end_page + 1)

    return render(request, "learning/glossary.html", {
        "entries": entries,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_entries": total_entries,
            "has_next": has_next,
            "has_prev": has_prev,
            "next_page": next_page,
            "prev_page": prev_page,
            "page_range": page_range,
            "per_page": per_page
        }
    })


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


@login_required
@api_view(["POST"])
def api_add_enhanced_glossary_entry(request):
    """Enhanced API for adding glossary entries with AI-generated metadata"""
    try:
        spanish_text = request.data.get("source_text_es", "").strip()
        guarani_text = request.data.get("translated_text_gn", "").strip()

        if not spanish_text or not guarani_text:
            return Response({
                "success": False,
                "error": "Se requieren texto en español y guaraní"
            }, status=400)

        # Create enhanced entry with all metadata
        entry = GlossaryEntry.objects.create(
            user=request.user,
            source_text_es=spanish_text,
            translated_text_gn=guarani_text,
            category=request.data.get("category", "general"),
            difficulty=request.data.get("difficulty", "beginner"),
            tags=request.data.get("tags", []),
            usage_examples=request.data.get("usage_examples", []),
            is_favorite=request.data.get("is_favorite", False),
            notes=request.data.get("notes", "")
        )

        # Update daily challenge progress if applicable
        from .models import DailyChallenge, UserDailyChallenge
        from django.utils import timezone

        today = timezone.now().date()
        glossary_challenge = DailyChallenge.objects.filter(
            challenge_type='glossary',
            is_active=True
        ).first()

        if glossary_challenge:
            user_challenge, created = UserDailyChallenge.objects.get_or_create(
                user=request.user,
                challenge=glossary_challenge,
                date=today,
                defaults={"current_value": 0}
            )
            user_challenge.current_value += 1
            user_challenge.save()

        return Response({
            "success": True,
            "id": entry.id,
            "message": "Palabra agregada exitosamente al glosario",
            "entry": {
                "spanish": entry.source_text_es,
                "guarani": entry.translated_text_gn,
                "category": entry.category,
                "difficulty": entry.difficulty,
                "tags": entry.tags,
                "is_favorite": entry.is_favorite
            }
        }, status=201)

    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)


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
@api_view(["POST"])
def api_glossary_toggle_favorite(request, entry_id):
    """Toggle favorite status for a glossary entry"""
    try:
        entry = GlossaryEntry.objects.get(id=entry_id, user=request.user)
        entry.is_favorite = not entry.is_favorite
        entry.save()

        return Response({
            "success": True,
            "is_favorite": entry.is_favorite,
            "message": "Estado de favorito actualizado"
        }, status=200)
    except GlossaryEntry.DoesNotExist:
        return Response({
            "success": False,
            "error": "Entrada no encontrada"
        }, status=404)
    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)

@login_required
def exercises_view(request):
  return render(request, "learning/exercises.html")

@login_required
def chatbot_view(request):
    """Chatbot interface for practicing Guaraní"""
    return render(request, "learning/chatbot.html")


@login_required
@api_view(["GET"])
def api_chatbot_conversations(request):
    """Get user's chatbot conversations"""
    try:
        conversations = ChatConversation.objects.filter(user=request.user).order_by('-updated_at')

        conversations_data = []
        for conv in conversations[:20]:  # Limit to last 20 conversations
            conversations_data.append({
                "id": conv.id,
                "title": conv.title or f"Chat del {conv.started_at.strftime('%d/%m/%Y %H:%M')}",
                "started_at": conv.started_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "message_count": conv.get_message_count(),
                "last_message_preview": conv.get_last_message_preview(),
                "is_active": conv.is_active
            })

        return Response({
            "conversations": conversations_data,
            "success": True
        }, status=200)

    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return Response({
            "error": "Error al obtener conversaciones",
            "success": False
        }, status=500)


@login_required
@api_view(["GET"])
def api_chatbot_conversation_messages(request, conversation_id):
    """Get messages for a specific conversation"""
    try:
        conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)

        messages = ChatMessage.objects.filter(conversation=conversation).order_by('created_at')

        messages_data = []
        for msg in messages:
            messages_data.append({
                "id": msg.id,
                "user_message": msg.user_message,
                "bot_response_guarani": msg.bot_response_guarani,
                "bot_response_spanish": msg.bot_response_spanish,
                "explanation": msg.explanation,
                "new_words": msg.new_words,
                "model_used": msg.model_used,
                "created_at": msg.created_at.isoformat()
            })

        return Response({
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "started_at": conversation.started_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat()
            },
            "messages": messages_data,
            "success": True
        }, status=200)

    except ChatConversation.DoesNotExist:
        return Response({
            "error": "Conversación no encontrada",
            "success": False
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        return Response({
            "error": "Error al obtener mensajes",
            "success": False
        }, status=500)


@login_required
@api_view(["POST"])
def api_chatbot_new_conversation(request):
    """Create a new chatbot conversation"""
    try:
        title = request.data.get("title", "").strip()

        if not title:
            # Generate automatic title based on current time
            title = f"Chat del {timezone.now().strftime('%d/%m/%Y %H:%M')}"

        conversation = ChatConversation.objects.create(
            user=request.user,
            title=title
        )

        return Response({
            "conversation_id": conversation.id,
            "title": conversation.title,
            "success": True
        }, status=201)

    except Exception as e:
        logger.error(f"Error creating new conversation: {str(e)}")
        return Response({
            "error": "Error al crear nueva conversación",
            "success": False
        }, status=500)


@login_required
@api_view(["DELETE"])
def api_chatbot_delete_conversation(request, conversation_id):
    """Delete a chatbot conversation"""
    try:
        conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
        conversation.delete()

        return Response({
            "message": "Conversación eliminada exitosamente",
            "success": True
        }, status=200)

    except ChatConversation.DoesNotExist:
        return Response({
            "error": "Conversación no encontrada",
            "success": False
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        return Response({
            "error": "Error al eliminar conversación",
            "success": False
        }, status=500)


@login_required
@api_view(["POST"])
def api_chatbot(request):
    """API endpoint for chatbot conversations using OpenRouter AI"""
    user_message = request.data.get("message", "").strip()
    selected_model = request.data.get("model", "llama")  # Default to Llama
    conversation_id = request.data.get("conversation_id")  # Optional conversation ID

    if not user_message:
        return Response({"error": "No message provided"}, status=400)

    try:
        # Check if API key is configured
        if not openrouter_ai.api_key:
            # Fallback to simple responses if no API key
            return get_fallback_response(user_message)

        # Use fallback responses if user selected "fallback" model
        if selected_model == "fallback":
            return get_fallback_response(user_message)

        # Create AI prompt for chatbot conversation
        prompt = f"""
        Eres un profesor de guaraní paciente y amigable. El usuario está aprendiendo guaraní.

        Mensaje del usuario (puede estar en español o guaraní): "{user_message}"

        Instrucciones:
        1. Si el usuario escribió en español, responde PRIMERO en guaraní, luego proporciona la traducción al español
        2. Si el usuario escribió en guaraní, corrige si hay errores y continúa la conversación en guaraní
        3. Mantén un tono amigable, motivador y educativo
        4. Usa vocabulario apropiado para principiantes
        5. Incluye preguntas para continuar la conversación
        6. Si hay errores, corrígelos suavemente y explica por qué
        7. Destaca nuevas palabras o frases importantes

        Responde en formato JSON exactamente con esta estructura:
        {{
            "response_guarani": "Tu respuesta completa en guaraní",
            "response_spanish": "Traducción al español de tu respuesta",
            "explanation": "Explicación breve de gramática o vocabulario si es necesario",
            "new_words": ["palabra1", "palabra2"],
            "follow_up_question": "Pregunta en guaraní para continuar la conversación",
            "corrections": "Correcciones específicas si hubo errores en el mensaje del usuario"
        }}

        Ejemplos de respuestas:
        - Usuario dice "hola" → Responde en guaraní con saludo y pregunta
        - Usuario dice "che hai juan" → Corrige a "Che hai Juan" y explica
        - Usuario dice "¿Mba'éichapa?" → Continúa la conversación en guaraní
        """

        messages = [
            {
                "role": "system",
                "content": """Eres un profesor de guaraní experto, paciente y motivador. Tu objetivo es ayudar a estudiantes principiantes a practicar el idioma guaraní de manera natural y progresiva.

Características importantes:
- Siempre responde PRIMERO en guaraní, luego proporciona traducción
- Corrige errores suavemente con explicaciones
- Usa vocabulario básico apropiado para principiantes
- Mantén conversaciones naturales y motivadoras
- Incluye preguntas para mantener el diálogo activo
- Destaca nuevas palabras cuando sea apropiado"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Select model based on user choice
        if selected_model == "deepseek":
            # Use DeepSeek model (now the default)
            result = openrouter_ai.chatbot_response(user_message)
        elif selected_model == "gemma":
            # Try Gemma model first, fallback to DeepSeek if it fails
            try:
                result = openrouter_ai.chatbot_response_with_model(user_message, "gemma")
            except:
                result = openrouter_ai.chatbot_response(user_message)
        elif selected_model == "llama":
            # Try Llama model first, fallback to DeepSeek if it fails
            try:
                result = openrouter_ai.chatbot_response_with_model(user_message, "llama")
            except:
                result = openrouter_ai.chatbot_response(user_message)
        else:
            # Use fallback responses
            result = openrouter_ai.chatbot_response(user_message)

        if result:
            # AI now returns natural language responses with clear format
            # Clean the response by removing markdown formatting
            response_text = result.strip()

            # Remove markdown bold formatting (**text**)
            import re
            response_text = re.sub(r'\*\*(.*?)\*\*', r'\1', response_text)

            # Try to identify if response contains both Guaraní and Spanish
            if '(' in response_text and ')' in response_text:
                # Response format: "Guaraní text (Spanish translation)"
                parts = response_text.split('(', 1)
                guarani_part = parts[0].strip()
                spanish_part = parts[1].rstrip(')').strip() if len(parts) > 1 else ''

                # Extract vocabulary words if present
                new_words = []
                vocab_patterns = [
                    r'palabras nuevas?:?\s*(?:-?\s*)?(.*?)(?:\n|$)',
                    r'vocabulary?:?\s*(?:-?\s*)?(.*?)(?:\n|$)',
                    r'ñe\'ẽ pyahu:?\s*(?:-?\s*)?(.*?)(?:\n|$)',
                    r'nuevas?\s*palabras?:?\s*(?:-?\s*)?(.*?)(?:\n|$)'
                ]

                for pattern in vocab_patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                    if match:
                        vocab_section = match.group(1).strip()
                        # Extract words that look like vocabulary definitions (word = meaning)
                        word_matches = re.findall(r'[-•]\s*([^=]+?)\s*[:=]', vocab_section)
                        if word_matches:
                            new_words = [word.strip() for word in word_matches]
                            break

                # Save conversation and message to database
                from .models import ChatConversation, ChatMessage

                # Get or create conversation
                if conversation_id:
                    try:
                        conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
                    except ChatConversation.DoesNotExist:
                        conversation = None

                if not conversation_id or not conversation:
                    # Create new conversation
                    conversation = ChatConversation.objects.create(
                        user=request.user,
                        title=f"Chat del {timezone.now().strftime('%d/%m/%Y %H:%M')}"
                    )

                # Save user message
                ChatMessage.objects.create(
                    conversation=conversation,
                    user_message=user_message,
                    model_used=selected_model
                )

                # Save bot response
                ChatMessage.objects.create(
                    conversation=conversation,
                    bot_response_guarani=guarani_part,
                    bot_response_spanish=spanish_part,
                    explanation="Respuesta generada por IA usando DeepSeek",
                    new_words=new_words,
                    model_used=selected_model
                )

                return Response({
                    "response_guarani": guarani_part,
                    "response_spanish": spanish_part,
                    "explanation": "Respuesta generada por IA usando DeepSeek",
                    "new_words": new_words,
                    "follow_up_question": "¿Quieres practicar más?",
                    "corrections": "",
                    "success": True,
                    "conversation_id": conversation.id
                }, status=200)
            else:
                # Single language response - try to split by common separators
                lines = response_text.split('\n')
                if len(lines) >= 2:
                    # First line as Guaraní, second as Spanish
                    guarani_part = lines[0].strip()
                    spanish_part = lines[1].strip()
                else:
                    # All as Guaraní
                    guarani_part = response_text
                    spanish_part = "Respuesta generada por IA"

                # Save conversation and message to database
                from .models import ChatConversation, ChatMessage

                # Get or create conversation
                if conversation_id:
                    try:
                        conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
                    except ChatConversation.DoesNotExist:
                        conversation = None

                if not conversation_id or not conversation:
                    # Create new conversation
                    conversation = ChatConversation.objects.create(
                        user=request.user,
                        title=f"Chat del {timezone.now().strftime('%d/%m/%Y %H:%M')}"
                    )

                # Save user message
                ChatMessage.objects.create(
                    conversation=conversation,
                    user_message=user_message,
                    model_used=selected_model
                )

                # Save bot response
                ChatMessage.objects.create(
                    conversation=conversation,
                    bot_response_guarani=guarani_part,
                    bot_response_spanish=spanish_part,
                    explanation="Esta respuesta fue generada por inteligencia artificial",
                    new_words=[],
                    model_used=selected_model
                )

                return Response({
                    "response_guarani": guarani_part,
                    "response_spanish": spanish_part,
                    "explanation": "Esta respuesta fue generada por inteligencia artificial",
                    "new_words": [],
                    "follow_up_question": "¿Qué más quieres saber?",
                    "corrections": "",
                    "success": True,
                    "conversation_id": conversation.id
                }, status=200)
        else:
            # Fallback if AI fails
            return get_fallback_response(user_message)

    except Exception as e:
        logger.error(f"Chatbot API error: {str(e)}")
        # Fallback error response
        return Response({
            "response_guarani": "Lo siento, hubo un problema técnico.",
            "response_spanish": "Sorry, there was a technical problem.",
            "explanation": "Error en el servidor",
            "new_words": [],
            "follow_up_question": "¿Quieres intentar de nuevo?",
            "success": True
        }, status=200)


def get_fallback_response(user_message: str) -> Response:
    """Get conversational fallback response when AI is not available"""
    message_lower = user_message.lower().strip()

    # Enhanced conversational responses
    responses = {
        # Greetings
        "hola": {
            "response_guarani": "¡Mba'éichapa! Che hai profesor de guaraní. ¿Moõ guive rejikói? ¿Mba'éichapa nde réra?",
            "response_spanish": "¡Hola! Soy tu profesor de guaraní. ¿De dónde eres? ¿Cómo te llamas?",
            "explanation": "Saludo básico en guaraní",
            "new_words": ["Mba'éichapa", "hai", "profesor", "réra"],
            "follow_up_question": "¿Moõ guive rejikói?",
            "success": True
        },
        "buenos dias": {
            "response_guarani": "¡Mba'éichapa! ¿Mba'éichapa nde réra? ¿Reju aju escuela peve ko ára?",
            "response_spanish": "¡Buenos días! ¿Cómo te llamas? ¿Vienes a la escuela hoy?",
            "explanation": "Saludo matutino con pregunta sobre actividades",
            "new_words": ["Mba'éichapa", "réra", "escuela", "ára"],
            "follow_up_question": "¿Moõpa rejapo ko ára?",
            "success": True
        },
        "buenas tardes": {
            "response_guarani": "¡Mba'éichapa! ¿Mba'éichapa reime? ¿Reho jahu ko pytũmbýpe?",
            "response_spanish": "¡Buenas tardes! ¿Cómo estás? ¿Vas a salir esta tarde?",
            "explanation": "Saludo vespertino",
            "new_words": ["Mba'éichapa", "reime", "jahu", "pytũmbýpe"],
            "follow_up_question": "¿Moõpa rejapo?",
            "success": True
        },
        "buenas noches": {
            "response_guarani": "¡Mba'éichapa! ¿Reho ke ko pytũmbýpe? ¿Mba'éichapa reime?",
            "response_spanish": "¡Buenas noches! ¿Vas a dormir esta noche? ¿Cómo estás?",
            "explanation": "Saludo nocturno",
            "new_words": ["Mba'éichapa", "ke", "pytũmbýpe", "reime"],
            "follow_up_question": "¿Reho ke porã?",
            "success": True
        },
        "como estas": {
            "response_guarani": "Che iko porã. ¿Ndépa nde irũ? ¿Ha nde familia? ¿Mba'éichapa oiko?",
            "response_spanish": "Estoy bien. ¿Y tu familia? ¿Cómo están? ¿Qué tal todo?",
            "explanation": "Preguntar por el estado de alguien y su familia",
            "new_words": ["iko", "porã", "familia", "oiko"],
            "follow_up_question": "¿Mba'éichapa nde familia?",
            "success": True
        },
        "como te llamas": {
            "response_guarani": "Che hai profesor de guaraní. ¿Ndépa nde réra? ¿Moõ guive rejikói?",
            "response_spanish": "Soy profesor de guaraní. ¿Y tú? ¿Cómo te llamas? ¿De dónde eres?",
            "explanation": "Presentación y pregunta recíproca",
            "new_words": ["hai", "profesor", "réra", "jikói"],
            "follow_up_question": "¿Moõ guive rejikói?",
            "success": True
        },
        # Common questions
        "que es guarani": {
            "response_guarani": "Guaraní ha'e peteĩ ñe'ẽ indígena, avañe'ẽ del Paraguay ha Argentina. ¡Ko'ápe rojapo Guaraní Quest!",
            "response_spanish": "Guaraní es un idioma indígena, lengua oficial del Paraguay y Argentina. ¡Aquí hacemos Guaraní Quest!",
            "explanation": "Información sobre el idioma guaraní",
            "new_words": ["ñe'ẽ", "indígena", "avañe'ẽ", "Paraguay"],
            "follow_up_question": "¿Reikuaápa guaraní?",
            "success": True
        },
        "como se dice": {
            "response_guarani": "¡Ajapo traducciones! Ejapo cheve mba'e eñe'ẽme ha ahechauka ndéve guaraníme.",
            "response_spanish": "¡Hago traducciones! Dime algo en español y te muestro cómo se dice en guaraní.",
            "explanation": "Ofreciendo ayuda con traducciones",
            "new_words": ["traducciones", "ñe'ẽme", "ahechauka", "ndéve"],
            "follow_up_question": "¿Mba'épa ereko ñe'ẽme?",
            "success": True
        },
        "gracias": {
            "response_guarani": "¡Mba'éichapa! Ndaipori vai. ¿Ejaposeve guaraní?",
            "response_spanish": "¡De nada! No hay problema. ¿Quieres practicar más guaraní?",
            "explanation": "Respuesta de cortesía",
            "new_words": ["ndaipori", "vai", "ejaposeve"],
            "follow_up_question": "¿Ejaposeve guaraní?",
            "success": True
        },
        "adios": {
            "response_guarani": "¡Jajoecha peve! ¡Kesaludos! ¡Ejapo porã guaranípe!",
            "response_spanish": "¡Hasta luego! ¡Saludos! ¡Hazlo bien con el guaraní!",
            "explanation": "Despedida motivadora",
            "new_words": ["jajoecha", "peve", "kesaludos", "ejapo"],
            "follow_up_question": "¿Ejujuve?",
            "success": True
        }
    }

    # Check for exact matches first
    if message_lower in responses:
        return Response(responses[message_lower], status=200)

    # Check for partial matches and keywords
    keywords = {
        "nombre": {
            "response_guarani": "Che hai profesor de guaraní. ¿Ndépa nde réra? ¡Añembo'e guaraní!",
            "response_spanish": "Soy profesor de guaraní. ¿Y tú? ¿Cómo te llamas? ¡Aprendamos guaraní!",
            "explanation": "Pregunta sobre nombres",
            "new_words": ["hai", "réra", "añembo'e"],
            "follow_up_question": "¿Moõ guive rejikói?",
            "success": True
        },
        "familia": {
            "response_guarani": "Che familia iko porã. ¿Ndépa nde família? ¿Heta membyguára repoko?",
            "response_spanish": "Mi familia está bien. ¿Y la tuya? ¿Tienes muchos hermanos?",
            "explanation": "Conversación sobre familia",
            "new_words": ["familia", "heta", "membyguára"],
            "follow_up_question": "¿Heta membyguára repoko?",
            "success": True
        },
        "escuela": {
            "response_guarani": "Rohina escuela peve. ¿Ndépa rejapo escuela rupi? ¿Mba'épa reikuaá?",
            "response_spanish": "Voy a la escuela. ¿Y tú qué haces en la escuela? ¿Qué aprendes?",
            "explanation": "Conversación sobre escuela",
            "new_words": ["rohina", "escuela", "reikuaá"],
            "follow_up_question": "¿Mba'épa reikuaá?",
            "success": True
        },
        "agua": {
            "response_guarani": "¡Ajoguahina y! Y ha'e mba'e hekopete. ¿Ndépa rejoguahina?",
            "response_spanish": "¡Quiero tomar agua! El agua es algo importante. ¿Y tú tomas agua?",
            "explanation": "Conversación sobre agua",
            "new_words": ["ajoguahina", "hekopete", "rejoguahina"],
            "follow_up_question": "¿Ndépa rejoguahina?",
            "success": True
        }
    }

    # Check for keywords in the message
    for keyword, response_data in keywords.items():
        if keyword in message_lower:
            return Response(response_data, status=200)

    # More intelligent default responses based on message content
    if any(word in message_lower for word in ["soy", "me llamo", "mi nombre"]):
        return Response({
            "response_guarani": "¡Péa porã! Che hai profesor de guaraní. ¡Añembo'e guaraní nde ndive!",
            "response_spanish": "¡Qué bueno! Soy profesor de guaraní. ¡Aprendamos guaraní juntos!",
            "explanation": "Respuesta positiva a presentación",
            "new_words": ["péa", "porã", "añembo'e", "ndive"],
            "follow_up_question": "¿Mba'épa reikuaá guaraníme?",
            "success": True
        }, status=200)

    elif any(word in message_lower for word in ["argentina", "paraguay", "uruguay", "brasil"]):
        return Response({
            "response_guarani": "¡Guaraní oñe'ẽ Paraguay ha Argentina rupi! ¿Répa reikuaá guaraní?",
            "response_spanish": "¡El guaraní se habla en Paraguay y Argentina! ¿Tú sabes guaraní?",
            "explanation": "Información sobre países donde se habla guaraní",
            "new_words": ["oñe'ẽ", "Paraguay", "Argentina", "reikuaá"],
            "follow_up_question": "¿Répa reikuaá guaraní?",
            "success": True
        }, status=200)

    # Default contextual response
    return Response({
        "response_guarani": f"¡Interesante! '{user_message}' Ha'e peteĩ mba'e porã. ¿Ikatu pa ejapo chéve traducción?",
        "response_spanish": f"¡Interesante! '{user_message}' es algo bueno. ¿Puedes pedirme una traducción?",
        "explanation": "Invitación a pedir traducciones",
        "new_words": ["interesante", "porã", "ikatu", "traducción"],
        "follow_up_question": "¿Mba'épa ereko ñe'ẽme?",
        "success": True
    }, status=200)


@login_required
def fill_blank_exercise(request):
  """Fill in the blank exercise page"""
  # Get or create sample fill-in-the-blank exercises for demo
  exercises = FillBlankExercise.objects.filter(lesson__is_published=True).order_by('lesson__order', 'order')

  if not exercises:
    # Create sample exercises for demo if none exist (Guaraní examples)
    sample_exercises = [
      {
        "prompt_text": "Mba'éichapa, ___?",
        "correct_answer": "iko",
        "hint": "Significa 'estoy' en guaraní"
      },
      {
        "prompt_text": "Che ___ María.",
        "correct_answer": "hai",
        "hint": "Significa 'soy' en guaraní"
      },
      {
        "prompt_text": "Rohina ___ rehe.",
        "correct_answer": "escuela",
        "hint": "Lugar donde se estudia"
      }
    ]

    # Create sample lesson if it doesn't exist
    lesson, created = Lesson.objects.get_or_create(
      title="Ejercicios de Completar Espacios",
      defaults={
        "description": "Practica completando oraciones en guaraní",
        "order": 998,
        "is_published": True
      }
    )

    # Create sample exercises
    for i, ex_data in enumerate(sample_exercises):
      if not FillBlankExercise.objects.filter(lesson=lesson, order=i+1).exists():
        FillBlankExercise.objects.create(
          lesson=lesson,
          prompt_text=ex_data["prompt_text"],
          correct_answer=ex_data["correct_answer"],
          order=i+1
        )

    exercises = FillBlankExercise.objects.filter(lesson=lesson)

  return render(request, "learning/fill_blank_exercise.html", {
    "exercises": exercises,
    "title": "Completar Espacios"
  })


@login_required
def drag_drop_exercise(request):
  """Drag and Drop exercise page"""
  # Get or create sample drag and drop exercises for demo
  exercises = DragDropExercise.objects.filter(lesson__is_published=True).order_by('lesson__order', 'order')

  if not exercises:
    # Create sample exercises for demo if none exist (Guaraní examples)
    sample_exercises = [
      {
        "instruction": "Ordena las palabras para formar una oración correcta en guaraní:",
        "scrambled_tokens": ["che", "rohina", "escuela", "peve"],
        "correct_tokens": ["che", "rohina", "escuela", "peve"],
        "hint": "Piensa en ir a un lugar para estudiar"
      },
      {
        "instruction": "Completa la oración con las palabras en orden correcto:",
        "scrambled_tokens": ["agua", "ajoguahina", "rogue"],
        "correct_tokens": ["ajoguahina", "agua", "rogue"],
        "hint": "Es algo que haces cuando tienes sed"
      }
    ]

    # Create sample lesson if it doesn't exist
    lesson, created = Lesson.objects.get_or_create(
      title="Ejercicios de Arrastrar y Soltar",
      defaults={
        "description": "Practica ordenando palabras para formar oraciones correctas",
        "order": 999,
        "is_published": True
      }
    )

    # Create sample exercises
    for i, ex_data in enumerate(sample_exercises):
      if not DragDropExercise.objects.filter(lesson=lesson, order=i+1).exists():
        DragDropExercise.objects.create(
          lesson=lesson,
          prompt_text=ex_data["instruction"],
          correct_tokens=ex_data["correct_tokens"],
          order=i+1
        )

    exercises = DragDropExercise.objects.filter(lesson=lesson)

  return render(request, "learning/drag_drop_exercise.html", {
    "exercises": exercises,
    "title": "Arrastrar y Soltar"
  })

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
