# 📷 NGRestore App

Aplicación web para convertir negativos en imágenes corregidas automáticamente.

## 🚀 Estructura del Proyecto
```bash
NegRestore/
├── app/                # Backend FastAPI (rutas y lógica de procesamiento)
├── frontend/           # Frontend con Vite + React + Tailwind + i18n
├── uploads/            # Imágenes subidas por el usuario
├── processed/          # Imágenes ya procesadas
├── main.py             # Entrada del backend
├── requirements.txt    # Dependencias Python
```
---

## 🔧 Instalación y ejecución

### 1. Backend (FastAPI + Python)

```bash
# Activar entorno virtual
source env/bin/activate   # Linux/macOS
# o
env\Scripts\activate.bat  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor FastAPI
uvicorn main:app --reload

```
El backend estará disponible en http://127.0.0.1:8000
### 2. Frontend (Vite + React)
```bash
cd frontend
npm install
npm run dev
```
La interfaz estará disponible en http://localhost:5173

--- 
# 🌐 Tecnologías utilizadas
* FastAPI para el backend

* OpenCV y Pillow para procesamiento de imagen

* React + TypeScript para el frontend

* Vite como bundler moderno

* TailwindCSS para estilos rápidos y adaptativos

* i18next para manejo de idiomas (🇪🇸 / 🇬🇧)
---

# 💡 Próximas mejoras

* Subida múltiple de imágenes

* Vista previa del antes y después

* Selector de idioma

* Botón de donación (PayPal)

* Mejoras visuales con animaciones

