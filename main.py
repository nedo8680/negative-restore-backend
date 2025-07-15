from dotenv import load_dotenv
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles 
from app.routes import router


app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
                   "https://negativerestore.com",
                   "https://www.negativerestore.com",
                   "https://negative-restore.netlify.app",
                   "http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Montar la carpeta uploads como estática, lo que permite acceder a las imágenes subidas 
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)