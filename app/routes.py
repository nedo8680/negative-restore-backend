import os
import json
from fastapi import APIRouter, File, UploadFile, HTTPException, Request, BackgroundTasks
from PIL import Image
from io import BytesIO
from app.services.image_processing import process_image  # Importamos la función de procesamiento
from fastapi.responses import FileResponse
from datetime import datetime
from app.utils.cleanup import delete_old_files  # Limpieza
from pydantic import BaseModel, EmailStr, Field
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


# Creamos un router para manejar las rutas
router = APIRouter()

# Directorios donde se guardarán las imágenes
UPLOAD_FOLDER = "uploads/"
PROCESSED_FOLDER = "processed/"

# Tipos de imagen permitidos
VALID_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
MAX_FILE_SIZE_MB = 4  # tamaño máximo en megabytes

# Donación mínima para el uso de la API
# Esta variable se puede usar para validar donaciones en el futuro
# o para mostrar mensajes en la interfaz de usuario
MIN_DONATION = 2.50
DONATIONS_FILE = "donations.json"

class ContactMessage(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    message: str = Field(..., min_length=10, max_length=1000)

# Ruta para el contacto
@router.post("/contact")
async def receive_contact_message(data: ContactMessage):
    timestamp = datetime.utcnow().isoformat()

    # 1. Guardar mensaje localmente (opcional)
    try:
        os.makedirs("messages", exist_ok=True)
        filename = f"messages/{int(datetime.utcnow().timestamp())}.json"
        with open(filename, "w") as f:
            json.dump({
                "timestamp": timestamp,
                "name": data.name,
                "email": data.email,
                "message": data.message,
            }, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to save message.")
    
    api_key = os.getenv("SENDGRID_API_KEY")

    # 2. Enviar email con SendGrid (asegúrate de configurar la API key en Render)
    try:
        message = Mail(
            from_email="edwinfuentes8680@gmail.com",  # Cambia esto
            to_emails="edwinfuentes8680@gmail.com",          # Cambia esto también
            subject="📩 New Contact Form Message",
            html_content=f"""
                <p><strong>Name:</strong> {data.name}</p>
                <p><strong>Email:</strong> {data.email}</p>
                <p><strong>Message:</strong></p>
                <p>{data.message}</p>
                <hr>
                <p>Received at: {timestamp} UTC</p>
            """
        )
        sg = SendGridAPIClient(api_key)
        sg.send(message)
    except Exception as e:
        print(f"SendGrid error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email.")

    return {"message": "Message received successfully. We will get back to you soon."}

# Ruta para subir imágenes
@router.post("/upload/")
async def upload_image(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Guarda una imagen subida en la carpeta 'uploads/', validando su formato."""
    
    # Verificar tipo de archivo
    if file.content_type not in VALID_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image format. Only JPG and PNG are allowed.")

    contents = await file.read()

    # Validar tamaño
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"The file exceeds the maximum allowed size {MAX_FILE_SIZE_MB} MB.")

    # Validar que sea una imagen real
    try:
        Image.open(BytesIO(contents)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="The file is not a valid image.")

    # Guardar la imagen
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    if background_tasks:
        background_tasks.add_task(delete_old_files)  # 👈 Limpieza tras subida

    return {"message": "Imagen subida con éxito", "filename": file.filename}

# Ruta para procesar la imagen
@router.post("/process/")
async def process_uploaded_image(filename: str , background_tasks: BackgroundTasks = None):
    """Aplica el procesamiento de imagen y guarda el resultado en 'processed/'."""
    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.join(PROCESSED_FOLDER, f"processed_{filename}")

    # Verificar que la imagen existe antes de procesarla
    if not os.path.exists(input_path):
        return {"error": "Archivo no encontrado"}

    # Llamamos al procesador de imágenes
    process_image(input_path, output_path)

    if background_tasks:
        background_tasks.add_task(delete_old_files)  # 👈 Limpieza tras procesamiento

    return {
        "message": "Imagen procesada con éxito",
        "filename": f"processed_{filename}"
    }

@router.get("/processed/{filename}")
async def get_processed_image(filename: str):
    """Devuelve una imagen procesada desde el directorio 'processed/'."""
    path = os.path.join(PROCESSED_FOLDER, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Imagen procesada no encontrada")
    return FileResponse( 
        path=path,
        media_type="application/octet-stream",  # fuerza la descarga
        filename=filename  # nombre del archivo sugerido
    )

@router.post("/donation/")
async def register_donation(request: Request):
    data = await request.json()

    amount = float(data.get("amount", 0))
    payer = data.get("payer", {}).get("name", {}).get("given_name", "Anónimo")

    if amount < MIN_DONATION:
        raise HTTPException(status_code=400, detail="El monto mínimo es $2.50")

    # Registro de la donación
    donation_entry = {
        "payer": payer,
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Leer archivo existente o inicializar lista vacía
    try:
        with open(DONATIONS_FILE, "r") as f:
            donations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        donations = []

    # Agregar nueva donación
    donations.append(donation_entry)

    # Guardar nuevamente
    with open(DONATIONS_FILE, "w") as f:
        json.dump(donations, f, indent=4)

    return {"message": "Donación registrada", "amount": amount, "payer": payer}

@router.get("/donations/")
async def get_donations():
    """Devuelve la lista de donaciones registradas."""
    try:
        with open(DONATIONS_FILE, "r") as f:
            donations = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        donations = []

    return donations