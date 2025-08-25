"""
Gmail Adapter - Versión Cloud Run Compatible
===========================================
Adapter simplificado para funcionar tanto local como en Cloud Run
"""

import os
import base64
import json
import logging
from typing import Dict, Any
from pathlib import Path

# Configurar logging
logger = logging.getLogger(__name__)

# Intentar importar dependencias de Google
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    GOOGLE_APIS_AVAILABLE = True
except ImportError as e:
    GOOGLE_APIS_AVAILABLE = False
    logger.warning(f"Google APIs no disponibles: {e}")

class GmailAdapter:
    """Gmail Adapter compatible con Cloud Run"""
    
    def __init__(self):
        self.description = "Ava Bot Gmail tool - Cloud Run compatible"
        self.service = None
        
        if GOOGLE_APIS_AVAILABLE:
            try:
                self._init_gmail_service()
                self.has_credentials = True
            except Exception as e:
                logger.error(f"Error inicializando Gmail service: {e}")
                self.has_credentials = False
        else:
            self.has_credentials = False
            
    def _init_gmail_service(self):
        """Inicializar servicio Gmail usando variables de entorno"""
        # Obtener credenciales desde variables de entorno
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN')
        token_uri = os.getenv('GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token')
        
        if not all([client_id, client_secret, refresh_token]):
            logger.error("Faltan variables de entorno OAuth para Gmail")
            return
            
        # Crear credenciales OAuth2
        creds_info = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "token_uri": token_uri,
            "type": "authorized_user"
        }
        
        creds = Credentials.from_authorized_user_info(
            creds_info, 
            ['https://www.googleapis.com/auth/gmail.send']
        )
        
        # Refrescar token si es necesario
        if creds.expired:
            creds.refresh(Request())
            
        # Crear servicio Gmail
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("✅ Gmail service inicializado correctamente")
        
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Método principal del adapter"""
        try:
            if not self.has_credentials or not self.service:
                return self._fallback_response(arguments)
                
            # Parámetros del email
            to = arguments.get('to', '')
            subject = arguments.get('subject', 'Mensaje de Ava')
            body = arguments.get('body', '')
            
            if not to:
                return {
                    "content": [{"type": "text", "text": "❌ **Error:** Campo 'to' es requerido"}]
                }
            
            # Enviar email simple por ahora (sin adjuntos para mayor compatibilidad)
            return self._send_simple_email(to, subject, body)
            
        except Exception as e:
            logger.error(f"Error en Gmail execute: {e}")
            return {
                "content": [{"type": "text", "text": f"❌ **Error Gmail:** {str(e)}"}]
            }
    
    def _send_simple_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Enviar email simple usando Gmail API"""
        try:
            # Crear mensaje
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))
            
            # Codificar mensaje
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Enviar usando Gmail API
            message_body = {'raw': raw_message}
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message_body
            ).execute()
            
            message_id = sent_message.get('id', 'N/A')
            
            return {
                "content": [{"type": "text", "text": f"""📧 **Email enviado exitosamente**

📧 **Para:** {to}
📝 **Asunto:** {subject}
✅ **Estado:** Entregado
🆔 **ID:** {message_id}
🌐 **Servidor:** Cloud Run"""}]
            }
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return {
                "content": [{"type": "text", "text": f"❌ **Error enviando email:** {str(e)}"}]
            }
    
    def _fallback_response(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Respuesta de fallback cuando Gmail no está disponible"""
        to = arguments.get('to', 'destinatario@example.com')
        subject = arguments.get('subject', 'Mensaje de Ava')
        body = arguments.get('body', '')
        
        return {
            "content": [{"type": "text", "text": f"""📧 **Solicitud de email procesada**

📧 **Para:** {to}
📝 **Asunto:** {subject}
📄 **Mensaje:**
{body}

⚠️ **Gmail API no disponible en este momento**
🔧 **Posibles causas:**
- Variables de entorno OAuth no configuradas
- Dependencias de Google APIs faltantes
- Error de autenticación

📋 **Acción requerida:** Configura las variables de entorno en Cloud Run:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET  
- GOOGLE_REFRESH_TOKEN"""}]
        }

# Función de prueba
if __name__ == "__main__":
    print("🧪 Testing Gmail Adapter - Cloud Run Compatible")
    
    try:
        adapter = GmailAdapter()
        print(f"Gmail Adapter: {adapter.description}")
        print(f"Credenciales: {adapter.has_credentials}")
        print(f"Google APIs: {GOOGLE_APIS_AVAILABLE}")
        
        # Test
        result = adapter.execute({
            "to": "test@example.com",
            "subject": "Test desde Cloud Run",
            "body": "Probando Gmail adapter compatible con Cloud Run"
        })
        
        print("\nResultado:")
        print(result["content"][0]["text"])
        
    except Exception as e:
        print(f"Error: {e}")
