
import sys
import os
from pathlib import Path

# === CORRECCIÓN DE RUTAS PARA IMPORTS DINÁMICOS ===
current_dir = Path(__file__).resolve().parent
tools_dir = current_dir.parent
ava_bot_dir = tools_dir.parent
project_root = ava_bot_dir.parent

# Agregar todas las rutas necesarias al sys.path
paths_to_add = [
    str(current_dir),
    str(tools_dir),
    str(ava_bot_dir),
    str(project_root),
    str(ava_bot_dir / 'utils'),
    str(ava_bot_dir / 'nodes'),
    str(ava_bot_dir / 'nodes' / 'email')
]
for path in paths_to_add:
    if path not in sys.path and os.path.exists(path):
        sys.path.insert(0, path)

# === IMPORTS CON LOGS DE FALLA ===
import logging
logger = logging.getLogger(__name__)

# Importar oauth_helper si está disponible
try:
    from oauth_helper import get_google_credentials
    OAUTH_HELPER_AVAILABLE = True
except ImportError:
    OAUTH_HELPER_AVAILABLE = False

# Importar GmailSender
try:
    from gmail_sender import GmailSender
except ImportError:
    try:
        from nodes.email.gmail_sender import GmailSender
    except ImportError as e:
        logger.error(f"❌ No se pudo importar GmailSender: {e}")
