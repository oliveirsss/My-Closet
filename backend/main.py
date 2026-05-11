from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from routers import ai_outfit, auth, items, outfits, social, storage, usage  # Import all routers

app = FastAPI()

security = HTTPBearer()
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
app.include_router(usage.router)
app.include_router(outfits.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.body()
        body_text = body.decode("utf-8", errors="replace")
    except Exception:
        body_text = "<unavailable>"

    print(f"[validation] {request.method} {request.url.path}: {exc.errors()}")
    print(f"[validation] request body: {body_text[:2000]}")

    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "backend": "Python FastAPI Modular",
        "ai_outfit": "available",
        "phase": "1",
        "note": "New AI recommendation system in development",
    }
