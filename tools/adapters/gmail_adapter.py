import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any

# ✅ CONFIGURACIÓN ROBUSTA DE RUTAS
def setup_paths():
    """Configurar rutas de manera robusta para funcionar en cualquier contexto"""
    current_file = Path(__file__).resolve()
    
    # Detectar si estamos en la estructura ava_bot/tools/adapters/ o directamente en mcp_server/
    possible_structures = [
        # Estructura 1: ava_bot/tools/adapters/gmail_adapter.py
        {
            'adapters_dir': current_file.parent,
            'tools_dir': current_file.parent.parent,
            'ava_bot_dir': current_file.parent.parent.parent,
            'project_root': current_file.parent.parent.parent.parent
        },
        # Estructura 2: mcp_server/tools/adapters/gmail_adapter.py  
        {
            'adapters_dir': current_file.parent,
            'tools_dir': current_file.parent.parent,
            'mcp_server_dir': current_file.parent.parent.parent,
            'project_root': current_file.parent.parent.parent.parent
        }
    ]
    
    paths_added = []
    
    for structure in possible_structures:
        for key, path in structure.items():
            if path.exists():
                str_path = str(path)
                if str_path not in sys.path:
                    sys.path.insert(0, str_path)
                    paths_added.append(f"{key}: {str_path}")
                
                # Agregar subdirectorios comunes
                common_subdirs = ['utils', 'nodes', 'nodes/email', 'tools', 'tools/adapters']
                for subdir in common_subdirs:
                    subdir_path = path / subdir
                    if subdir_path.exists():
                        str_subdir = str(subdir_path)
                        if str_subdir not in sys.path:
                            sys.path.insert(0, str_subdir)
                            paths_added.append(f"{subdir}: {str_subdir}")
    
    return paths_added

# Configurar rutas al importar
paths_added = setup_paths()

# ✅ CONFIGURAR LOGGING
logger = logging.getLogger(__name__)

# ✅ INTENTAR IMPORTAR DEPENDENCIAS CON FALLBACKS MÚLTIPLES
OAUTH_HELPER_AVAILABLE = False
GMAIL_SENDER_AVAILABLE = False
oauth_helper_error = None
gmail_sender_error = None

# Intentar importar oauth_helper
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
    logger.info("✅ oauth_helper importado correctamente")
except ImportError as e:
    oauth_helper_error = str(e)
    logger.warning(f"⚠️ oauth_helper no disponible: {e}")

# Intentar importar GmailSender con múltiples rutas
gmail_sender_import_attempts = [
    "nodes.email.gmail_sender",
    "gmail_sender", 
    "email.gmail_sender",
    "ava_bot.nodes.email.gmail_sender"
]

for attempt in gmail_sender_import_attempts:
    try:
        module = __import__(attempt, fromlist=['GmailSender'])
        GmailSender = getattr(module, 'GmailSender')
        GMAIL_SENDER_AVAILABLE = True
        logger.info(f"✅ GmailSender importado desde: {attempt}")
        break
    except (ImportError, AttributeError) as e:
        gmail_sender_error = str(e)
        continue

if not GMAIL_SENDER_AVAILABLE:
    logger.error(f"❌ No se pudo importar GmailSender. Último error: {gmail_sender_error}")

# ✅ IMPORTACIONES ESTÁNDAR
try:
    import base64
    import json
    from datetime import datetime
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import mimetypes
    import smtplib
except ImportError as e:
    logger.error(f"❌ Error importando librerías estándar: {e}")

# ✅ CLASE PRINCIPAL CON MÚLTIPLES FALLBACKS
class GmailAdapter:
    def __init__(self):
        """Inicialización robusta con múltiples fallbacks"""
        self.description = "Ava Bot Gmail - Envío de emails con OAuth y SMTP"
        self.has_credentials = False
        self.gmail_sender = None
        self.smtp_config = None
        self._connection_tested = False
        
        # Intentar inicializar en orden de preferencia
        self._init_oauth_gmail()
        if not self.has_credentials:
            self._init_smtp_gmail()
        
        logger.info(f"✅ GmailAdapter inicializado - Credenciales: {self.has_credentials}")
    
    def _init_oauth_gmail(self):
        """Inicializar con OAuth si está disponible"""
        if not (OAUTH_HELPER_AVAILABLE and GMAIL_SENDER_AVAILABLE):
            return
            
        try:
            self.gmail_sender = GmailSender()
            self.has_credentials = True
            self.description += " (OAuth Mode)"
            logger.info("✅ Gmail OAuth inicializado")
        except Exception as e:
            logger.warning(f"⚠️ Error inicializando OAuth Gmail: {e}")
    
    def _init_smtp_gmail(self):
        """Inicializar con SMTP como fallback"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            gmail_user = os.getenv("GMAIL_USER")
            gmail_password = os.getenv("GMAIL_APP_PASSWORD")
            
            if gmail_user and gmail_password:
                self.smtp_config = {
                    'user': gmail_user,
                    'password': gmail_password,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587
                }
                self.has_credentials = True
                self.description += " (SMTP Mode)"
                logger.info("✅ Gmail SMTP configurado")
            else:
                logger.warning("⚠️ Variables GMAIL_USER/GMAIL_APP_PASSWORD no encontradas")
                
        except Exception as e:
            logger.warning(f"⚠️ Error configurando SMTP: {e}")
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Método principal de ejecución"""
        try:
            # Test de conexión solo la primera vez
            if not self._connection_tested:
                self._test_connection()
                self._connection_tested = True
            
            action = arguments.get('action', 'send')
            
            if action == 'send':
                return self._handle_send_action(arguments)
            elif action == 'test':
                return self._handle_test_action()
            else:
                return {
                    "content": [{"type": "text", "text": f"❌ Acción no reconocida: {action}"}]
                }
                
        except Exception as e:
            logger.error(f"Error en execute: {e}")
            return {
                "content": [{"type": "text", "text": f"❌ Error del sistema: {str(e)}"}]
            }
    
    def _handle_send_action(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Manejar acción de envío de email"""
        to = arguments.get('to')
        subject = arguments.get('subject', 'Mensaje de Ava Bot')
        body = arguments.get('body', '')
        
        if not to:
            return {
                "content": [{"type": "text", "text": "❌ Campo 'to' requerido"}]
            }
        
        if not self.has_credentials:
            return self._generate_manual_email_response(to, subject, body)
        
        # Detectar si necesita adjuntos
        send_latest_image = arguments.get('send_latest_image', False)
        attachment_data = arguments.get('attachment_data')
        
        if send_latest_image:
            return self._send_with_latest_image(to, subject, body)
        elif attachment_data:
            return self._send_with_attachments(to, subject, body, attachment_data)
        else:
            return self._send_simple_email(to, subject, body)
    
    def _send_simple_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Enviar email simple"""
        try:
            if self.gmail_sender:
                # Usar OAuth Gmail
                result = self.gmail_sender.send_email(to=to, subject=subject, body=body)
                if isinstance(result, dict) and result.get('success'):
                    return {
                        "content": [{"type": "text", "text": f"""✅ **Email enviado (OAuth)**

📧 **Para:** {to}
📝 **Asunto:** {subject}
🆔 **ID:** {result.get('message_id', 'N/A')}
✅ **Estado:** Entregado"""}]
                    }
                else:
                    error_msg = result.get('error', 'Error desconocido') if isinstance(result, dict) else str(result)
                    return self._send_smtp_fallback(to, subject, body, f"OAuth falló: {error_msg}")
            
            elif self.smtp_config:
                # Usar SMTP directo
                return self._send_smtp_email(to, subject, body)
            
            else:
                return {
                    "content": [{"type": "text", "text": "❌ **No hay método de envío configurado**"}]
                }
                
        except Exception as e:
            logger.error(f"Error enviando email simple: {e}")
            return self._send_smtp_fallback(to, subject, body, f"Error: {str(e)}")
    
    def _send_smtp_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Enviar email usando SMTP directo"""
        try:
            msg = MIMEText(body, 'plain', 'utf-8')
            msg['From'] = self.smtp_config['user']
            msg['To'] = to
            msg['Subject'] = subject
            
            with smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port']) as server:
                server.starttls()
                server.login(self.smtp_config['user'], self.smtp_config['password'])
                server.send_message(msg)
            
            return {
                "content": [{"type": "text", "text": f"""✅ **Email enviado (SMTP)**

📧 **Para:** {to}
📝 **Asunto:** {subject}
📡 **Método:** SMTP directo
✅ **Estado:** Entregado"""}]
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                "content": [{"type": "text", "text": "❌ **Error de autenticación SMTP**. Verifica GMAIL_USER y GMAIL_APP_PASSWORD"}]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ **Error SMTP:** {str(e)}"}]
            }
    
    def _send_smtp_fallback(self, to: str, subject: str, body: str, error_msg: str) -> Dict[str, Any]:
        """Fallback a SMTP si OAuth falla"""
        if self.smtp_config:
            logger.info(f"Intentando SMTP fallback debido a: {error_msg}")
            return self._send_smtp_email(to, subject, body)
        else:
            return {
                "content": [{"type": "text", "text": f"❌ **Email falló:** {error_msg}\n\n⚠️ **Sin fallback SMTP configurado**"}]
            }
    
    def _send_with_latest_image(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Enviar email con la última imagen generada"""
        try:
            # Intentar importar FileManagerAdapter dinámicamente
            file_manager_import_attempts = [
                "file_adapter",
                "tools.adapters.file_adapter", 
                "ava_bot.tools.adapters.file_adapter"
            ]
            
            file_manager = None
            for attempt in file_manager_import_attempts:
                try:
                    module = __import__(attempt, fromlist=['FileManagerAdapter'])
                    FileManagerAdapter = getattr(module, 'FileManagerAdapter')
                    file_manager = FileManagerAdapter()
                    break
                except (ImportError, AttributeError):
                    continue
            
            if not file_manager:
                return {
                    "content": [{"type": "text", "text": "❌ **FileManagerAdapter no disponible** para obtener imagen"}]
                }
            
            # Obtener última imagen
            latest_result = file_manager.execute({"action": "get_latest_image"})
            
            if "filename" not in latest_result:
                return {
                    "content": [{"type": "text", "text": "❌ **No se encontró ninguna imagen generada**"}]
                }
            
            # Preparar datos de adjunto
            attachment_data = {
                "method": "file_path",
                "filename": latest_result["filename"],
                "filepath": latest_result["filepath"],
                "content_type": "image/png"
            }
            
            return self._send_with_attachments(to, subject, body, attachment_data)
            
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ **Error obteniendo imagen:** {str(e)}"}]
            }
    
    def _send_with_attachments(self, to: str, subject: str, body: str, attachment_data: Dict) -> Dict[str, Any]:
        """Enviar email con adjuntos"""
        try:
            # Crear mensaje MIME
            message = MIMEMultipart()
            message['From'] = self.smtp_config['user'] if self.smtp_config else 'ava@bot.com'
            message['To'] = to
            message['Subject'] = subject
            
            # Agregar cuerpo
            message.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Procesar adjunto
            method = attachment_data.get('method', 'base64')
            filename = attachment_data.get('filename', 'attachment')
            
            if method == 'file_path':
                filepath = attachment_data.get('filepath')
                if filepath and os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        file_data = f.read()
                    
                    content_type = attachment_data.get('content_type', 'application/octet-stream')
                    main_type, sub_type = content_type.split('/', 1)
                    
                    attachment = MIMEBase(main_type, sub_type)
                    attachment.set_payload(file_data)
                    encoders.encode_base64(attachment)
                    attachment.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    
                    message.attach(attachment)
                    
                    # Enviar usando el método disponible
                    if self.gmail_sender and hasattr(self.gmail_sender, 'service'):
                        # Usar Gmail API
                        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                        message_body = {'raw': raw_message}
                        
                        sent_message = self.gmail_sender.service.users().messages().send(
                            userId='me',
                            body=message_body
                        ).execute()
                        
                        return {
                            "content": [{"type": "text", "text": f"""✅ **Email con adjunto enviado (OAuth)**

📧 **Para:** {to}
📝 **Asunto:** {subject}
📎 **Adjunto:** {filename} ({len(file_data)} bytes)
🆔 **ID:** {sent_message.get('id', 'N/A')}"""}]
                        }
                    
                    elif self.smtp_config:
                        # Usar SMTP
                        with smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port']) as server:
                            server.starttls()
                            server.login(self.smtp_config['user'], self.smtp_config['password'])
                            server.send_message(message)
                        
                        return {
                            "content": [{"type": "text", "text": f"""✅ **Email con adjunto enviado (SMTP)**

📧 **Para:** {to}
📝 **Asunto:** {subject}
📎 **Adjunto:** {filename} ({len(file_data)} bytes)"""}]
                        }
                    
                    else:
                        return {
                            "content": [{"type": "text", "text": "❌ **No hay método de envío configurado**"}]
                        }
                
                else:
                    return {
                        "content": [{"type": "text", "text": f"❌ **Archivo no encontrado:** {filepath}"}]
                    }
            
            else:
                return {
                    "content": [{"type": "text", "text": f"❌ **Método de adjunto no soportado:** {method}"}]
                }
                
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"❌ **Error enviando con adjuntos:** {str(e)}"}]
            }
    
    def _generate_manual_email_response(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Generar respuesta para envío manual cuando no hay credenciales"""
        return {
            "content": [{"type": "text", "text": f"""📧 **Solicitud de email procesada**

📧 **Para:** {to}
📝 **Asunto:** {subject}
📄 **Mensaje:**
{body}

⚠️ **Gmail no configurado** - Copia y envía manualmente

🔧 **Para envío automático, configura:**
• OAuth: Coloca credenciales en utils/oauth_helper.py
• SMTP: Agrega GMAIL_USER y GMAIL_APP_PASSWORD al .env"""}]
        }
    
    def _test_connection(self):
        """Test de conexión"""
        logger.info("🧪 GMAIL CONNECTION TEST")
        logger.info("=" * 40)
        
        if OAUTH_HELPER_AVAILABLE:
            try:
                creds = get_google_credentials(['https://www.googleapis.com/auth/gmail.send'])
                logger.info(f"✅ OAuth disponible: {bool(creds)}")
            except Exception as e:
                logger.warning(f"⚠️ OAuth error: {e}")
        else:
            logger.warning(f"⚠️ OAuth helper no disponible: {oauth_helper_error}")
        
        logger.info(f"🔧 Gmail sender: {'✅' if self.gmail_sender else '❌'}")
        logger.info(f"📧 SMTP config: {'✅' if self.smtp_config else '❌'}")
        logger.info(f"🔑 Credenciales: {'✅' if self.has_credentials else '❌'}")
        logger.info("=" * 40)
    
    def _handle_test_action(self) -> Dict[str, Any]:
        """Manejar acción de test"""
        status_lines = [
            "🧪 **GMAIL ADAPTER STATUS**",
            "",
            f"📊 **Rutas agregadas:** {len(paths_added)}",
            f"🔧 **OAuth disponible:** {'✅' if OAUTH_HELPER_AVAILABLE else '❌'}",
            f"📬 **GmailSender disponible:** {'✅' if GMAIL_SENDER_AVAILABLE else '❌'}",
            f"📧 **SMTP configurado:** {'✅' if self.smtp_config else '❌'}",
            f"🔑 **Credenciales activas:** {'✅' if self.has_credentials else '❌'}",
            "",
            f"📝 **Descripción:** {self.description}"
        ]
        
        if not OAUTH_HELPER_AVAILABLE:
            status_lines.extend([
                "",
                f"⚠️ **OAuth Error:** {oauth_helper_error}"
            ])
        
        if not GMAIL_SENDER_AVAILABLE:
            status_lines.extend([
                "",
                f"⚠️ **GmailSender Error:** {gmail_sender_error}"
            ])
        
        if paths_added:
            status_lines.extend([
                "",
                "📁 **Rutas agregadas:**"
            ])
            status_lines.extend([f"   • {path}" for path in paths_added[:5]])  # Mostrar solo las primeras 5
        
        return {
            "content": [{"type": "text", "text": "\n".join(status_lines)}]
        }
    
    def process(self, arguments: Dict[str, Any]) -> str:
        """Método de compatibilidad"""
        result = self.execute(arguments)
        if isinstance(result, dict) and "content" in result:
            return result["content"][0]["text"]
        return str(result)

# ✅ FUNCIÓN DE PRUEBA
if __name__ == "__main__":
    print("🧪 PROBANDO GMAIL ADAPTER CORREGIDO")
    print("=" * 50)
    
    try:
        adapter = GmailAdapter()
        
        # Test de estado
        test_result = adapter.execute({"action": "test"})
        print(test_result["content"][0]["text"])
        
        print("\n" + "=" * 50)
        
        # Test de envío
        send_result = adapter.execute({
            "to": "agamenonmacondo@gmail.com",
            "subject": "🧪 Test Gmail Adapter Corregido",
            "body": "Este es un test del gmail adapter con rutas corregidas."
        })
        
        print("\n📧 RESULTADO DE ENVÍO:")
        print(send_result["content"][0]["text"])
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
