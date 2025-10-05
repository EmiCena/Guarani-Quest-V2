from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import GlossaryEntry

class Command(BaseCommand):
    help = 'Populate glossary with enhanced sample data showcasing new features'

    def handle(self, *args, **options):
        # Get or create a demo user
        user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={'email': 'demo@example.com'}
        )

        if created:
            self.stdout.write('Created demo user for glossary testing')

        # Sample data with enhanced features
        sample_entries = [
            {
                'source_text_es': 'Hola',
                'translated_text_gn': 'Mba\'éichapa',
                'category': 'saludo',
                'difficulty': 'beginner',
                'tags': ['básico', 'importante', 'frecuente'],
                'usage_examples': ['Mba\'éichapa, ¿mba\'éichapa reime?', 'Mba\'éichapa Juan, ¿moõ guive rejikói?'],
                'is_favorite': True,
                'mastery_level': 0.8
            },
            {
                'source_text_es': 'Gracias',
                'translated_text_gn': 'Aguyje',
                'category': 'saludo',
                'difficulty': 'beginner',
                'tags': ['cortesía', 'frecuente'],
                'usage_examples': ['Aguyje por la ayuda', 'Aguyje, ndaipori vai'],
                'is_favorite': False,
                'mastery_level': 0.6
            },
            {
                'source_text_es': 'Familia',
                'translated_text_gn': 'Familia',
                'category': 'familia',
                'difficulty': 'beginner',
                'tags': ['sustantivo', 'importante'],
                'usage_examples': ['Che familia iko porã', '¿Ndépa nde familia?'],
                'is_favorite': True,
                'mastery_level': 0.9
            },
            {
                'source_text_es': 'Escuela',
                'translated_text_gn': 'Escuela',
                'category': 'escuela',
                'difficulty': 'beginner',
                'tags': ['lugar', 'educación'],
                'usage_examples': ['Rohina escuela peve', 'Escuela ha\'e lugar estudio'],
                'is_favorite': False,
                'mastery_level': 0.7
            },
            {
                'source_text_es': 'Agua',
                'translated_text_gn': 'Y',
                'category': 'comida',
                'difficulty': 'beginner',
                'tags': ['bebida', 'esencial'],
                'usage_examples': ['Ajoguahina y', 'Y hekopete ha\'e'],
                'is_favorite': False,
                'mastery_level': 0.5
            },
            {
                'source_text_es': 'Uno',
                'translated_text_gn': 'Peteĩ',
                'category': 'numeros',
                'difficulty': 'beginner',
                'tags': ['número', 'cardinal'],
                'usage_examples': ['Peteĩ óga', 'Peteĩ familia'],
                'is_favorite': False,
                'mastery_level': 0.3
            },
            {
                'source_text_es': 'Rojo',
                'translated_text_gn': 'Pytã',
                'category': 'colores',
                'difficulty': 'intermediate',
                'tags': ['color', 'adjetivo'],
                'usage_examples': ['Pytã ha\'e color porã', 'Che auto pytã'],
                'is_favorite': False,
                'mastery_level': 0.4
            },
            {
                'source_text_es': 'Hermoso/bonito',
                'translated_text_gn': 'Porã',
                'category': 'general',
                'difficulty': 'intermediate',
                'tags': ['adjetivo', 'descripción'],
                'usage_examples': ['Ko\'ápe porã', 'Nde réra porã'],
                'is_favorite': True,
                'mastery_level': 0.85
            }
        ]

        created_count = 0

        for entry_data in sample_entries:
            entry, created = GlossaryEntry.objects.get_or_create(
                user=user,
                source_text_es=entry_data['source_text_es'],
                translated_text_gn=entry_data['translated_text_gn'],
                defaults=entry_data
            )

            if created:
                created_count += 1
                self.stdout.write(f'Created: {entry.source_text_es} → {entry.translated_text_gn}')
            else:
                # Update existing entry with enhanced data
                for key, value in entry_data.items():
                    if key not in ['source_text_es', 'translated_text_gn']:
                        setattr(entry, key, value)
                entry.save()
                self.stdout.write(f'Updated: {entry.source_text_es} → {entry.translated_text_gn}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created/updated {created_count} enhanced glossary entries')
        )

        # Show summary
        total_entries = GlossaryEntry.objects.filter(user=user).count()
        favorite_entries = GlossaryEntry.objects.filter(user=user, is_favorite=True).count()

        self.stdout.write(
            self.style.SUCCESS(f'Total entries: {total_entries}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Favorite entries: {favorite_entries}')
        )

        # Show category breakdown
        categories = GlossaryEntry.objects.filter(user=user).values('category').distinct()
        for cat in categories:
            count = GlossaryEntry.objects.filter(user=user, category=cat['category']).count()
            self.stdout.write(f'  {cat["category"]}: {count} entries')
