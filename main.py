from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import router

# --- Utilidades ---
class NoCacheStaticFiles(StaticFiles):
    """Sirve archivos estáticos sin caché del navegador."""

    def set_headers(self, response, full_path, stat_result) -> None:  # type: ignore[override]
        super().set_headers(response, full_path, stat_result)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"

# Crear directorios necesarios (idempotente)
Path("uploads").mkdir(exist_ok=True)
Path("processed").mkdir(exist_ok=True)

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://negativerestore.com",
        "https://www.negativerestore.com",
        "https://negative-restore.netlify.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas de la aplicación
app.include_router(router)

# Montar la carpeta uploads como estática, sin caché
app.mount("/uploads", NoCacheStaticFiles(directory="uploads"), name="uploads")

# Healthcheck simple
@app.get("/healthz")
async def healthz() -> Dict[str, bool]:
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
