from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from database import supabase, get_user_from_token
# Agora importamos tudo do schemas.py
from schemas import UserSignup, UserProfileUpdate
from supabase import create_client
import os

router = APIRouter()


# --- Rota de Criar Conta (Signup) ---
@router.post("/signup")
def signup(user: UserSignup):
    try:
        res = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password,
            "options": {
                "data": {"name": user.name}
            }
        })
        return {"user": res.user}
    except Exception as e:
        print(f"❌ Erro no Signup: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )


# --- Rota de Atualizar Perfil ---
@router.put("/profile")
def update_profile(data: UserProfileUpdate, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    url = os.environ.get("SUPABASE_URL")

    if not service_key:
        raise HTTPException(status_code=500, detail="Service Key em falta")

    try:
        admin_supabase = create_client(url, service_key)

        response = admin_supabase.auth.admin.update_user_by_id(
            uid=user.user.id,
            attributes={
                "user_metadata": {
                    "name": data.name,
                    "avatar_url": data.avatar_url,
                    "bio": data.bio,
                    "location": data.location
                }
            }
        )

        return {"success": True, "user": response.user}

    except Exception as e:
        print(f"Erro ao atualizar perfil: {e}")
        raise HTTPException(status_code=500, detail=str(e))