from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, items, storage  # Importar os novos routers

app = FastAPI()

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Registar os Routers ---
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(storage.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "backend": "Python FastAPI Modular"}