from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import Lesson, FillBlankExercise

class Command(BaseCommand):
    help = 'Create sample fill-in-the-blank exercises for Guaraní learning'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lesson-title',
            default='Ejercicios de Completar Espacios',
            help='Title for the lesson containing the exercises'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of exercises to create'
        )

    def handle(self, *args, **options):
        lesson_title = options['lesson_title']
        count = options['count']

        # Get or create the lesson
        lesson, created = Lesson.objects.get_or_create(
            title=lesson_title,
            defaults={
                'description': 'Ejercicios para practicar completar espacios en guaraní',
                'order': 998,
                'is_published': True
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created lesson: {lesson.title}')
            )

        # Sample Guaraní fill-in-the-blank exercises
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
            },
            {
                "prompt_text": "Ajoguahina ___ rehe.",
                "correct_answer": "y",
                "hint": "Lo que bebemos cuando tenemos sed"
            },
            {
                "prompt_text": "Rohayhu ___ che irũ.",
                "correct_answer": "nde",
                "hint": "Pronombre de segunda persona"
            },
            {
                "prompt_text": "Pe ___ ógape.",
                "correct_answer": "kuña",
                "hint": "Persona de género femenino"
            },
            {
                "prompt_text": "Ajapysaka ___ ryapu.",
                "correct_answer": "tũ",
                "hint": "Color que vemos en el cielo nocturno"
            },
            {
                "prompt_text": "Rohana ___ ra'yra.",
                "correct_answer": "ore",
                "hint": "Pronombre posesivo de primera persona plural"
            }
        ]

        exercises_created = 0

        for i, ex_data in enumerate(sample_exercises[:count]):
            exercise, created = FillBlankExercise.objects.get_or_create(
                lesson=lesson,
                order=i + 1,
                defaults={
                    'prompt_text': ex_data['prompt_text'],
                    'correct_answer': ex_data['correct_answer']
                }
            )

            if created:
                exercises_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created exercise: {ex_data["prompt_text"]} -> {ex_data["correct_answer"]}')
                )
            else:
                self.stdout.write(
                    f'Exercise already exists: {ex_data["prompt_text"]}'
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {exercises_created} fill-in-the-blank exercises')
        )

        self.stdout.write(
            self.style.SUCCESS(f'Access the exercises at: /admin/learning/fillblankexercise/')
        )
