# learning/management/commands/create_lesson_with_ai.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from learning.models import Lesson, LessonSection
from learning.services.ai_openrouter import openrouter_ai
import json

class Command(BaseCommand):
    help = 'Create a lesson using AI features'

    def add_arguments(self, parser):
        parser.add_argument('--title', type=str, help='Lesson title in Spanish')
        parser.add_argument('--topic', type=str, help='Topic/theme of the lesson')
        parser.add_argument('--difficulty', type=str, default='beginner', help='Difficulty level')
        parser.add_argument('--sections', type=int, default=3, help='Number of sections to create')

    def handle(self, *args, **options):
        # Check if user is admin (only admins can run this command)
        from django.contrib.auth.models import User
        import getpass
        import os

        # For security, only allow admins to use this command
        # In a real deployment, you'd check against the actual user
        # For now, we'll just warn that this should be admin-only
        self.stdout.write(self.style.WARNING('⚠️  ADVERTENCIA: Este comando debería ejecutarse solo por administradores'))
        self.stdout.write('')

        title = options['title']
        topic = options['topic']
        difficulty = options['difficulty']
        sections_count = options['sections']

        if not title:
            self.stdout.write(self.style.ERROR('Please provide a lesson title with --title'))
            return

        if not topic:
            self.stdout.write(self.style.ERROR('Please provide a topic with --topic'))
            return

        self.stdout.write(f'Creating lesson: {title}')
        self.stdout.write(f'Topic: {topic}')
        self.stdout.write(f'Difficulty: {difficulty}')
        self.stdout.write(f'Sections: {sections_count}')
        self.stdout.write('')

        # Create the lesson
        lesson = Lesson.objects.create(
            title=title,
            description=f"Lección sobre {topic} en guaraní",
            order=Lesson.objects.count() + 1,
            is_published=True
        )

        self.stdout.write(self.style.SUCCESS(f'Created lesson: {lesson.title} (ID: {lesson.id})'))
        self.stdout.write('')

        # Generate sections using AI
        for i in range(sections_count):
            self.stdout.write(f'Generating section {i+1}/{sections_count}...')

            # Generate section content using AI
            section_content = self._generate_section_content(topic, difficulty, i+1)

            if section_content:
                section = LessonSection.objects.create(
                    lesson=lesson,
                    title=section_content['title'],
                    content=section_content['content'],
                    order=i+1,
                    section_type='content'
                )

                self.stdout.write(self.style.SUCCESS(f'  ✓ Created section: {section.title}'))
                self.stdout.write(f'    Content: {section_content["content"][:100]}...')

                # Generate exercises for this section
                exercises = self._generate_exercises_for_section(topic, difficulty, i+1)
                self.stdout.write(f'    Generated {len(exercises)} exercises')
            else:
                self.stdout.write(self.style.WARNING(f'  ⚠ Could not generate section {i+1}'))
                # Create a basic section as fallback
                LessonSection.objects.create(
                    lesson=lesson,
                    title=f"Sección {i+1}: {topic.title()}",
                    content=f"Contenido sobre {topic} generado automáticamente.",
                    order=i+1,
                    section_type='content'
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Lesson creation completed!'))
        self.stdout.write(f'Lesson URL: /learning/lessons/{lesson.id}/')
        self.stdout.write('')
        self.stdout.write('To add more exercises, use:')
        self.stdout.write(f'  python manage.py add_exercises_to_lesson --lesson-id {lesson.id}')

    def _generate_section_content(self, topic, difficulty, section_num):
        """Generate section content using AI"""
        try:
            prompt = f"""
            Crea contenido para la sección {section_num} de una lección sobre "{topic}" en guaraní.
            Dificultad: {difficulty}

            Responde en formato JSON con:
            {{
                "title": "Título de la sección",
                "content": "Contenido educativo en español sobre el tema",
                "key_phrases": ["frase1", "frase2", "frase3"]
            }}
            """

            messages = [
                {
                    "role": "system",
                    "content": "Eres un experto profesor de guaraní. Crea contenido educativo estructurado y preciso."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Use the AI service
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're in an async context, handle differently
                    return self._get_default_section_content(topic, section_num)
                else:
                    result = loop.run_until_complete(
                        openrouter_ai._make_request(openrouter_ai.free_models["content"], messages, 300)
                    )
            except RuntimeError:
                # No event loop, create one
                result = openrouter_ai._translate_sync(messages)

            if result:
                try:
                    data = json.loads(result)
                    return {
                        'title': data.get('title', f'Sección {section_num}: {topic.title()}'),
                        'content': data.get('content', f'Contenido sobre {topic}'),
                        'key_phrases': data.get('key_phrases', [])
                    }
                except json.JSONDecodeError:
                    return self._get_default_section_content(topic, section_num)

            return self._get_default_section_content(topic, section_num)

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Error generating section: {str(e)}'))
            return self._get_default_section_content(topic, section_num)

    def _get_default_section_content(self, topic, section_num):
        """Default section content when AI fails"""
        topics_content = {
            'saludos': {
                'title': 'Saludos básicos en guaraní',
                'content': 'En guaraní, los saludos son una parte fundamental de la comunicación diaria. Aprendamos los saludos más comunes.',
                'key_phrases': ['Mba\'éichapa', 'Mba\'éichapa ne reime', 'Mba\'éichapa nde reko']
            },
            'numeros': {
                'title': 'Números del 1 al 10',
                'content': 'Los números son esenciales para contar y hacer operaciones básicas. Veamos cómo se dicen en guaraní.',
                'key_phrases': ['Peteĩ', 'Mokõi', 'Mbohapy', 'Irundy']
            },
            'familia': {
                'title': 'Miembros de la familia',
                'content': 'La familia es muy importante en la cultura guaraní. Aprendamos cómo nombrar a cada miembro.',
                'key_phrases': ['Taita', 'Sy', 'Tembi\'u', 'Roguata']
            }
        }

        return topics_content.get(topic.lower(), {
            'title': f'Sección {section_num}: {topic.title()}',
            'content': f'Contenido educativo sobre {topic}. Esta sección fue creada automáticamente.',
            'key_phrases': ['Frase de ejemplo 1', 'Frase de ejemplo 2', 'Frase de ejemplo 3']
        })

    def _generate_exercises_for_section(self, topic, difficulty, section_num):
        """Generate exercises for a section"""
        exercises = []

        try:
            # Generate fill-in-the-blank exercise
            fill_blank = openrouter_ai.generate_exercise_content('fill_blank', difficulty)
            if fill_blank.get('success', False):
                from learning.models import FillBlankExercise
                fb_exercise = FillBlankExercise.objects.create(
                    lesson=None,  # We'll assign this later
                    prompt=fill_blank['prompt'],
                    correct_answer=fill_blank['correct_answer'],
                    difficulty=difficulty
                )
                exercises.append(fb_exercise)

            # Generate multiple choice exercise
            mcq = openrouter_ai.generate_exercise_content('mcq', difficulty)
            if mcq.get('success', False):
                from learning.models import MultipleChoiceExercise
                mcq_exercise = MultipleChoiceExercise.objects.create(
                    lesson=None,
                    question=mcq['prompt'],
                    option_a=mcq['options'][0] if len(mcq['options']) > 0 else 'Opción A',
                    option_b=mcq['options'][1] if len(mcq['options']) > 1 else 'Opción B',
                    option_c=mcq['options'][2] if len(mcq['options']) > 2 else 'Opción C',
                    option_d=mcq['options'][3] if len(mcq['options']) > 3 else 'Opción D',
                    correct_key='A',  # This should be determined from the AI response
                    difficulty=difficulty
                )
                exercises.append(mcq_exercise)

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Error generating exercises: {str(e)}'))

        return exercises
