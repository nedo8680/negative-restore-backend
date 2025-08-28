import os
import json
import hashlib
from datetime import datetime
from io import BytesIO
from typing import Set, Dict, Tuple

from fastapi import APIRouter, File, UploadFile, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel, EmailStr, Field
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from app.services.image_processing import process_image
from app.utils.cleanup import delete_old_files

# Router
router = APIRouter()

# Directorios de almacenamiento
UPLOAD_FOLDER: str = "uploads/"
PROCESSED_FOLDER: str = "processed/"

# Validaciones (tipado compatible con py3.8)
VALID_IMAGE_TYPES: Set[str] = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
MAX_FILE_SIZE_MB: int = 4

# Donaciones
MIN_DONATION: float = 2.50
DONATIONS_FILE: str = "donations.json"


class ContactMessage(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    message: str = Field(..., min_length=10, max_length=1000)


# --- Utilidades internas ---
_EXT_BY_MIME: Dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _derive_filenames(original: str, data: bytes, mime: str) -> Tuple[str, str]:
    """
    Genera nombres únicos basados en contenido (hash).
    Devuelve (nombre_subida, nombre_procesado).
    """
    stem, _ = os.path.splitext(os.path.basename(original or "image"))
    ext = _EXT_BY_MIME.get(mime)
    if not ext:
        raise HTTPException(status_code=400, detail="Unsupported MIME type")

    h8 = hashlib.sha256(data).hexdigest()[:8]
    stored_name = f"{stem}__{h8}{ext}"
    processed_name = f"processed_{stem}__{h8}.jpg"
    return stored_name, processed_name


# ------------------- Rutas -------------------
@router.post("/contact")
async def receive_contact_message(data: ContactMessage):
    timestamp = datetime.utcnow().isoformat()

    # 1) Guardar mensaje localmente (opcional)
    try:
        os.makedirs("messages", exist_ok=True)
        filename = f"messages/{int(datetime.utcnow().timestamp())}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": timestamp,
                    "name": data.name,
                    "email": data.email,
                    "message": data.message,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save message.")

    api_key = os.getenv("SENDGRID_API_KEY")

    # 2) Enviar email con SendGrid
    try:
        message = Mail(
            from_email="edwinfuentes8680@gmail.com",
            to_emails="edwinfuentes8680@gmail.com",
            subject="📩 New Contact Form Message",
            html_content=f"""
                <p><strong>Name:</strong> {data.name}</p>
                <p><strong>Email:</strong> {data.email}</p>
                <p><strong>Message:</strong></p>
                <p>{data.message}</p>
                <hr>
                <p>Received at: {timestamp} UTC</p>
            """,
        )
        sg = SendGridAPIClient(api_key)
        sg.send(message)
    except Exception as e:
        print(f"SendGrid error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email.")

    return {"message": "Message received successfully. We will get back to you soon."}


@router.post("/upload/")
async def upload_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,  # <- sin Optional ni default None semántico
):
    """
    Sube imagen a `uploads/` con nombre basado en hash de contenido.
    Evita colisiones cuando el usuario reusa el mismo nombre.
    """
    if file.content_type not in VALID_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image format. Only JPG/PNG/WebP are allowed.")

    contents = await file.read()

    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"The file exceeds the maximum allowed size {MAX_FILE_SIZE_MB} MB.")

    # Validar que sea una imagen real
    try:
        Image.open(BytesIO(contents)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="The file is not a valid image.")

    stored_name, processed_name = _derive_filenames(file.filename, contents, file.content_type)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_path = os.path.join(UPLOAD_FOLDER, stored_name)

    # Solo escribe si no existe (dedupe por contenido)
    if not os.path.exists(file_path):
        with open(file_path, "wb") as buffer:
            buffer.write(contents)

    # BackgroundTasks lo inyecta FastAPI (instancia válida)
    background_tasks.add_task(delete_old_files)

    return {
        "message": "Imagen subida con éxito",
        "filename": stored_name,  # ← usar este para /process/
        "original_filename": file.filename,
        "processed_suggested": processed_name,
    }


@router.post("/process/")
async def process_uploaded_image(
    filename: str,
    background_tasks: BackgroundTasks = None,
):
    """
    Procesa una imagen de `uploads/` y guarda en `processed/` con nombre único.
    Salida: JPG. Usa hash en el nombre para evitar choques por mismo nombre original.
    """
    input_path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(input_path):
        return {"error": "Archivo no encontrado"}

    # Derivar nombre de salida desde el nombre almacenado (que ya incluye hash)
    stem, _ = os.path.splitext(os.path.basename(filename))
    out_name = f"processed_{stem}.jpg"
    output_path = os.path.join(PROCESSED_FOLDER, out_name)

    process_image(input_path, output_path)

    background_tasks.add_task(delete_old_files)

    return {"message": "Imagen procesada con éxito", "filename": out_name}


@router.get("/processed/{filename}")
async def get_processed_image(filename: str):
    """Devuelve una imagen procesada desde `processed/` con headers no-cache."""
    path = os.path.join(PROCESSED_FOLDER, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Imagen procesada no encontrada")
    resp = FileResponse(
        path=path,
        media_type="application/octet-stream",  # fuerza descarga
        filename=filename,
    )
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@router.post("/donation/")
async def register_donation(request: Request):
    data = await request.json()

    amount = float(data.get("amount", 0))
    payer = data.get("payer", {}).get("name", {}).get("given_name", "Anónimo")

    if amount < MIN_DONATION:
        raise HTTPException(status_code=400, detail="El monto mínimo es $2.50")

    donation_entry = {
        "payer": payer,
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        with open(DONATIONS_FILE, "r", encoding="utf-8") as f:
            donations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        donations = []

    donations.append(donation_entry)

    with open(DONATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(donations, f, indent=4, ensure_ascii=False)

    return {"message": "Donación registrada", "amount": amount, "payer": payer}


@router.get("/donations/")
async def get_donations():
    try:
        with open(DONATIONS_FILE, "r", encoding="utf-8") as f:
            donations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        donations = []

    return donations
