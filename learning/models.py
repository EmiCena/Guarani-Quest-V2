# learning/models.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

User = get_user_model()

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

class FillBlankExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="fillblanks")
    prompt_text = models.TextField(help_text="Use '____' to indicate the blank.")
    correct_answer = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"FillBlank #{self.id} - Lesson {self.lesson_id}"

class MultipleChoiceExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="mcqs")
    question_text = models.TextField()
    choices_json = models.JSONField()
    correct_key = models.CharField(max_length=10)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"MCQ #{self.id} - Lesson {self.lesson_id}"

class MatchingExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="matchings")
    instructions = models.CharField(max_length=255, default="Match the pairs")
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

class PronunciationExercise(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="pronun_exercises")
    text_guarani = models.CharField(max_length=255)
    reference_audio = models.FileField(upload_to="pronunciation_refs/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Pronun #{self.id}: {self.text_guarani}"

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