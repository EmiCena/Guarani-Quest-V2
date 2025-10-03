# 🤖 Guarani-Quest: AI y Gamificación

Este documento describe las nuevas características de IA y gamificación agregadas a Guarani-Quest.

## 🚀 Características Implementadas

### 1. 🤖 Funciones de IA con OpenRouter

#### Traducción Automática con IA
- **Modelo gratuito**: `meta-llama/llama-3.2-3b-instruct:free`
- **Endpoint**: `POST /api/ai-translate/`
- **Uso**:
```json
{
  "text": "Hola, ¿cómo estás?"
}
```

#### Análisis de Pronunciación con IA
- **Modelo gratuito**: `meta-llama/llama-3.2-3b-instruct:free`
- **Endpoint**: `POST /api/ai-pronunciation-analysis/`
- **Uso**:
```json
{
  "expected_text": "Mba'éichapa",
  "user_text": "Mba'eichapa",
  "exercise_id": 123
}
```

#### Generación de Ejercicios con IA
- **Modelo gratuito**: `meta-llama/llama-3.2-3b-instruct:free`
- **Endpoint**: `POST /api/ai-generate-exercise/`
- **Tipos soportados**: `fill_blank`, `mcq`, `translation`
- **Uso**:
```json
{
  "exercise_type": "translation",
  "difficulty": "beginner"
}
```

### 2. 🎮 Sistema de Gamificación Mejorado

#### Logros (Achievements)
- **Modelos**: `Achievement`, `UserAchievement`
- **Logros prediseñados**:
  - 🎯 Primeros Pasos (50 puntos)
  - 🗺️ Explorador (100 puntos)
  - 🌟 Políglota (200 puntos)
  - 💎 Perfeccionista (150 puntos)
  - 🔥 Racha Diaria (300 puntos)
  - 🎤 Maestro de la Pronunciación (250 puntos)
  - 🐾 Cuidando a tu Mascota (100 puntos)
  - 🏆 Retador Diario (200 puntos)

#### Desafíos Diarios
- **Modelos**: `DailyChallenge`, `UserDailyChallenge`
- **Desafíos disponibles**:
  - 📚 Lección Diaria (20 puntos)
  - 💪 Ejercicios Intensivos (30 puntos)
  - 🔥 Mantén la Racha (25 puntos)
  - 🎤 Pronunciación Perfecta (35 puntos)
  - 📖 Estudiante Aplicado (15 puntos)

#### Tabla de Posiciones
- **Modelo**: `Leaderboard`, `LeaderboardEntry`
- **Períodos**: Diario, Semanal, Mensual, Todo el tiempo
- **Endpoint**: `GET /api/leaderboard/?period=weekly`

### 3. 🐾 Sistema de Mascota Virtual Avanzado

#### Características de la Mascota
- **Especies disponibles**: Jaguareté, Tucán, Capibara, Mariposa, Mono
- **Estados de ánimo**: Feliz, Triste, Cansado, Hambriento, Aburrido, Emocionado, Somnoliento
- **Interacciones**:
  - 🍖 Alimentar (aumenta felicidad y energía)
  - 🎾 Jugar (aumenta felicidad, consume energía)
  - 🧽 Limpiar (aumenta felicidad)

#### Sistema de Nivel y Experiencia
- **Progresión**: 100 XP por nivel
- **Beneficios**: Mayor felicidad y energía máxima por nivel
- **Mensajes personalizados** según el estado de ánimo

## 🔧 Configuración

### 1. Variables de Entorno

Crea un archivo `.env` basado en `.env.example`:

```bash
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# OpenRouter AI (required for AI features)
OPENROUTER_API_KEY=your-openrouter-api-key-here
SITE_URL=http://localhost:8000

# Azure Speech Services (optional)
AZURE_SPEECH_REGION=your-region
AZURE_SPEECH_KEY=your-key

# Google Cloud Translation (optional)
GOOGLE_PROJECT_ID=your-project-id
```

### 2. Obtener API Key de OpenRouter

1. Ve a [https://openrouter.ai/](https://openrouter.ai/)
2. Crea una cuenta gratuita
3. Genera una API key
4. Agrega la key a tu archivo `.env`

## 📡 Endpoints de la API

### AI Endpoints
- `POST /api/ai-translate/` - Traducción con IA
- `POST /api/ai-pronunciation-analysis/` - Análisis de pronunciación
- `POST /api/ai-generate-exercise/` - Generación de ejercicios

### Gamificación Endpoints
- `GET /api/user-profile/` - Perfil del usuario y mascota
- `POST /api/pet-interact/` - Interactuar con la mascota
- `GET /api/daily-challenges/` - Desafíos diarios
- `POST /api/update-daily-challenge/` - Actualizar progreso de desafíos
- `GET /api/leaderboard/` - Tabla de posiciones
- `POST /api/award-achievement/` - Otorgar logros

## 🗄️ Modelos de Base de Datos

### Nuevos Modelos Creados
- `UserProfile` - Perfil de gamificación del usuario
- `Achievement` - Logros disponibles
- `UserAchievement` - Logros obtenidos por usuarios
- `DailyChallenge` - Desafíos diarios
- `UserDailyChallenge` - Progreso de desafíos por usuario
- `Leaderboard` - Tablas de posiciones
- `LeaderboardEntry` - Entradas de tabla de posiciones
- `VirtualPet` - Mascota virtual mejorada

## 🧪 Pruebas

### Ejecutar Pruebas de AI
```bash
python test_ai_features.py
```

### Inicializar Datos de Gamificación
```bash
python manage.py init_gamification
```

## 🎯 Próximos Pasos

### Frontend Integration
Para completar la implementación, necesitarás:

1. **Actualizar plantillas** para mostrar elementos de gamificación
2. **Agregar JavaScript** para interactuar con los nuevos endpoints
3. **Crear interfaz de usuario** para la mascota virtual
4. **Implementar notificaciones** para logros y desafíos

### Ejemplo de Integración Frontend

```javascript
// Ejemplo de uso de la API de traducción con IA
async function translateWithAI(text) {
    const response = await fetch('/api/ai-translate/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ text })
    });
    return await response.json();
}

// Ejemplo de interacción con la mascota
async function feedPet(foodType = 'normal') {
    const response = await fetch('/api/pet-interact/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            action: 'feed',
            food_type: foodType
        })
    });
    return await response.json();
}
```

## 🔍 Características Técnicas

### AI Service (`learning/services/ai_openrouter.py`)
- **Manejo de errores robusto** con fallbacks
- **Soporte asíncrono** para mejor rendimiento
- **Modelos gratuitos** de OpenRouter
- **Logging detallado** para debugging

### Sistema de Mascota
- **Lógica de estado de ánimo** basada en tiempo y acciones
- **Sistema de nivel** con experiencia
- **Mensajes contextuales** según el estado
- **Múltiples especies** con características únicas

### Gamificación
- **Progreso automático** de desafíos
- **Sistema de puntos** integrado
- **Logros dinámicos** basados en acciones del usuario
- **Tablas de posiciones** con múltiples períodos

## 🚨 Notas Importantes

1. **API Key requerida**: Las funciones de IA requieren una API key gratuita de OpenRouter
2. **Modelos gratuitos**: Se utilizan modelos gratuitos con límites de uso
3. **Fallbacks implementados**: El sistema funciona sin IA usando respuestas por defecto
4. **Escalabilidad**: El sistema está diseñado para manejar múltiples usuarios

## 📞 Soporte

Para problemas o preguntas:
1. Revisa los logs de Django para errores de API
2. Verifica que la API key de OpenRouter sea válida
3. Asegúrate de que todas las dependencias estén instaladas

¡Disfruta de las nuevas características de IA y gamificación en Guarani-Quest! 🎉
