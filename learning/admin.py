# learning/admin.py
from django.contrib import admin
from .models import (
    Lesson, LessonSection,
    FillBlankExercise, MultipleChoiceExercise, MatchingExercise, MatchingPair,
    PronunciationExercise, WordPhrase, GlossaryEntry,
    UserExerciseResult, PronunciationAttempt, UserLessonProgress
)

class LessonSectionInline(admin.TabularInline):
    model = LessonSection
    extra = 1

class FillBlankInline(admin.TabularInline):
    model = FillBlankExercise
    extra = 1

class MCQInline(admin.TabularInline):
    model = MultipleChoiceExercise
    extra = 1

class PronunInline(admin.TabularInline):
    model = PronunciationExercise
    extra = 1

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_published")
    list_editable = ("order", "is_published")
    inlines = [LessonSectionInline, FillBlankInline, MCQInline, PronunInline]

class MatchingPairInline(admin.TabularInline):
    model = MatchingPair
    extra = 2

@admin.register(MatchingExercise)
class MatchingExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "order")
    inlines = [MatchingPairInline]

@admin.register(FillBlankExercise)
class FillBlankExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "order", "correct_answer")
    list_editable = ("order",)

@admin.register(MultipleChoiceExercise)
class MultipleChoiceExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "order", "correct_key")
    list_editable = ("order",)

@admin.register(PronunciationExercise)
class PronunciationExerciseAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "text_guarani", "order")
    list_editable = ("order",)

@admin.register(WordPhrase)
class WordPhraseAdmin(admin.ModelAdmin):
    list_display = ("word_guarani", "translation_es")
    search_fields = ("word_guarani", "translation_es")

@admin.register(GlossaryEntry)
class GlossaryEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "source_text_es", "translated_text_gn", "created_at")
    search_fields = ("source_text_es", "translated_text_gn")
    list_filter = ("user",)

@admin.register(UserExerciseResult)
class UserExerciseResultAdmin(admin.ModelAdmin):
    list_display = ("user", "content_type", "object_id", "score", "is_correct", "attempts", "last_submitted")
    list_filter = ("user", "content_type")

@admin.register(PronunciationAttempt)
class PronunciationAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "exercise", "accuracy_score", "fluency_score", "completeness_score", "created_at")
    list_filter = ("user", "exercise")

@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "written_score", "pronunciation_confidence", "progress_percent", "completed", "updated_at")
    list_filter = ("user", "lesson", "completed")