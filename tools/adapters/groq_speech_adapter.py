import os
import sys
import logging
import tempfile
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger(__name__)

# Intentar importar dependencias de audio
try:
    import pydub
    from pydub import AudioSegment
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False
    logger.warning("⚠️ pydub no disponible para procesamiento de audio")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("⚠️ groq no disponible")

class GroqSpeechAdapter:
    def __init__(self):
        """Inicializar adaptador de speech con Groq - CORREGIDO"""
        self.description = "Groq Speech to Text Adapter - Whisper Large v3"
        
        # Cargar variables de entorno
        load_dotenv(dotenv_path="C:/Users/h/Downloads/pagina ava/mod-pagina/.env", override=True)
        
        try:
            if not GROQ_AVAILABLE:
                self.has_client = False
                logger.error("❌ Groq library no disponible")
                return
                
            api_key = os.getenv("GROQ_API_KEY")
            
            if api_key:
                # ✅ CORREGIDO: Remover argumento 'proxies'
                self.client = Groq(api_key=api_key)
                self.has_client = True
                self.model_name = "whisper-large-v3"
                logger.info("✅ Groq Speech client inicializado correctamente")
            else:
                self.has_client = False
                logger.warning("⚠️ GROQ_API_KEY no encontrada")
                
        except Exception as e:
            self.has_client = False
            logger.error(f"❌ Error inicializando Groq client: {e}")
    
    def execute(self, arguments: dict) -> dict:
        """Ejecutar transcripción de audio"""
        try:
            if not self.has_client:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ **Groq Speech no disponible**\n\n"
                               "🔧 **Posibles causas:**\n"
                               "• GROQ_API_KEY no configurada\n"
                               "• Error de inicialización del cliente\n"
                               "• Dependencias faltantes\n\n"
                               "💡 **Solución:** Configura tu GROQ_API_KEY en las variables de entorno"
                    }]
                }
            
            audio_path = arguments.get('audio_path', '')
            language = arguments.get('language', 'es')  # español por defecto
            
            if not audio_path:
                return {
                    "content": [{
                        "type": "text",
                        "text": "❌ **Error:** Se requiere la ruta del archivo de audio (audio_path)"
                    }]
                }
            
            # Verificar que el archivo existe
            if not Path(audio_path).exists():
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ **Error:** El archivo de audio no existe: {audio_path}"
                    }]
                }
            
            # Transcribir audio
            result = self._transcribe_audio(audio_path, language)
            
            if result.get('success'):
                return {
                    "content": [{
                        "type": "text",
                        "text": f"🎤 **Transcripción completada**\n\n"
                               f"📁 **Archivo:** {Path(audio_path).name}\n"
                               f"🌐 **Idioma:** {language}\n"
                               f"🤖 **Modelo:** {self.model_name}\n"
                               f"⏱️ **Duración:** {result.get('duration', 'N/A')} segundos\n\n"
                               f"📝 **Transcripción:**\n"
                               f"{result.get('transcription', '')}"
                    }],
                    "transcription_data": {
                        "text": result.get('transcription', ''),
                        "language": language,
                        "duration": result.get('duration'),
                        "model": self.model_name,
                        "confidence": result.get('confidence', 'N/A')
                    }
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ **Error en transcripción**\n\n"
                               f"**Error:** {result.get('error', 'Error desconocido')}\n"
                               f"**Archivo:** {audio_path}\n\n"
                               f"🔧 **Posibles soluciones:**\n"
                               f"• Verificar formato de audio (MP3, WAV, M4A, etc.)\n"
                               f"• Comprobar que el archivo no esté corrupto\n"
                               f"• Intentar con un archivo más pequeño"
                    }]
                }
                
        except Exception as e:
            logger.error(f"Error en groq speech adapter: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ **Error del sistema de speech:** {str(e)}"
                }]
            }
    
    def _transcribe_audio(self, audio_path: str, language: str) -> dict:
        """Transcribir audio usando Groq Whisper"""
        try:
            # Preparar archivo para transcripción
            processed_file = self._prepare_audio_file(audio_path)
            
            if not processed_file:
                return {
                    'success': False,
                    'error': 'No se pudo procesar el archivo de audio'
                }
            
            # Transcribir con Groq
            with open(processed_file, "rb") as file:
                transcription = self.client.audio.transcriptions.create(
                    file=(Path(processed_file).name, file.read()),
                    model=self.model_name,
                    language=language,
                    response_format="verbose_json"
                )
            
            # Limpiar archivo temporal si se creó
            if processed_file != audio_path:
                Path(processed_file).unlink(missing_ok=True)
            
            return {
                'success': True,
                'transcription': transcription.text,
                'duration': transcription.duration if hasattr(transcription, 'duration') else None,
                'language': transcription.language if hasattr(transcription, 'language') else language
            }
            
        except Exception as e:
            logger.error(f"Error en transcripción Groq: {e}")
            return {
                'success': False,
                'error': f'Error de transcripción: {str(e)}'
            }
    
    def _prepare_audio_file(self, audio_path: str) -> Optional[str]:
        """Preparar archivo de audio para transcripción"""
        try:
            if not AUDIO_PROCESSING_AVAILABLE:
                # Sin pydub, solo verificar formato
                supported_formats = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}
                if Path(audio_path).suffix.lower() in supported_formats:
                    return audio_path
                else:
                    logger.error(f"Formato no soportado sin pydub: {Path(audio_path).suffix}")
                    return None
            
            # Con pydub, convertir si es necesario
            audio = AudioSegment.from_file(audio_path)
            
            # Si es muy largo, truncar a 25MB aprox (límite de Groq)
            max_duration_ms = 10 * 60 * 1000  # 10 minutos
            if len(audio) > max_duration_ms:
                audio = audio[:max_duration_ms]
                logger.info("Audio truncado a 10 minutos para cumplir límites de API")
            
            # Si no es MP3, convertir
            if not audio_path.lower().endswith('.mp3'):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                audio.export(temp_file.name, format="mp3", bitrate="128k")
                return temp_file.name
            
            return audio_path
            
        except Exception as e:
            logger.error(f"Error preparando archivo de audio: {e}")
            return None
    
    def process(self, arguments: dict) -> str:
        """Alias para execute - compatibilidad"""
        result = self.execute(arguments)
        if isinstance(result, dict) and "content" in result:
            return result["content"][0]["text"]
        return str(result)

# Función de prueba
def test_groq_speech():
    """Función para probar Groq Speech adapter"""
    print("🧪 Testing Groq Speech Adapter...")
    
    adapter = GroqSpeechAdapter()
    print(f"Cliente disponible: {adapter.has_client}")
    
    # Test básico
    result = adapter.execute({
        "audio_path": "test_audio.mp3",  # Archivo de ejemplo
        "language": "es"
    })
    
    print(f"Resultado: {result}")

if __name__ == "__main__":
    test_groq_speech()
