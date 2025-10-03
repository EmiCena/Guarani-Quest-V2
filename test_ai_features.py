#!/usr/bin/env python
# test_ai_features.py
"""
Test script to verify AI features are working correctly.
Run this script to test the OpenRouter AI integration.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'guarani_lms.settings')
django.setup()

from learning.services.ai_openrouter import openrouter_ai

def test_ai_translation():
    """Test AI translation functionality"""
    print("Testing AI Translation...")
    test_texts = [
        "Hola, ¿cómo estás?",
        "Me gusta aprender guaraní",
        "El cielo es azul"
    ]

    for text in test_texts:
        print(f"\nTexto original: {text}")
        try:
            translation = openrouter_ai.translate_es_to_gn(text)
            if translation:
                print(f"Traducción IA: {translation}")
            else:
                print("❌ Error: No se pudo obtener traducción")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def test_ai_pronunciation_analysis():
    """Test AI pronunciation analysis"""
    print("\n\nTesting AI Pronunciation Analysis...")
    expected_text = "Mba'éichapa"
    user_text = "Mba'eichapa"  # Slightly different

    print(f"Texto esperado: {expected_text}")
    print(f"Pronunciación del usuario: {user_text}")

    try:
        analysis = openrouter_ai.analyze_pronunciation(expected_text, user_text)
        print("Análisis de pronunciación:")
        print(f"  Precisión: {analysis['accuracy_score']}%")
        print(f"  Fluidez: {analysis['fluency_score']}%")
        print(f"  Retroalimentación: {analysis['feedback']}")
        print(f"  Sugerencias: {', '.join(analysis['suggestions'])}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_ai_exercise_generation():
    """Test AI exercise generation"""
    print("\n\nTesting AI Exercise Generation...")

    exercise_types = ["fill_blank", "mcq", "translation"]

    for exercise_type in exercise_types:
        print(f"\nGenerando ejercicio tipo: {exercise_type}")
        try:
            content = openrouter_ai.generate_exercise_content(exercise_type, "beginner")
            print(f"Prompt: {content['prompt']}")
            print(f"Respuesta correcta: {content['correct_answer']}")
            if content.get('options'):
                print(f"Opciones: {content['options']}")
            if not content['success']:
                print("⚠️  Se usó contenido por defecto (AI no disponible)")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

def main():
    """Main test function"""
    print("🚀 Testing Guarani-Quest AI Features")
    print("=" * 50)

    # Check if API key is configured
    api_key = getattr(openrouter_ai, 'api_key', '')
    if not api_key:
        print("⚠️  WARNING: OpenRouter API key not configured!")
        print("   Set OPENROUTER_API_KEY in your .env file to enable AI features.")
        print("   You can get a free API key at: https://openrouter.ai/")
        return

    # Run tests
    test_ai_translation()
    test_ai_pronunciation_analysis()
    test_ai_exercise_generation()

    print("\n" + "=" * 50)
    print("✅ AI Features Test Complete!")
    print("\nTo use these features in your app:")
    print("1. Set OPENROUTER_API_KEY in your .env file")
    print("2. Use the API endpoints:")
    print("   - POST /api/ai-translate/ (AI translation)")
    print("   - POST /api/ai-pronunciation-analysis/ (AI pronunciation feedback)")
    print("   - POST /api/ai-generate-exercise/ (AI exercise generation)")
    print("3. Use the gamification endpoints:")
    print("   - GET /api/user-profile/ (user stats and pet)")
    print("   - POST /api/pet-interact/ (pet interactions)")
    print("   - GET /api/daily-challenges/ (daily challenges)")
    print("   - GET /api/leaderboard/ (leaderboards)")

if __name__ == "__main__":
    main()
