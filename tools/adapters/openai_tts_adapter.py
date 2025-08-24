"""
Adaptador TTS usando OpenAI TTS con soporte para instructions y streaming (API oficial)
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.base_tool import BaseTool
import os
import base64
import logging
import tempfile
import time
from openai import OpenAI
import pygame
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class OpenAITTSAdapter(BaseTool):
    """Adaptador TTS usando OpenAI TTS con soporte para gpt-4o-mini-tts, instructions y streaming"""
    
    name = "openai_tts_adapter"
    description = "OpenAI TTS - Síntesis de voz avanzada con 11 voces, acentos colombianos/mexicanos/argentinos, streaming y modelo gpt-4o-mini-tts con instructions"
    
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["text_to_speech", "get_voices"],
                "description": "Acción a realizar"
            },
            "text": {
                "type": "string", 
                "description": "Texto para convertir a voz"
            },
            "voice": {
                "type": "string",
                "enum": ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"],
                "default": "coral",
                "description": "Voz de OpenAI a usar (11 voces disponibles)"
            },
            "model": {
                "type": "string",
                "default": "gpt-4o-mini-tts",
                "enum": ["gpt-4o-mini-tts"],
                "description": "Modelo TTS de OpenAI (solo gpt-4o-mini-tts)"
            },
            "speed": {
                "type": "number",
                "minimum": 0.25,
                "maximum": 4.0,
                "default": 1.0,
                "description": "Velocidad de reproducción (0.25 a 4.0)"
            },
            "response_format": {
                "type": "string",
                "enum": ["mp3", "opus", "aac", "flac"],
                "default": "mp3",
                "description": "Formato de audio de salida"
            },
            "return_audio": {
                "type": "boolean",
                "default": False,
                "description": "Retornar audio en base64"
            },
            "play_audio": {
                "type": "boolean",
                "default": True,
                "description": "Reproducir audio inmediatamente"
            },
            "instructions": {
                "type": "string",
                "default": "",
                "description": "Instrucciones específicas para el habla (acento, tono, emoción, etc.)"
            },
            "preset_accent": {
                "type": "string",
                "enum": ["colombiano", "mexicano", "argentino", "español", "neutral", "custom"],
                "default": "neutral",
                "description": "Acento preconfigurado o custom para usar instructions personalizadas"
            }
        },
        "required": ["action", "text"]
    }
    
    def __init__(self, openai_api_key=None):
        """Inicializar adaptador OpenAI TTS"""
        # ✅ FIXED: Initialize logger properly
        self.logger = logging.getLogger(__name__)
        
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
        if not api_key:
            self.logger.error("No OpenAI API key found")
            raise ValueError("OpenAI API key is required")
            
        self.client = OpenAI(api_key=api_key)
        
        # Inicializar pygame para reproducción
        try:
            pygame.mixer.init()
            self.logger.info("✅ pygame mixer inicializado")
        except Exception as e:
            self.logger.warning(f"⚠️ pygame no disponible: {e}")
    
    def process(self, params):
        """Procesar operaciones TTS con OpenAI"""
        action = params.get("action")
        
        if action == "text_to_speech":
            return self._openai_text_to_speech(params)
        elif action == "get_voices":
            return self._get_openai_voices()
        else:
            return {
                "success": False,
                "error": f"Acción no reconocida: {action}"
            }
    
    def _get_instructions(self, preset_accent, custom_instructions=""):
        """Generar instructions basadas en acento preconfigurado o personalizado"""
        
        preset_instructions = {
            "colombiano": "Habla con acento colombiano amigable y cálido, con entonación melodiosa característica de Colombia. Usa un tono alegre y pausado.",
            "mexicano": "Habla con acento mexicano neutro, con entonación clara y ritmo pausado típico del español mexicano.",
            "argentino": "Habla con acento argentino rioplatense, con entonación característica y ritmo dinámico del español argentino.",
            "español": "Habla con acento español peninsular neutro, con pronunciación clara y entonación característica de España.",
            "neutral": "Speak in a natural and clear tone."
        }
        
        if preset_accent == "custom":
            return custom_instructions
        else:
            return preset_instructions.get(preset_accent, "Speak in a natural and clear tone.")
    
    def _openai_text_to_speech(self, params):
        """Convertir texto a voz usando OpenAI TTS con streaming e instructions (API oficial)"""
        try:
            text = params.get("text", "")
            voice = params.get("voice", "coral")
            model = params.get("model", "gpt-4o-mini-tts")
            speed = params.get("speed", 1.0)
            response_format = params.get("response_format", "mp3")
            return_audio = params.get("return_audio", False)
            play_audio = params.get("play_audio", True)
            preset_accent = params.get("preset_accent", "neutral")
            custom_instructions = params.get("instructions", "")
            
            if not text:
                return {
                    "success": False,
                    "error": "Texto requerido",
                    "message": "❌ No se proporcionó texto para convertir"
                }
            
            # Generar instructions finales
            final_instructions = self._get_instructions(preset_accent, custom_instructions)
            
            print(f"🎙️ Generando voz con OpenAI TTS...")
            print(f"📝 Texto: {text[:50]}{'...' if len(text) > 50 else ''}")
            print(f"🗣️ Voz: {voice}")
            print(f"🤖 Modelo: {model}")
            print(f"🌍 Acento: {preset_accent}")
            
            # Crear archivo temporal
            temp_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=f".{response_format}"
            )
            temp_file.close()
            speech_file_path = Path(temp_file.name)
            
            try:
                # ✅ Try streaming first, fallback to regular if not available
                try:
                    with self.client.audio.speech.with_streaming_response.create(
                        model=model,
                        voice=voice,
                        input=text,
                        instructions=final_instructions,
                        speed=speed,
                        response_format=response_format
                    ) as response:
                        response.stream_to_file(speech_file_path)
                    
                    print("✅ Audio generado con streaming")
                    
                except AttributeError:
                    # Fallback to regular TTS without streaming/instructions
                    print("⚠️ Streaming no disponible, usando TTS estándar...")
                    response = self.client.audio.speech.create(
                        model="tts-1",  # Fallback model
                        voice=voice,
                        input=text,
                        speed=speed,
                        response_format=response_format
                    )
                    
                    with open(speech_file_path, 'wb') as f:
                        f.write(response.content)
                    
                    print("✅ Audio generado (modo estándar)")
                
            except Exception as model_error:
                self.logger.error(f"Error con modelo {model}: {model_error}")
                return {
                    "success": False,
                    "error": str(model_error),
                    "message": f"❌ Error OpenAI TTS: {str(model_error)}"
                }
            
            audio_base64 = None
            
            # Reproducir audio si se solicita
            if play_audio:
                try:
                    print("🔊 Reproduciendo audio...")
                    pygame.mixer.music.load(str(speech_file_path))
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        pygame.time.wait(100)
                    
                    pygame.mixer.music.unload()
                    time.sleep(0.1)
                    print("✅ Audio reproducido exitosamente")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Error reproduciendo audio: {e}")
                    print(f"⚠️ Error reproducción: {e}")
            
            # Convertir a base64 si se solicita
            if return_audio:
                try:
                    with open(speech_file_path, 'rb') as f:
                        audio_bytes = f.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode()
                except Exception as e:
                    self.logger.warning(f"Error leyendo archivo para base64: {e}")
            
            # Limpiar archivo temporal
            self._cleanup_file(speech_file_path)
            
            return {
                "success": True,
                "action": "text_to_speech",
                "text": text,
                "voice": voice,
                "model": model,
                "speed": speed,
                "preset_accent": preset_accent,
                "instructions": final_instructions,
                "format": response_format,
                "audio_base64": audio_base64,
                "message": f"🎙️ OpenAI TTS ({voice}, {preset_accent}): '{text[:30]}...'" if len(text) > 30 else f"🎙️ OpenAI TTS ({voice}, {preset_accent}): '{text}'"
            }
            
        except Exception as e:
            self.logger.error(f"Error general en TTS: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Error OpenAI TTS: {str(e)}"
            }
    
    def _get_openai_voices(self):
        """Obtener voces disponibles de OpenAI (11 voces actualizadas)"""
        voices_info = [
            {
                "id": "alloy",
                "name": "Alloy",
                "description": "Neutral, balanced voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "ash",
                "name": "Ash",
                "description": "Clear, articulate voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "ballad",
                "name": "Ballad",
                "description": "Melodic, storytelling voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "coral",
                "name": "Coral",
                "description": "Warm, friendly voice with excellent instruction support",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "echo",
                "name": "Echo",
                "description": "Male voice with character",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "fable",
                "name": "Fable", 
                "description": "Storytelling voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "nova",
                "name": "Nova",
                "description": "Young, energetic voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "onyx",
                "name": "Onyx",
                "description": "Deep, authoritative voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "sage",
                "name": "Sage",
                "description": "Wise, mature voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            },
            {
                "id": "shimmer",
                "name": "Shimmer",
                "description": "Bright, cheerful voice",
                "type": "TTS",
                "provider": "OpenAI",
                "supports_instructions": True
            }
        ]
        
        return {
            "success": True,
            "action": "get_voices",
            "voices": voices_info,
            "total_voices": len(voices_info),
            "message": f"🎭 OpenAI TTS: {len(voices_info)} voces disponibles (todas con soporte instructions y streaming)"
        }
    
    def _cleanup_file(self, file_path):
        """Limpiar archivo temporal con reintentos"""
        if not file_path or not Path(file_path).exists():
            return
            
        for attempt in range(3):
            try:
                time.sleep(0.1)
                os.unlink(file_path)
                break
            except PermissionError:
                if attempt == 2:
                    self.logger.warning(f"No se pudo eliminar archivo: {file_path}")
                else:
                    time.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"Error eliminando archivo: {e}")
                break


def test_openai_tts_adapter():
    """Probar el adaptador OpenAI TTS con streaming e instructions"""
    print("🧪 PRUEBA OPENAI TTS ADAPTER - STREAMING E INSTRUCTIONS")
    print("=" * 70)
    
    # Verificar clave API
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_KEY")
    if not api_key:
        print("❌ ERROR: No se encontró la clave de OpenAI")
        print("💡 Asegúrate de tener OPENAI_API_KEY en tu .env")
        return
    
    print(f"✅ Clave API encontrada: {api_key[:20]}...")
    
    # Verificar versión de OpenAI
    try:
        import openai
        print(f"📦 Versión OpenAI: {openai.__version__}")
    except:
        print("⚠️ No se pudo verificar la versión de OpenAI")
    
    # Inicializar adaptador
    try:
        adapter = OpenAITTSAdapter()
        print("✅ Adaptador inicializado correctamente")
    except Exception as e:
        print(f"❌ Error inicializando: {e}")
        return
    
    print("\n" + "─" * 70)
    
    # TEST 1: Audio con acento colombiano
    print("📋 TEST 1: AUDIO CON ACENTO COLOMBIANO (STREAMING)")
    
    test_colombiano = {
        "action": "text_to_speech",
        "text": "¡Hola parcero! Soy AVA Assistant y te saludo con mucho cariño desde Colombia",
        "voice": "coral",
        "model": "gpt-4o-mini-tts",
        "preset_accent": "colombiano",
        "play_audio": True,
        "return_audio": False
    }
    
    try:
        print("🎙️ Generando audio con acento colombiano (streaming)...")
        result = adapter.process(test_colombiano)
        if result.get("success"):
            print("✅ Audio generado con streaming y reproducido")
            print(f"📝 Texto: {result.get('text')}")
            print(f"🗣️ Voz: {result.get('voice')}")
            print(f"🤖 Modelo: {result.get('model')}")
            print(f"🌍 Acento: {result.get('preset_accent')}")
            print(f"📋 Instructions: {result.get('instructions')}")
            print(f"🌊 Streaming: {result.get('streaming', False)}")
        else:
            print(f"❌ Error: {result.get('error')}")
            if "solution" in result:
                print(f"💡 Solución: {result.get('solution')}")
    except Exception as e:
        print(f"❌ Excepción: {e}")
    
    print("\n" + "─" * 70)
    
    # TEST 2: Instructions personalizadas
    print("📋 TEST 2: INSTRUCTIONS PERSONALIZADAS (STREAMING)")
    
    test_custom = {
        "action": "text_to_speech",
        "text": "Esta es una prueba increíble del nuevo sistema de voz con streaming",
        "voice": "coral",
        "model": "gpt-4o-mini-tts",
        "preset_accent": "custom",
        "instructions": "Speak in a cheerful and positive tone, like you're excited to share good news with a friend.",
        "play_audio": True,
        "return_audio": False
    }
    
    try:
        print("🎙️ Generando audio con instructions personalizadas...")
        result = adapter.process(test_custom)
        if result.get("success"):
            print("✅ Audio con instructions personalizadas generado")
            print(f"📋 Instructions: {result.get('instructions')}")
            print(f"🌊 Streaming: {result.get('streaming', False)}")
        else:
            print(f"❌ Error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Excepción: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 PRUEBA COMPLETADA")
    print("\n🔧 CONFIGURACIÓN REQUERIDA:")
    print("   📦 pip install --upgrade openai")
    print("   🤖 Modelo: gpt-4o-mini-tts únicamente")
    print("   🌊 Streaming: with_streaming_response.create()")
    print("   📋 Instructions: Soporte completo para acentos")


if __name__ == "__main__":
    test_openai_tts_adapter()