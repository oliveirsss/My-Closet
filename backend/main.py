from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import ai_outfit, auth, items, social, storage  # Import all routers

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
app.include_router(social.router)
app.include_router(ai_outfit.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "backend": "Python FastAPI Modular",
        "ai_outfit": "available",
        "phase": "1",
        "note": "New AI recommendation system in development",
    }
