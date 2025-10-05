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

        # Free models available on OpenRouter (ordered by speed/reliability)
        self.free_models = {
            "translation": "deepseek/deepseek-chat-v3.1:free",  # Fast and reliable
            "general": "deepseek/deepseek-chat-v3.1:free",
            "pronunciation": "deepseek/deepseek-chat-v3.1:free",
            "content": "deepseek/deepseek-chat-v3.1:free"
        }

        # Alternative models (if DeepSeek fails)
        self.backup_models = {
            "translation": "meta-llama/llama-3.2-3b-instruct:free",
            "general": "meta-llama/llama-3.2-3b-instruct:free",
            "pronunciation": "meta-llama/llama-3.2-3b-instruct:free",
            "content": "meta-llama/llama-3.2-3b-instruct:free"
        }

        # Fast models for comparison
        self.fast_models = {
            "translation": "google/gemma-2-2b-it:free",
            "general": "google/gemma-2-2b-it:free",
            "pronunciation": "google/gemma-2-2b-it:free",
            "content": "google/gemma-2-2b-it:free"
        }

        # Model selection method
        self.use_fast_models = False

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

    # Synchronous wrapper methods for easier use
    def translate_es_to_gn(self, text: str) -> Optional[str]:
        """Translate Spanish to Guaraní"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._translate_es_to_gn_async(text))

    def translate_gn_to_es(self, text: str) -> Optional[str]:
        """Translate Guaraní to Spanish"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._translate_gn_to_es_async(text))

    def analyze_pronunciation(self, expected_text: str, user_text: str) -> Dict[str, float]:
        """Analyze pronunciation accuracy"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._analyze_pronunciation_async(expected_text, user_text))

    def generate_exercise_content(self, exercise_type: str, difficulty: str) -> Dict[str, Any]:
        """Generate exercise content"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._generate_exercise_content_async(exercise_type, difficulty))

    def chatbot_response(self, message: str) -> Optional[str]:
        """Generate chatbot response"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._chatbot_response_async(message))

    def chatbot_response_with_model(self, message: str, model_type: str) -> Optional[str]:
        """Generate chatbot response with specific model"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._chatbot_response_with_model_async(message, model_type))

    async def _translate_es_to_gn_async(self, text: str) -> Optional[str]:
        """Async translation from Spanish to Guaraní"""
        prompt = f"""
        Traduce esta frase del español al guaraní de manera natural y precisa:

        "{text}"

        IMPORTANTE:
        - Responde SOLO con la traducción en guaraní
        - No agregues explicaciones ni texto adicional
        - Usa el vocabulario y gramática correcta del guaraní
        - Mantén el significado exacto del texto original

        Ejemplos:
        - "hola" → "maitei"
        - "gracias" → "aguyje"
        - "¿cómo estás?" → "¿mba'éichapa reime?"
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un experto traductor de español a guaraní. Responde solo con la traducción, sin explicaciones adicionales."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        model = self.free_models["translation"]
        return await self._make_request(model, messages, 100)

    async def _translate_gn_to_es_async(self, text: str) -> Optional[str]:
        """Async translation from Guaraní to Spanish"""
        prompt = f"""
        Traduce esta frase del guaraní al español de manera natural y precisa:

        "{text}"

        IMPORTANTE:
        - Responde SOLO con la traducción en español
        - No agregues explicaciones ni texto adicional
        - Usa el vocabulario y gramática correcta del español
        - Mantén el significado exacto del texto original

        Ejemplos:
        - "maitei" → "hola"
        - "aguyje" → "gracias"
        - "¿mba'éichapa reime?" → "¿cómo estás?"
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un experto traductor de guaraní a español. Responde solo con la traducción, sin explicaciones adicionales."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        model = self.free_models["translation"]
        return await self._make_request(model, messages, 100)

    async def _analyze_pronunciation_async(self, expected_text: str, user_text: str) -> Dict[str, float]:
        """Async pronunciation analysis"""
        prompt = f"""
        Analiza la pronunciación comparando el texto esperado vs. lo que dijo el usuario:

        Texto esperado (guaraní): "{expected_text}"
        Texto pronunciado por el usuario: "{user_text}"

        Evalúa en una escala de 0-100 para cada aspecto:
        - Precisión (accuracy): qué tan cerca está la pronunciación del usuario al texto correcto
        - Fluidez (fluency): qué tan natural fluye la pronunciación
        - Completitud (completeness): qué porcentaje del texto fue pronunciado correctamente
        - Prosodia (prosody): qué tan correcta es la entonación y ritmo

        Responde en formato JSON:
        {{
            "accuracy_score": 85,
            "fluency_score": 78,
            "completeness_score": 92,
            "prosody_score": 80
        }}
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un experto en análisis de pronunciación de guaraní. Responde solo con el JSON de evaluación."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        model = self.free_models["pronunciation"]
        result = await self._make_request(model, messages, 200)

        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

        # Fallback scoring
        return {
            "accuracy_score": 75.0,
            "fluency_score": 70.0,
            "completeness_score": 80.0,
            "prosody_score": 75.0
        }

    async def _generate_exercise_content_async(self, exercise_type: str, difficulty: str) -> Dict[str, Any]:
        """Async exercise content generation"""
        prompt = f"""
        Genera contenido para un ejercicio de {exercise_type} en guaraní con dificultad {difficulty}.

        Responde en formato JSON con la estructura apropiada para el tipo de ejercicio.
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un experto profesor de guaraní. Crea ejercicios educativos claros y precisos."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        model = self.free_models["content"]
        result = await self._make_request(model, messages, 300)

        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

        # Fallback content
        return {"content": "Contenido generado automáticamente", "type": exercise_type}

    async def _chatbot_response_async(self, message: str) -> Optional[str]:
        """Async chatbot response"""
        prompt = f"""
        Eres un profesor de guaraní paciente y amigable. El usuario dice: "{message}"

        IMPORTANTE:
        - Responde PRIMERO en guaraní, luego proporciona la traducción al español entre paréntesis
        - Mantén un tono amigable y educativo
        - Usa vocabulario apropiado para principiantes
        - Incluye preguntas para continuar la conversación

        Ejemplo de formato:
        "Mba'éichapa! (¡Hola!) ¿Moõ guive rejikói? (¿De dónde eres?)"

        Responde de manera natural y conversacional.
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un profesor de guaraní experto y paciente. Siempre responde primero en guaraní con traducción en español entre paréntesis."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        model = self.free_models["general"]
        return await self._make_request(model, messages, 200)

    async def _chatbot_response_with_model_async(self, message: str, model_type: str) -> Optional[str]:
        """Async chatbot response with specific model"""
        # Select model based on type
        if model_type == "gemma":
            model = self.fast_models["general"]
        elif model_type == "llama":
            model = self.backup_models["general"]
        else:
            model = self.free_models["general"]

        prompt = f"""
        Eres un profesor de guaraní paciente y amigable. El usuario dice: "{message}"

        IMPORTANTE:
        - Responde PRIMERO en guaraní, luego proporciona la traducción al español entre paréntesis
        - Mantén un tono amigable y educativo
        - Usa vocabulario apropiado para principiantes
        - Incluye preguntas para continuar la conversación

        Ejemplo de formato:
        "Mba'éichapa! (¡Hola!) ¿Moõ guive rejikói? (¿De dónde eres?)"

        Responde de manera natural y conversacional.
        """

        messages = [
            {
                "role": "system",
                "content": "Eres un profesor de guaraní experto y paciente. Siempre responde primero en guaraní con traducción en español entre paréntesis."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        return await self._make_request(model, messages, 200)


# Create global instance for easy importing
openrouter_ai = OpenRouterAI()
