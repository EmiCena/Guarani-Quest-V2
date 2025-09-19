# learning/models.py
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

User = get_user_model()


# ---------- Core lesson/content models ----------

class Lesson(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class LessonSection(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="sections")
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    reference_audio = models.FileField(upload_to="lesson_sections/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.lesson.title} - {self.title or 'section'}"


# ---------- Written exercises ----------

class FillBlankExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="fillblanks")
    prompt_text = models.TextField(help_text="Usa '____' para indicar el espacio en blanco.")
    correct_answer = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"FillBlank #{self.id} - Lesson {self.lesson_id}"


class MultipleChoiceExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="mcqs")
    question_text = models.TextField()
    # Expected JSON: [{"key":"A","text":"..."}, {"key":"B","text":"..."}]
    choices_json = models.JSONField()
    correct_key = models.CharField(max_length=10)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"MCQ #{self.id} - Lesson {self.lesson_id}"

    @property
    def normalized_choices(self):
        data = self.choices_json or []
        result = []
        for i, item in enumerate(data):
            if isinstance(item, dict):
                key = str(item.get("key") or item.get("value") or chr(65 + i))
                text = str(item.get("text") or item.get("label") or item.get("option") or "")
            else:
                key = chr(65 + i)
                text = str(item)
            result.append({"key": key, "text": text})
        return result


class MatchingExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="matchings")
    instructions = models.CharField(max_length=255, default="Relaciona las parejas")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Matching #{self.id} - Lesson {self.lesson_id}"


class MatchingPair(models.Model):
    exercise = models.ForeignKey(MatchingExercise, on_delete=models.CASCADE, related_name="pairs")
    left_text = models.CharField(max_length=255)
    right_text = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.left_text} ↔ {self.right_text}"


# ---------- Pronunciation ----------

class PronunciationExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="pronun_exercises")
    text_guarani = models.CharField(max_length=255)
    reference_audio = models.FileField(upload_to="pronunciation_refs/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Pronun #{self.id}: {self.text_guarani}"


# ---------- Glossary / dictionary ----------

class WordPhrase(models.Model):
    word_guarani = models.CharField(max_length=255)
    translation_es = models.CharField(max_length=255)
    audio_pronunciation = models.FileField(upload_to="dictionary_audio/", blank=True, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.word_guarani} — {self.translation_es}"


class GlossaryEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="glossary_entries")
    source_text_es = models.CharField(max_length=255)
    translated_text_gn = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.source_text_es} → {self.translated_text_gn}"


# ---------- User results / progress ----------

class UserExerciseResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exercise_results")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    exercise_object = GenericForeignKey("content_type", "object_id")

    score = models.FloatField(default=0.0)
    is_correct = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=1)
    last_submitted = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "content_type", "object_id")]


class PronunciationAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pronunciation_attempts")
    exercise = models.ForeignKey(PronunciationExercise, on_delete=models.CASCADE, related_name="attempts")
    expected_text = models.CharField(max_length=255)
    accuracy_score = models.FloatField(default=0.0)
    fluency_score = models.FloatField(default=0.0)
    completeness_score = models.FloatField(default=0.0)
    prosody_score = models.FloatField(default=0.0)
    audio_file = models.FileField(upload_to="pronunciation_attempts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UserLessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    written_score = models.FloatField(default=0.0)
    pronunciation_confidence = models.FloatField(default=0.0)
    progress_percent = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "lesson")]

    def __str__(self):
        return f"{self.user} - {self.lesson} - {self.progress_percent:.1f}%"


# ---------- SRS (Spaced Repetition) with AI scheduler ----------

class SRSDeck(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="srs_decks")
    name = models.CharField(max_length=120, default="Mi Glosario")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "name")]

    def __str__(self):
        return f"{self.user} — {self.name}"


class Flashcard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="flashcards")
    deck = models.ForeignKey(SRSDeck, on_delete=models.CASCADE, related_name="cards")
    front_text_es = models.CharField(max_length=255)
    back_text_gn = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    # Classic SRS fields
    due_at = models.DateTimeField(default=timezone.now)
    interval_days = models.PositiveIntegerField(default=0)
    ease_factor = models.FloatField(default=2.5)
    repetitions = models.PositiveIntegerField(default=0)
    lapses = models.PositiveIntegerField(default=0)
    suspended = models.BooleanField(default=False)

    # AI parameters
    ai_difficulty = models.FloatField(default=0.0)     # item difficulty (logit)
    half_life_days = models.FloatField(default=1.5)    # memory half-life (days)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "deck", "due_at"])]

    def __str__(self):
        return f"{self.front_text_es} → {self.back_text_gn}"


class ReviewLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="srs_reviews")
    card = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()  # 0..5
    reviewed_at = models.DateTimeField(auto_now_add=True)
    interval_before = models.PositiveIntegerField(default=0)
    interval_after = models.PositiveIntegerField(default=0)
    ef_before = models.FloatField(default=2.5)
    ef_after = models.FloatField(default=2.5)


class SRSUserState(models.Model):
    MODE_CHOICES = [
        ("beginner", "Beginner"),
        ("comfortable", "Comfortable"),
        ("aggressive", "Aggressive"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="srs_states")
    deck = models.ForeignKey(SRSDeck, on_delete=models.CASCADE, related_name="states")
    theta = models.FloatField(default=0.0)  # learner ability (logit)

    # Study-mode fields
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default="comfortable")
    new_limit = models.PositiveIntegerField(default=15)   # cap of new cards per day
    new_shown_on = models.DateField(null=True, blank=True)
    new_shown_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "deck")]

    def __str__(self):
        return f"{self.user} — {self.deck} — θ={self.theta:.2f} — mode={self.mode}"
    
# --- Nuevos ejercicios ---

class DragDropExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="dragdrops")
    prompt_text = models.CharField(max_length=255, help_text="Ej: Ordena la oración.")
    correct_tokens = models.JSONField(help_text="Lista de tokens en orden correcto, p.ej. ['Che','héra','María']")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"DragDrop #{self.id} - L{self.lesson_id}"

class ListeningExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="listenings")
    prompt_text = models.CharField(max_length=255, blank=True, default="")
    audio = models.FileField(upload_to="listening/", help_text="Audio estímulo (mp3/wav)")
    choices_json = models.JSONField(help_text='[{"key":"A","text":"..."}, ...]')
    correct_key = models.CharField(max_length=5)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Listening #{self.id} - L{self.lesson_id}"

class TranslationExercise(models.Model):
    DIRECTION = (
        ("es_gn", "Español → Guaraní"),
        ("gn_es", "Guaraní → Español"),
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="translations")
    prompt_text = models.CharField(max_length=255)
    direction = models.CharField(max_length=10, choices=DIRECTION, default="es_gn")
    acceptable_answers = models.JSONField(default=list, help_text='Lista de respuestas válidas/sinónimos')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Translation #{self.id} - L{self.lesson_id}"

# learning/models.py (solo la clase; el resto de tu archivo no cambia)
class GlossaryEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="glossary_entries")
    source_text_es = models.CharField(max_length=255)
    translated_text_gn = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    audio_pronunciation = models.FileField(upload_to="glossary_audio/", blank=True, null=True)  # nuevo
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.source_text_es} → {self.translated_text_gn}"