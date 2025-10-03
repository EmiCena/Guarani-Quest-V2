# learning/management/commands/init_gamification.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from learning.models import Achievement, DailyChallenge, UserProfile, VirtualPet

class Command(BaseCommand):
    help = 'Initialize gamification data with achievements and daily challenges'

    def handle(self, *args, **options):
        self.stdout.write('Initializing gamification data...')

        # Create default achievements
        achievements_data = [
            {
                'name': 'Primeros Pasos',
                'description': 'Completa tu primera lección',
                'points_reward': 50,
                'icon': '🎯'
            },
            {
                'name': 'Explorador',
                'description': 'Completa 5 lecciones',
                'points_reward': 100,
                'icon': '🗺️'
            },
            {
                'name': 'Políglota',
                'description': 'Aprende 50 palabras nuevas',
                'points_reward': 200,
                'icon': '🌟'
            },
            {
                'name': 'Perfeccionista',
                'description': 'Obtén 100% en 10 ejercicios',
                'points_reward': 150,
                'icon': '💎'
            },
            {
                'name': 'Racha Diaria',
                'description': 'Mantén una racha de 7 días',
                'points_reward': 300,
                'icon': '🔥'
            },
            {
                'name': 'Maestro de la Pronunciación',
                'description': 'Completa 20 ejercicios de pronunciación',
                'points_reward': 250,
                'icon': '🎤'
            },
            {
                'name': 'Cuidando a tu Mascota',
                'description': 'Alimenta a tu mascota 10 veces',
                'points_reward': 100,
                'icon': '🐾'
            },
            {
                'name': 'Retador Diario',
                'description': 'Completa 5 desafíos diarios',
                'points_reward': 200,
                'icon': '🏆'
            }
        ]

        for achievement_data in achievements_data:
            achievement, created = Achievement.objects.get_or_create(
                name=achievement_data['name'],
                defaults=achievement_data
            )
            if created:
                self.stdout.write(f'Created achievement: {achievement.name}')
            else:
                self.stdout.write(f'Achievement already exists: {achievement.name}')

        # Create default daily challenges
        challenges_data = [
            {
                'name': 'Lección Diaria',
                'description': 'Completa una lección hoy',
                'challenge_type': 'lessons',
                'target_value': 1,
                'points_reward': 20
            },
            {
                'name': 'Ejercicios Intensivos',
                'description': 'Resuelve 10 ejercicios hoy',
                'challenge_type': 'exercises',
                'target_value': 10,
                'points_reward': 30
            },
            {
                'name': 'Mantén la Racha',
                'description': 'Inicia sesión por 3 días consecutivos',
                'challenge_type': 'streak',
                'target_value': 3,
                'points_reward': 25
            },
            {
                'name': 'Pronunciación Perfecta',
                'description': 'Practica pronunciación 5 veces',
                'challenge_type': 'pronunciation',
                'target_value': 5,
                'points_reward': 35
            },
            {
                'name': 'Estudiante Aplicado',
                'description': 'Agrega 3 palabras nuevas al glosario',
                'challenge_type': 'glossary',
                'target_value': 3,
                'points_reward': 15
            }
        ]

        for challenge_data in challenges_data:
            challenge, created = DailyChallenge.objects.get_or_create(
                name=challenge_data['name'],
                defaults=challenge_data
            )
            if created:
                self.stdout.write(f'Created daily challenge: {challenge.name}')
            else:
                self.stdout.write(f'Daily challenge already exists: {challenge.name}')

        # Create user profiles and pets for existing users who don't have them
        from django.contrib.auth.models import User

        for user in User.objects.all():
            profile, profile_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'points': 0, 'streak': 0}
            )

            pet, pet_created = VirtualPet.objects.get_or_create(
                user=user,
                defaults={
                    'name': 'Karai',
                    'species': 'jaguarete',
                    'happiness': 50,
                    'energy': 70,
                    'level': 1,
                    'experience': 0
                }
            )

            if profile_created:
                self.stdout.write(f'Created profile for user: {user.username}')
            if pet_created:
                self.stdout.write(f'Created pet for user: {user.username}')

        self.stdout.write(
            self.style.SUCCESS('Successfully initialized gamification data!')
        )
