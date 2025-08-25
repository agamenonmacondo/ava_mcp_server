import os
import sys
import logging
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger(__name__)

# Intentar importar dependencias de audio
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("⚠️ pygame no disponible para reproducción de audio")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ openai no disponible")

class OpenAITTSAdapter:
    def __init__(self):
        """Inicializar adaptador de TTS con OpenAI - CORREGIDO"""
        self.description = "OpenAI Text to Speech Adapter - TTS-1"
        
        # Cargar variables de entorno
        load_dotenv(dotenv_path="C:/Users/h/Downloads/pagina ava/mod-pagina/.env", override=True)
        
        # Configurar directorio de salida
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(current_dir, "..", "..", "generated_audio")
        os.makedirs(self.output_dir, exist_ok=True)
        
        try:
            if not OPENAI_AVAILABLE:
                self.has_client = False
                logger.error("❌ OpenAI library no disponible")
                return
                
            api_key = os.getenv("OPENAI_API_KEY")
            
            if api_key:
                # ✅ CORREGIDO: Remover argumento 'proxies'
                self.client = OpenAI(api_key=api_key)
                self.has_client = True
                self.model_name = "tts-1"
                logger.info("✅ OpenAI TTS client inicializado correctamente")
            else:
                self.has_client = False
                logger.warning("⚠️ OPENAI_API_KEY no encontrada")
                
        except Exception as e:
            self.has_client = False
            logger.error(f"❌ Error inicializando OpenAI client: {e}")
    
    def execute(self, arguments: dict) -> dict:
        """Ejecutar síntesis de voz"""
        try:
            if not self.has_client:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ **OpenAI TTS no disponible**\n\n"
                               "🔧 **Posibles causas:**\n"
                               "• OPENAI_API_KEY no configurada\n"
                               "• Error de inicialización del cliente\n"
                               "• Dependencias faltantes\n\n"
                               "💡 **Solución:** Configura tu OPENAI_API_KEY en las variables de entorno"
                    }]
                }
            
            text = arguments.get('text', '')
            voice = arguments.get('voice', 'alloy')  # alloy, echo, fable, onyx, nova, shimmer
            model = arguments.get('model', 'tts-1')  # tts-1 o tts-1-hd
            play_audio = arguments.get('play', False)
            
            if not text:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ **Error:** Se requiere el texto a sintetizar (text)"
                    }]
                }
            
            if len(text) > 4096:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ **Error:** El texto es demasiado largo ({len(text)} caracteres). Máximo: 4096 caracteres"
                    }]
                }
            
            # Generar audio
            result = self._generate_speech(text, voice, model)
            
            if result.get('success'):
                # Reproducir si se solicita
                if play_audio and PYGAME_AVAILABLE:
                    self._play_audio(result['filepath'])
                
                return {
                    "content": [{
                        "type": "text",
                        "text": f"🔊 **Audio generado exitosamente**\n\n"
                               f"📝 **Texto:** {text[:100]}{'...' if len(text) > 100 else ''}\n"
                               f"🎭 **Voz:** {voice}\n"
                               f"🤖 **Modelo:** {model}\n"
                               f"📁 **Guardado en:** {result['filepath']}\n"
                               f"📊 **Tamaño:** {result.get('size_bytes', 0):,} bytes\n"
                               f"⏱️ **Generado en:** {result.get('generation_time', 'N/A')} segundos\n\n"
                               f"{'🔊 Audio reproducido' if play_audio and PYGAME_AVAILABLE else '💾 Audio guardado'}"
                    }],
                    "audio_data": {
                        "filepath": result['filepath'],
                        "text": text,
                        "voice": voice,
                        "model": model,
                        "size_bytes": result.get('size_bytes'),
                        "generation_time": result.get('generation_time')
                    }
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ **Error generando audio**\n\n"
                               f"**Error:** {result.get('error', 'Error desconocido')}\n"
                               f"**Texto:** {text[:100]}...\n\n"
                               f"🔧 **Posibles soluciones:**\n"
                               f"• Verificar OPENAI_API_KEY\n"
                               f"• Reducir longitud del texto\n"
                               f"• Intentar con otra voz\n"
                               f"• Verificar créditos en OpenAI"
                    }]
                }
                
        except Exception as e:
            logger.error(f"Error en openai tts adapter: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ **Error del sistema de TTS:** {str(e)}"
                }]
            }
    
    def _generate_speech(self, text: str, voice: str, model: str) -> dict:
        """Generar audio usando OpenAI TTS"""
        start_time = datetime.now()
        
        try:
            # Generar audio con OpenAI
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format="mp3"
            )
            
            # Guardar archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tts_generated_{timestamp}.mp3"
            filepath = os.path.join(self.output_dir, filename)
            
            # Escribir archivo de audio
            with open(filepath, 'wb') as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            size_bytes = os.path.getsize(filepath)
            
            logger.info(f"✅ Audio TTS generado: {filepath}")
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': filename,
                'size_bytes': size_bytes,
                'generation_time': round(generation_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Error generando TTS: {e}")
            return {
                'success': False,
                'error': f'Error de generación TTS: {str(e)}'
            }
    
    def _play_audio(self, filepath: str):
        """Reproducir audio usando pygame"""
        try:
            if not PYGAME_AVAILABLE:
                logger.warning("pygame no disponible para reproducción")
                return
            
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            
            # Esperar a que termine la reproducción
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            logger.info("✅ Audio reproducido correctamente")
            
        except Exception as e:
            logger.error(f"Error reproduciendo audio: {e}")
    
    def get_available_voices(self) -> list:
        """Obtener lista de voces disponibles"""
        return ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer']
    
    def get_available_models(self) -> list:
        """Obtener lista de modelos disponibles"""
        return ['tts-1', 'tts-1-hd']
    
    def process(self, arguments: dict) -> str:
        """Alias para execute - compatibilidad"""
        result = self.execute(arguments)
        if isinstance(result, dict) and "content" in result:
            return result["content"][0]["text"]
        return str(result)

# Función de prueba
def test_openai_tts():
    """Función para probar OpenAI TTS adapter"""
    print("🧪 Testing OpenAI TTS Adapter...")
    
    adapter = OpenAITTSAdapter()
    print(f"Cliente disponible: {adapter.has_client}")
    print(f"Voces disponibles: {adapter.get_available_voices()}")
    print(f"Modelos disponibles: {adapter.get_available_models()}")
    
    # Test básico
    result = adapter.execute({
        "text": "Hola, soy Ava Bot. Este es un test de síntesis de voz.",
        "voice": "nova",
        "model": "tts-1",
        "play": False
    })
    
    print(f"Resultado: {result}")

if __name__ == "__main__":
    test_openai_tts()
