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
    updated_at = models.DateTimeField(auto_now=True)

    # Enhanced fields for better organization
    category = models.CharField(max_length=50, blank=True, default='general')  # saludo, familia, escuela, etc.
    difficulty = models.CharField(max_length=20, choices=[
        ('beginner', 'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado')
    ], default='beginner')
    tags = models.JSONField(default=list, blank=True)  # ['importante', 'frecuente', 'formal']
    usage_examples = models.JSONField(default=list, blank=True)  # ['Che hai Juan', 'Mba'éichapa María']
    is_favorite = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)  # Para compartir palabras

    # Study and progress tracking
    last_reviewed = models.DateTimeField(null=True, blank=True)
    review_count = models.PositiveIntegerField(default=0)
    mastery_level = models.FloatField(default=0.0)  # 0-100 scale for better granularity
    study_streak = models.PositiveIntegerField(default=0)  # Racha de estudio para esta palabra
    next_review_date = models.DateTimeField(null=True, blank=True)  # Próxima fecha de revisión SRS

    # Statistics and analytics
    total_study_time = models.PositiveIntegerField(default=0)  # Tiempo total de estudio en segundos
    correct_attempts = models.PositiveIntegerField(default=0)
    incorrect_attempts = models.PositiveIntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)  # Tiempo promedio de respuesta en segundos

    # Audio and pronunciation
    audio_pronunciation = models.FileField(upload_to="glossary_audio/", blank=True, null=True)
    pronunciation_quality = models.FloatField(default=0.0)  # Calidad de pronunciación 0-1
    pronunciation_attempts = models.PositiveIntegerField(default=0)

    # Source and metadata
    source = models.CharField(max_length=100, blank=True)  # Fuente de la palabra (manual, AI, import, etc.)
    is_verified = models.BooleanField(default=False)  # Verificado por expertos

    # Study reminders and scheduling
    reminder_enabled = models.BooleanField(default=True)
    reminder_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Diario'),
        ('every_3_days', 'Cada 3 días'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('custom', 'Personalizado')
    ], default='every_3_days')
    custom_reminder_days = models.PositiveIntegerField(default=3)

    class Meta:
        ordering = ["-is_favorite", "-last_reviewed", "-created_at"]
        indexes = [
            models.Index(fields=["user", "category"]),
            models.Index(fields=["user", "difficulty"]),
            models.Index(fields=["user", "is_favorite"]),
            models.Index(fields=["user", "next_review_date"]),
            models.Index(fields=["is_public", "is_verified"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.source_text_es} → {self.translated_text_gn}"

    def save(self, *args, **kwargs):
        if not self.share_token and self.is_public:
            # Generate unique share token
            import secrets
            self.share_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def get_category_display(self):
        categories = {
            'saludo': 'Saludos',
            'familia': 'Familia',
            'escuela': 'Escuela',
            'comida': 'Comida',
            'lugares': 'Lugares',
            'numeros': 'Números',
            'colores': 'Colores',
            'general': 'General'
        }
        return categories.get(self.category, self.category.title())

    def get_difficulty_display(self):
        difficulties = {
            'beginner': 'Principiante',
            'intermediate': 'Intermedio',
            'advanced': 'Avanzado'
        }
        return difficulties.get(self.difficulty, self.difficulty.title())

    def update_mastery(self, correct=True, response_time=0.0):
        """Update mastery level based on performance"""
        if correct:
            self.correct_attempts += 1
            # Increase mastery based on current level and performance
            if self.mastery_level < 50:
                self.mastery_level = min(100, self.mastery_level + 15)
            elif self.mastery_level < 80:
                self.mastery_level = min(100, self.mastery_level + 10)
            else:
                self.mastery_level = min(100, self.mastery_level + 5)
        else:
            self.incorrect_attempts += 1
            # Decrease mastery but not too drastically
            self.mastery_level = max(0, self.mastery_level - 8)

        # Update average response time
        if response_time > 0:
            if self.average_response_time == 0:
                self.average_response_time = response_time
            else:
                self.average_response_time = (self.average_response_time + response_time) / 2

        self.last_reviewed = timezone.now()
        self.review_count += 1
        self.save(update_fields=['mastery_level', 'last_reviewed', 'review_count',
                                'correct_attempts', 'incorrect_attempts', 'average_response_time'])

    def get_next_review_date(self):
        """Calculate next review date using SRS algorithm"""
        if not self.last_reviewed:
            return timezone.now()

        # Simple SRS: increase interval based on mastery and ease factor
        base_interval = self.interval_days or 1

        if self.mastery_level >= 90:
            interval = base_interval * self.ease_factor * 3
        elif self.mastery_level >= 70:
            interval = base_interval * self.ease_factor * 2
        elif self.mastery_level >= 50:
            interval = base_interval * self.ease_factor * 1.5
        else:
            interval = max(1, base_interval * 0.8)  # Reduce interval for struggling words

        next_date = self.last_reviewed + timezone.timedelta(days=int(interval))
        return next_date

    def should_review_today(self):
        """Check if this word should be reviewed today"""
        if not self.next_review_date:
            return True
        return timezone.now().date() >= self.next_review_date.date()

    def get_study_stats(self):
        """Get comprehensive study statistics"""
        total_attempts = self.correct_attempts + self.incorrect_attempts
        accuracy = (self.correct_attempts / total_attempts * 100) if total_attempts > 0 else 0

        return {
            'total_attempts': total_attempts,
            'correct_attempts': self.correct_attempts,
            'incorrect_attempts': self.incorrect_attempts,
            'accuracy': round(accuracy, 1),
            'mastery_level': self.mastery_level,
            'study_streak': self.study_streak,
            'average_response_time': round(self.average_response_time, 2),
            'days_since_last_review': (timezone.now().date() - self.last_reviewed.date()).days if self.last_reviewed else None,
            'next_review_date': self.get_next_review_date(),
            'should_review_today': self.should_review_today()
        }


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




# --- Gamification and Mascot Models ---

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    points = models.PositiveIntegerField(default=0)
    streak = models.PositiveIntegerField(default=0)
    last_active = models.DateField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    points_reward = models.PositiveIntegerField(default=50)
    icon = models.CharField(max_length=50, default='🏆')
    
    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'achievement')]

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"

class DailyChallenge(models.Model):
    CHALLENGE_TYPES = [
        ('lessons', 'Completar lecciones'),
        ('exercises', 'Resolver ejercicios'),
        ('streak', 'Mantener racha'),
        ('pronunciation', 'Practicar pronunciación'),
        ('glossary', 'Agregar palabras al glosario'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    challenge_type = models.CharField(max_length=20, choices=CHALLENGE_TYPES)
    target_value = models.PositiveIntegerField(default=1)
    points_reward = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_challenge_type_display()})"

class UserDailyChallenge(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_challenges')
    challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    current_value = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [('user', 'challenge', 'date')]

    def __str__(self):
        return f"{self.user.username} - {self.challenge.name} - {self.date}"

class Leaderboard(models.Model):
    PERIOD_CHOICES = [
        ('daily', 'Diario'),
        ('weekly', 'Semanal'),
        ('monthly', 'Mensual'),
        ('all_time', 'Todo el tiempo'),
    ]

    name = models.CharField(max_length=100)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='weekly')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_period_display()})"

class LeaderboardEntry(models.Model):
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(default=0)
    period_start = models.DateField()
    period_end = models.DateField()

    class Meta:
        unique_together = [('leaderboard', 'user', 'period_start', 'period_end')]
        ordering = ['-score', 'user__username']

    def __str__(self):
        return f"{self.user.username} - {self.score} puntos"

class VirtualPet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pet')
    name = models.CharField(max_length=50, default='Karai')
    species = models.CharField(max_length=50, default='Jaguareté')
    happiness = models.PositiveSmallIntegerField(default=50)  # 0-100
    energy = models.PositiveSmallIntegerField(default=70)     # 0-100
    level = models.PositiveSmallIntegerField(default=1)
    experience = models.PositiveIntegerField(default=0)      # XP for leveling up
    last_interaction = models.DateTimeField(auto_now=True)
    last_fed = models.DateTimeField(null=True, blank=True)
    last_played = models.DateTimeField(null=True, blank=True)
    last_cleaned = models.DateTimeField(null=True, blank=True)

    MOOD_CHOICES = [
        ('happy', 'Feliz'),
        ('sad', 'Triste'),
        ('tired', 'Cansado'),
        ('hungry', 'Hambriento'),
        ('bored', 'Aburrido'),
        ('excited', 'Emocionado'),
        ('sleepy', 'Somnoliento'),
    ]
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, default='happy')

    PET_SPECIES = [
        ('jaguarete', 'Jaguareté'),
        ('tucán', 'Tucán'),
        ('capibara', 'Capibara'),
        ('mariposa', 'Mariposa'),
        ('mono', 'Mono'),
    ]
    species = models.CharField(max_length=20, choices=PET_SPECIES, default='jaguarete')

    def __str__(self):
        return f"{self.name} ({self.species}) - {self.user.username}'s pet"

    def update_mood(self):
        """Update pet mood based on current stats and time since last interaction"""
        now = timezone.now()

        # Base mood on happiness and energy
        if self.happiness >= 80 and self.energy >= 60:
            if self.energy >= 80:
                self.mood = 'excited'
            else:
                self.mood = 'happy'
        elif self.happiness <= 30:
            self.mood = 'sad'
        elif self.energy <= 30:
            self.mood = 'tired'
        elif self.energy <= 20:
            self.mood = 'sleepy'
        else:
            # Check if needs care
            hours_since_fed = None
            if self.last_fed:
                hours_since_fed = (now - self.last_fed).total_seconds() / 3600

            if hours_since_fed and hours_since_fed > 6:
                self.mood = 'hungry'
            else:
                self.mood = 'bored'

        self.save(update_fields=['mood'])

    def feed(self, food_type='normal'):
        """Feed the pet to increase happiness and energy"""
        from random import randint

        # Different food types give different benefits
        multipliers = {
            'normal': 1.0,
            'treat': 1.5,
            'deluxe': 2.0
        }

        multiplier = multipliers.get(food_type, 1.0)

        happiness_gain = int(15 * multiplier)
        energy_gain = int(10 * multiplier)

        self.happiness = min(100, self.happiness + happiness_gain)
        self.energy = min(100, self.energy + energy_gain)
        self.last_fed = timezone.now()

        # Give experience for caring
        self.experience += int(5 * multiplier)

        self.save()
        self.update_mood()
        self.check_level_up()

        return {
            'happiness_gain': happiness_gain,
            'energy_gain': energy_gain,
            'experience_gained': int(5 * multiplier)
        }

    def play(self, game_type='simple'):
        """Play with the pet to increase happiness and gain experience"""
        from random import randint

        # Different games give different benefits
        multipliers = {
            'simple': 1.0,
            'fun': 1.5,
            'challenging': 2.0
        }

        multiplier = multipliers.get(game_type, 1.0)

        happiness_gain = int(20 * multiplier)
        energy_loss = int(15 * multiplier)
        experience_gain = int(10 * multiplier)

        self.happiness = min(100, self.happiness + happiness_gain)
        self.energy = max(0, self.energy - energy_loss)
        self.last_played = timezone.now()
        self.experience += experience_gain

        self.save()
        self.update_mood()
        self.check_level_up()

        return {
            'happiness_gain': happiness_gain,
            'energy_loss': energy_loss,
            'experience_gained': experience_gain
        }

    def clean(self):
        """Clean the pet to increase happiness"""
        happiness_gain = 10
        self.happiness = min(100, self.happiness + happiness_gain)
        self.last_cleaned = timezone.now()
        self.experience += 3

        self.save()
        self.update_mood()
        self.check_level_up()

        return {
            'happiness_gain': happiness_gain,
            'experience_gained': 3
        }

    def check_level_up(self):
        """Check if pet should level up based on experience"""
        exp_needed = self.level * 100  # 100 XP per level

        if self.experience >= exp_needed:
            self.level += 1
            self.experience = 0  # Reset XP for next level
            self.save()
            return True
        return False

    def get_status_summary(self):
        """Get a summary of the pet's current status"""
        return {
            'name': self.name,
            'species': self.get_species_display(),
            'level': self.level,
            'happiness': self.happiness,
            'energy': self.energy,
            'mood': self.get_mood_display(),
            'experience': self.experience,
            'experience_to_next': self.level * 100,
            'last_interaction': self.last_interaction,
            'needs_feeding': self._needs_feeding(),
            'needs_playing': self._needs_playing(),
            'is_tired': self.energy < 30,
        }

    def _needs_feeding(self):
        """Check if pet needs feeding"""
        if not self.last_fed:
            return True

        hours_since_fed = (timezone.now() - self.last_fed).total_seconds() / 3600
        return hours_since_fed > 4  # Needs feeding every 4 hours

    def _needs_playing(self):
        """Check if pet needs playing"""
        if not self.last_played:
            return True

        hours_since_played = (timezone.now() - self.last_played).total_seconds() / 3600
        return hours_since_played > 6  # Needs playing every 6 hours

    def get_random_message(self):
        """Get a random message from the pet based on its mood"""
        messages = {
            'happy': [
                f"¡{self.name} está muy feliz de verte!",
                f"{self.name} ronronea contento mientras te saluda.",
                f"¡{self.name} te mira con ojos brillantes de alegría!",
            ],
            'excited': [
                f"¡{self.name} está súper emocionado!",
                f"{self.name} salta de alegría al verte.",
                f"¡{self.name} no cabe en sí de la emoción!",
            ],
            'sad': [
                f"{self.name} parece un poco triste hoy.",
                f"{self.name} necesita un poco de atención.",
                f"{self.name} te mira con ojos suplicantes.",
            ],
            'hungry': [
                f"{self.name} tiene hambre y te mira expectante.",
                f"{self.name} olfatea el aire buscando comida.",
                f"¡{self.name} quiere un bocadillo!",
            ],
            'tired': [
                f"{self.name} bosteza y parece cansado.",
                f"{self.name} se acurruca buscando descanso.",
                f"{self.name} necesita una siesta.",
            ],
            'bored': [
                f"{self.name} parece aburrido y busca diversión.",
                f"{self.name} te mira esperando que juegues con él.",
                f"¡{self.name} quiere jugar!",
            ],
            'sleepy': [
                f"{self.name} tiene mucho sueño.",
                f"{self.name} se frota los ojos somnoliento.",
                f"{self.name} necesita dormir un poco.",
            ],
        }

        import random
        mood_messages = messages.get(self.mood, messages['happy'])
        return random.choice(mood_messages)
