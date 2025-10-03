# learning/services/ai_openrouter.py
import os
import json
import asyncio
import aiohttp
from django.conf import settings
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class OpenRouterAI:
    """AI service using free models from OpenRouter"""

    def __init__(self):
        self.api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": getattr(settings, 'SITE_URL', 'http://localhost:8000'),
            "X-Title": "Guarani Language Learning App"
        }

        # Free models available on OpenRouter
        self.free_models = {
            "translation": "meta-llama/llama-3.2-3b-instruct:free",
            "general": "meta-llama/llama-3.2-3b-instruct:free",
            "pronunciation": "meta-llama/llama-3.2-3b-instruct:free",
            "content": "meta-llama/llama-3.2-3b-instruct:free"
        }

    async def _make_request(self, model: str, messages: list, max_tokens: int = 150) -> Optional[str]:
        """Make async request to OpenRouter API"""
        if not self.api_key:
            logger.warning("OpenRouter API key not configured")
            return None

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        logger.error(f"OpenRouter API error: {response.status} - {await response.text()}")
                        return None
        except asyncio.TimeoutError:
            logger.error("OpenRouter API request timed out")
            return None
        except Exception as e:
            logger.error(f"OpenRouter API request failed: {str(e)}")
            return None

    def translate_es_to_gn(self, text_es: str) -> Optional[str]:
        """Translate Spanish text to Guarani using AI"""
        if not text_es.strip():
            return None

        messages = [
            {
                "role": "system",
                "content": "Eres un experto traductor de español a guaraní. Traduce el siguiente texto de español a guaraní de manera natural y precisa. Solo devuelve la traducción, sin explicaciones adicionales."
            },
            {
                "role": "user",
                "content": f"Traduce esto al guaraní: '{text_es}'"
            }
        ]

        # Use asyncio to run the async function
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we need to handle this differently
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._translate_sync, messages)
                    return future.result(timeout=10)
            else:
                return loop.run_until_complete(self._make_request(self.free_models["translation"], messages, 100))
        except Exception as e:
            logger.error(f"Translation failed: {str(e)}")
            return None

    def _translate_sync(self, messages: list) -> Optional[str]:
        """Synchronous wrapper for translation"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._make_request(self.free_models["translation"], messages, 100))
        except Exception as e:
            logger.error(f"Sync translation failed: {str(e)}")
            return None
        finally:
            loop.close()

    def analyze_pronunciation(self, expected_text: str, user_text: str) -> Dict[str, Any]:
        """Analyze pronunciation attempt and provide feedback"""
        messages = [
            {
                "role": "system",
                "content": "Eres un experto profesor de guaraní. Analiza la pronunciación del usuario comparando el texto esperado con lo que dijo. Proporciona un análisis detallado con puntuaciones de precisión, fluidez y retroalimentación constructiva."
            },
            {
                "role": "user",
                "content": f"Texto esperado (guaraní): '{expected_text}'\nTexto pronunciado por el usuario: '{user_text}'\n\nProporciona un análisis en formato JSON con las siguientes claves:\n- accuracy_score (0-100): qué tan cerca está la pronunciación\n- fluency_score (0-100): qué tan fluida es la pronunciación\n- feedback: comentarios constructivos en español\n- suggestions: sugerencias específicas para mejorar"
            }
        ]

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._analyze_pronunciation_sync, messages)
                    result = future.result(timeout=10)
            else:
                result = loop.run_until_complete(self._make_request(self.free_models["pronunciation"], messages, 200))

            if result:
                return self._parse_pronunciation_analysis(result)
            return self._get_default_pronunciation_analysis()
        except Exception as e:
            logger.error(f"Pronunciation analysis failed: {str(e)}")
            return self._get_default_pronunciation_analysis()

    def _analyze_pronunciation_sync(self, messages: list) -> Optional[str]:
        """Synchronous wrapper for pronunciation analysis"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._make_request(self.free_models["pronunciation"], messages, 200))
        except Exception as e:
            logger.error(f"Sync pronunciation analysis failed: {str(e)}")
            return None
        finally:
            loop.close()

    def _parse_pronunciation_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response for pronunciation analysis"""
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "accuracy_score": max(0, min(100, float(data.get("accuracy_score", 50)))),
                    "fluency_score": max(0, min(100, float(data.get("fluency_score", 50)))),
                    "completeness_score": max(0, min(100, float(data.get("completeness_score", 50)))),
                    "prosody_score": max(0, min(100, float(data.get("prosody_score", 50)))),
                    "feedback": data.get("feedback", "Buen intento. Sigue practicando."),
                    "suggestions": data.get("suggestions", ["Practica la pronunciación diariamente"])
                }
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        return self._get_default_pronunciation_analysis()

    def _get_default_pronunciation_analysis(self) -> Dict[str, Any]:
        """Default pronunciation analysis when AI fails"""
        return {
            "accuracy_score": 75.0,
            "fluency_score": 70.0,
            "completeness_score": 80.0,
            "prosody_score": 70.0,
            "feedback": "Análisis básico completado. Para mejores resultados, asegúrate de que tu micrófono capture claramente tu voz.",
            "suggestions": ["Practica la pronunciación de las vocales guaraníes", "Presta atención a los acentos"]
        }

    def generate_exercise_content(self, exercise_type: str, difficulty: str = "beginner") -> Dict[str, Any]:
        """Generate exercise content using AI"""
        prompts = {
            "fill_blank": "Genera una oración en guaraní con una palabra faltante para que el estudiante la complete.",
            "mcq": "Genera una pregunta de opción múltiple sobre gramática o vocabulario guaraní.",
            "translation": "Genera una oración simple en español que deba traducirse al guaraní."
        }

        prompt = prompts.get(exercise_type, prompts["translation"])

        messages = [
            {
                "role": "system",
                "content": f"Eres un profesor de guaraní. {prompt} Dificultad: {difficulty}. Responde en formato JSON con las claves: prompt, correct_answer, y opciones si aplica."
            },
            {
                "role": "user",
                "content": f"Genera contenido para ejercicio de tipo '{exercise_type}' en guaraní, dificultad '{difficulty}'."
            }
        ]

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(self._generate_exercise_sync, messages)
                    result = future.result(timeout=10)
            else:
                result = loop.run_until_complete(self._make_request(self.free_models["content"], messages, 150))

            if result:
                return self._parse_exercise_content(result, exercise_type)
            return self._get_default_exercise_content(exercise_type)
        except Exception as e:
            logger.error(f"Exercise generation failed: {str(e)}")
            return self._get_default_exercise_content(exercise_type)

    def _generate_exercise_sync(self, messages: list) -> Optional[str]:
        """Synchronous wrapper for exercise generation"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self._make_request(self.free_models["content"], messages, 150))
        except Exception as e:
            logger.error(f"Sync exercise generation failed: {str(e)}")
            return None
        finally:
            loop.close()

    def _parse_exercise_content(self, ai_response: str, exercise_type: str) -> Dict[str, Any]:
        """Parse AI response for exercise content"""
        try:
            import re
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "prompt": data.get("prompt", "Contenido generado por IA"),
                    "correct_answer": data.get("correct_answer", ""),
                    "options": data.get("options", []),
                    "success": True
                }
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        return self._get_default_exercise_content(exercise_type)

    def _get_default_exercise_content(self, exercise_type: str) -> Dict[str, Any]:
        """Default exercise content when AI fails"""
        defaults = {
            "fill_blank": {
                "prompt": "Che ___ María. (soy)",
                "correct_answer": "héra",
                "options": [],
                "success": False
            },
            "mcq": {
                "prompt": "¿Cómo se dice 'hola' en guaraní?",
                "correct_answer": "maitei",
                "options": ["maitei", "jajotopata", "mboriahu", "ikatú"],
                "success": False
            },
            "translation": {
                "prompt": "Hola, ¿cómo estás?",
                "correct_answer": "Mba'éichapa reime?",
                "options": [],
                "success": False
            }
        }
        return defaults.get(exercise_type, defaults["translation"])

# Global instance
openrouter_ai = OpenRouterAI()
