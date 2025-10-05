from django.core.management.base import BaseCommand
from learning.models import Lesson, DragDropExercise

class Command(BaseCommand):
    help = 'Create sample drag and drop exercises for Guaraní learning'

    def add_arguments(self, parser):
        parser.add_argument(
            '--lesson-title',
            default='Ejercicios de Arrastrar y Soltar',
            help='Title for the lesson containing the exercises'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of exercises to create'
        )

    def handle(self, *args, **options):
        lesson_title = options['lesson_title']
        count = options['count']

        # Get or create the lesson
        lesson, created = Lesson.objects.get_or_create(
            title=lesson_title,
            defaults={
                'description': 'Ejercicios para practicar ordenar palabras en guaraní',
                'order': 999,
                'is_published': True
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created lesson: {lesson.title}')
            )

        # Sample Guaraní drag and drop exercises
        sample_exercises = [
            {
                "prompt_text": "Ordena las palabras para formar una oración correcta en guaraní:",
                "correct_tokens": ["che", "rohina", "escuela", "peve"],
                "hint": "Piensa en ir a un lugar para estudiar"
            },
            {
                "prompt_text": "Completa la oración con las palabras en orden correcto:",
                "correct_tokens": ["agua", "ajoguahina", "rogue"],
                "hint": "Es algo que haces cuando tienes sed"
            },
            {
                "prompt_text": "Arma la frase correctamente:",
                "correct_tokens": ["maitei", "mba'éichapa", "iko"],
                "hint": "Una forma de saludar y responder"
            },
            {
                "prompt_text": "Ordena estas palabras:",
                "correct_tokens": ["óga", "aháta", "che", "peve"],
                "hint": "Me dirijo hacia mi hogar"
            }
        ]

        exercises_created = 0

        for i, ex_data in enumerate(sample_exercises[:count]):
            exercise, created = DragDropExercise.objects.get_or_create(
                lesson=lesson,
                order=i + 1,
                defaults={
                    'prompt_text': ex_data['prompt_text'],
                    'correct_tokens': ex_data['correct_tokens']
                }
            )

            if created:
                exercises_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created exercise: {ex_data["prompt_text"]} -> {", ".join(ex_data["correct_tokens"])}')
                )
            else:
                self.stdout.write(
                    f'Exercise already exists: {ex_data["prompt_text"]}'
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {exercises_created} drag and drop exercises')
        )

        self.stdout.write(
            self.style.SUCCESS(f'Access the exercises at: /admin/learning/dragdropexercise/')
        )
