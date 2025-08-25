"""
Vision Adapter - meta-llama/llama-4-scout-17b-16e-instruct
===========================================================

Adapter para procesamiento de imágenes usando Llama 4 Scout.
Funciona completamente offline sin necesidad de servidor web.
"""

import os
import base64
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
load_dotenv(dotenv_path="C:/Users/h/Downloads/pagina ava/mod-pagina/.env", override=True)

class VisionAdapter:
    """
    Adapter para análisis de visión completamente offline
    
    Funcionalidades:
    - Análisis de imágenes sin servidor web
    - Procesamiento directo con base64
    - Múltiples tipos de análisis
    - Compatible con archivos locales
    """
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY no encontrada en variables de entorno")
        
        self.client = Groq(api_key=self.api_key)
        self.model_name = "meta-llama/llama-4-maverick-17b-128e-instruct"
        
        # Esquema para análisis
        self.schema = {
            "image_path": {"type": "string", "description": "Ruta completa de la imagen a analizar"},
            "prompt": {"type": "string", "description": "Pregunta o instrucción sobre la imagen", "default": "Describe detalladamente lo que ves en esta imagen"}
        }
        
        print(f"✅ VisionAdapter inicializado con modelo {self.model_name}")

    def custom_validation(self, params: dict) -> dict:
        """Valida parámetros de entrada"""
        image_path = params.get("image_path")
        if not image_path:
            raise ValueError("image_path es requerido")
        
        if not Path(image_path).exists():
            raise ValueError(f"La imagen no existe: {image_path}")
        
        # Validar formatos soportados
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        if Path(image_path).suffix.lower() not in valid_extensions:
            raise ValueError(f"Formato no soportado: {Path(image_path).suffix}")
        
        return {
            "image_path": image_path,
            "prompt": params.get("prompt", "Describe detalladamente lo que ves en esta imagen")
        }

    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analiza imagen usando modelo Llama de visión vía Groq"""
        
        # Leer y codificar imagen
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Detectar tipo de imagen
        image_ext = Path(image_path).suffix.lower()
        mime_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }.get(image_ext, 'image/jpeg')
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1024,
            temperature=0.3
        )
        
        return {
            "success": True,
            "analysis": response.choices[0].message.content,
            "model_used": self.model_name,
            "image_path": image_path,
            "prompt": prompt,
            "usage": response.usage.__dict__ if response.usage else {},
            "image_size": f"{os.path.getsize(image_path)} bytes"
        }

    def process(self, params: dict) -> dict:
        """Método principal del adaptador"""
        try:
            validated_params = self.custom_validation(params)
            prompt = validated_params.get("prompt")
            if not prompt or not prompt.strip():
                print(f"\n💬 ¿Qué quieres preguntar sobre la imagen '{Path(validated_params['image_path']).name}'?")
                prompt = input("❓ Tu pregunta: ").strip()
                if not prompt:
                    prompt = "Describe detalladamente lo que ves en esta imagen"
                validated_params["prompt"] = prompt

            result = self.analyze_image(
                validated_params["image_path"],
                validated_params["prompt"]
            )
            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "image_path": params.get("image_path"),
                "prompt": params.get("prompt")
            }

    def interactive_mode(self):
        """Modo interactivo para que el usuario suba imágenes y haga prompts"""
        print("\n🖼️ MODO INTERACTIVO - ANÁLISIS DE IMÁGENES")
        print("=" * 50)
        print("📁 Formatos soportados: PNG, JPG, JPEG, GIF, BMP, WEBP")
        print("❌ Escribe 'quit' para salir")
        print("🔄 Escribe 'cambiar' para cambiar de imagen")
        
        current_image = None
        
        while True:
            # Si no hay imagen cargada, pedir una
            if not current_image:
                print("\n📸 Por favor, proporciona la ruta de la imagen:")
                image_path = input("🖼️ Ruta: ").strip()
                
                if image_path.lower() == 'quit':
                    print("👋 ¡Hasta luego!")
                    break
                
                # Validar imagen
                if not Path(image_path).exists():
                    print("❌ La imagen no existe. Intenta de nuevo.")
                    continue
                
                valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
                if Path(image_path).suffix.lower() not in valid_extensions:
                    print("❌ Formato no soportado. Intenta de nuevo.")
                    continue
                
                current_image = image_path
                print(f"✅ Imagen cargada: {Path(image_path).name}")
                print(f"📊 Tamaño: {os.path.getsize(image_path)} bytes")
            
            # Pedir prompt al usuario
            print(f"\n🔍 Imagen actual: {Path(current_image).name}")
            print("💬 ¿Qué quieres preguntar sobre esta imagen?")
            prompt = input("❓ Tu pregunta: ").strip()
            
            if prompt.lower() == 'quit':
                print("👋 ¡Hasta luego!")
                break
            elif prompt.lower() == 'cambiar':
                current_image = None
                continue
            elif not prompt:
                prompt = "Describe detalladamente lo que ves en esta imagen"
            
            # Analizar imagen
            print("\n🔄 Analizando imagen...")
            params = {"image_path": current_image, "prompt": prompt}
            result = self.process(params)
            
            if result["success"]:
                print(f"\n🤖 Respuesta del modelo:")
                print("-" * 50)
                print(result["analysis"])
                print("-" * 50)
                print(f"⚡ Tokens usados: {result['usage'].get('total_tokens', 'N/A')}")
                print(f"⏱️ Tiempo: {result['usage'].get('total_time', 'N/A'):.2f}s" if result['usage'].get('total_time') else "")
            else:
                print(f"❌ Error: {result['error']}")
            
            print("\n" + "="*50)

# Pruebas y modo interactivo
if __name__ == "__main__":
    print("🧪 Testing VisionAdapter con Llama via Groq...")
    
    try:
        adapter = VisionAdapter()
        
        # Preguntar al usuario qué modo quiere
        print("\n🎯 ¿Qué modo quieres usar?")
        print("1. Modo interactivo (recomendado)")
        print("2. Modo de prueba automática")
        
        choice = input("Elige (1 o 2): ").strip()
        
        if choice == "1":
            adapter.interactive_mode()
        else:
            # Modo de prueba automática
            test_params = {
                "image_path": "D:/ComfyUI-Easy-Install/ComfyUI-Easy-Install/ComfyUI-Easy-Install/ComfyUI/output/wan22_00306.png",
                "prompt": "¿Qué objetos puedes identificar en esta imagen?"
            }
            
            print(f"\n🔍 Analizando imagen de prueba...")
            result = adapter.process(test_params)
            print(f"\n📊 Resultado:")
            if result["success"]:
                print(f"✅ Análisis: {result['analysis']}")
            else:
                print(f"❌ Error: {result['error']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
