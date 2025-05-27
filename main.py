from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.routes import router

app = FastAPI()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://negative-restore-backend.onrender.com","https://negative-restore.netlify.app","http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)