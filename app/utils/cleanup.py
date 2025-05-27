import os
import time
import logging
from logging.handlers import RotatingFileHandler

MAX_FILE_AGE_SECONDS = 7200  # 2 horas
FOLDERS_TO_CLEAN = ["uploads", "processed"]

# Configuración del logger con rotación
log_dir = "logs"
log_path = os.path.join(log_dir, "cleanup.log")
os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger("cleanup_logger")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    log_path,
    maxBytes=1024 * 1024,  # 1 MB por archivo
    backupCount=5          # guarda hasta 5 archivos antiguos
)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)

# Evita agregar múltiples handlers si el archivo se importa varias veces
if not logger.hasHandlers():
    logger.addHandler(handler)

def delete_old_files():
    now = time.time()
    for folder in FOLDERS_TO_CLEAN:
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                file_age = now - os.path.getmtime(path)
                if file_age > MAX_FILE_AGE_SECONDS:
                    try:
                        os.remove(path)
                        logger.info(f"🗑️ Deleted old file: {path}")
                    except Exception as e:
                        logger.error(f"❌ Error deleting {path}: {e}")
