# learning/management/commands/populate_demo_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from learning.models import (
    Lesson, LessonSection, UserLessonProgress,
    GlossaryEntry, UserProfile, VirtualPet,
    Achievement, UserAchievement, DailyChallenge,
    UserDailyChallenge, Leaderboard, LeaderboardEntry,
    FillBlankExercise, MultipleChoiceExercise, PronunciationExercise
)
import random

class Command(BaseCommand):
    help = 'Populate database with demo data for gamification features'

    def handle(self, *args, **options):
        self.stdout.write('Populating demo data...')

        # Get or create demo user
        user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@guaraniquest.com',
                'first_name': 'Usuario',
                'last_name': 'Demo'
            }
        )
        if created:
            user.set_password('demo123')
            user.save()
            self.stdout.write('Created demo user: demo_user / demo123')

        # Update user profile with demo data
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'points': 0, 'streak': 0}
        )

        # Update streak and points
        today = timezone.now().date()
        profile.points = 450
        profile.streak = 7
        profile.last_active = today
        profile.save()

        # Update or create pet with demo data
        pet, created = VirtualPet.objects.get_or_create(
            user=user,
            defaults={
                'name': 'Tito',
                'species': 'jaguarete',
                'happiness': 85,
                'energy': 70,
                'level': 3,
                'experience': 45,
                'mood': 'happy'
            }
        )

        if not created:
            pet.happiness = 85
            pet.energy = 70
            pet.level = 3
            pet.experience = 45
            pet.mood = 'happy'
            pet.save()

        # Create sample lessons if they don't exist
        lessons_data = [
            {
                'title': 'Saludos básicos',
                'description': 'Aprende los saludos fundamentales en guaraní',
                'order': 1,
                'progress': 100,
                'completed': True
            },
            {
                'title': 'Números 1-10',
                'description': 'Los primeros números en guaraní',
                'order': 2,
                'progress': 85,
                'completed': False
            },
            {
                'title': 'Familia y relaciones',
                'description': 'Vocabulario sobre familia',
                'order': 3,
                'progress': 60,
                'completed': False
            },
            {
                'title': 'Colores',
                'description': 'Los colores básicos en guaraní',
                'order': 4,
                'progress': 30,
                'completed': False
            }
        ]

        for lesson_data in lessons_data:
            lesson, created = Lesson.objects.get_or_create(
                title=lesson_data['title'],
                defaults={
                    'description': lesson_data['description'],
                    'order': lesson_data['order'],
                    'is_published': True
                }
            )

            # Create lesson progress
            progress, created = UserLessonProgress.objects.get_or_create(
                user=user,
                lesson=lesson,
                defaults={
                    'written_score': lesson_data['progress'],
                    'pronunciation_confidence': lesson_data['progress'] * 0.8,
                    'progress_percent': lesson_data['progress'],
                    'completed': lesson_data['completed']
                }
            )

            if not created:
                progress.progress_percent = lesson_data['progress']
                progress.completed = lesson_data['completed']
                progress.save()

        # Create sample glossary entries
        glossary_data = [
            {'es': 'hola', 'gn': 'maitei', 'notes': 'Saludo básico'},
            {'es': 'gracias', 'gn': 'aguyje', 'notes': 'Expresión de gratitud'},
            {'es': 'agua', 'gn': 'y', 'notes': 'Elemento esencial'},
            {'es': 'casa', 'gn': 'óga', 'notes': 'Lugar de vivienda'},
            {'es': 'comer', 'gn': 'karu', 'notes': 'Acción de alimentarse'},
            {'es': 'dormir', 'gn': 'ke', 'notes': 'Acción de descansar'},
            {'es': 'trabajar', 'gn': 'mba\'apo', 'notes': 'Actividad laboral'},
            {'es': 'amigo', 'gn': 'anga', 'notes': 'Persona cercana'},
        ]

        for entry_data in glossary_data:
            entry, created = GlossaryEntry.objects.get_or_create(
                user=user,
                source_text_es=entry_data['es'],
                translated_text_gn=entry_data['gn'],
                defaults={'notes': entry_data['notes']}
            )

        # Award some achievements
        achievements = Achievement.objects.all()
        for i, achievement in enumerate(achievements[:5]):  # Award first 5 achievements
            UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
                defaults={'earned_at': timezone.now()}
            )

        # Create daily challenges progress
        today = timezone.now().date()
        challenges = DailyChallenge.objects.filter(is_active=True)

        for challenge in challenges[:3]:  # Progress on first 3 challenges
            user_challenge, created = UserDailyChallenge.objects.get_or_create(
                user=user,
                challenge=challenge,
                date=today,
                defaults={'current_value': 0}
            )

            # Set some progress based on challenge type
            if challenge.challenge_type == 'lessons':
                user_challenge.current_value = 1
                if random.choice([True, False]):
                    user_challenge.is_completed = True
                    user_challenge.completed_at = timezone.now()
            elif challenge.challenge_type == 'exercises':
                user_challenge.current_value = random.randint(5, 15)
                if user_challenge.current_value >= challenge.target_value:
                    user_challenge.is_completed = True
                    user_challenge.completed_at = timezone.now()
            elif challenge.challenge_type == 'glossary':
                user_challenge.current_value = random.randint(2, 5)
                if user_challenge.current_value >= challenge.target_value:
                    user_challenge.is_completed = True
                    user_challenge.completed_at = timezone.now()

            user_challenge.save()

        # Create leaderboard entries
        leaderboard, created = Leaderboard.objects.get_or_create(
            name="General Semanal",
            period="weekly",
            defaults={"last_updated": timezone.now()}
        )

        # Create some fake users for leaderboard
        fake_users_data = [
            {'username': 'usuario_avanzado', 'points': 850},
            {'username': 'aprendiz_guarni', 'points': 720},
            {'username': 'estudiante_rapido', 'points': 680},
            {'username': 'demo_user', 'points': 450},  # Current user
            {'username': 'principiante', 'points': 320},
        ]

        for user_data in fake_users_data:
            fake_user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': f'{user_data["username"]}@example.com',
                    'first_name': user_data['username'].title()
                }
            )

            if created:
                fake_user.set_password('demo123')
                fake_user.save()

                # Create profile for fake user
                fake_profile = UserProfile.objects.create(
                    user=fake_user,
                    points=user_data['points'],
                    streak=random.randint(1, 15)
                )

                # Create pet for fake user
                pet_species = random.choice(['jaguarete', 'tucan', 'capibara'])
                VirtualPet.objects.create(
                    user=fake_user,
                    name=f'Pet{random.randint(1, 100)}',
                    species=pet_species,
                    happiness=random.randint(60, 95),
                    energy=random.randint(50, 90),
                    level=random.randint(1, 5),
                    experience=random.randint(0, 100)
                )

            # Update leaderboard entry
            period_start = today - timezone.timedelta(days=today.weekday())
            period_end = period_start + timezone.timedelta(days=6)

            LeaderboardEntry.objects.update_or_create(
                leaderboard=leaderboard,
                user=fake_user,
                period_start=period_start,
                period_end=period_end,
                defaults={'score': user_data['points']}
            )

        # Update leaderboard ranks
        entries = LeaderboardEntry.objects.filter(leaderboard=leaderboard)
        for i, entry in enumerate(entries.order_by('-score')):
            entry.rank = i + 1
            entry.save()

        self.stdout.write(
            self.style.SUCCESS('Successfully populated demo data!')
        )
        self.stdout.write(f'Demo user: demo_user / demo123')
        self.stdout.write(f'Total points: {profile.points}')
        self.stdout.write(f'Current streak: {profile.streak} days')
        self.stdout.write(f'Pet: {pet.name} (Level {pet.level})')
        self.stdout.write(f'Achievements earned: {UserAchievement.objects.filter(user=user).count()}')
        self.stdout.write(f'Daily challenges progress: {UserDailyChallenge.objects.filter(user=user, date=today).count()}')
