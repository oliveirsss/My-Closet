from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from database import supabase, get_user_from_token
from schemas import UserSignup, UserProfile, UserProfileUpdate
from supabase import create_client
import os
from datetime import datetime

router = APIRouter()


def get_admin_client():
    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not service_key:
        raise HTTPException(status_code=500, detail="Service Key em falta")
    return create_client(url, service_key)


# --- Rota Signup (Mantém igual) ---
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


# --- Rota Update Profile (Atualizada) ---
@router.get("/profile")
def get_profile(authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        admin_supabase = get_admin_client()
        response = admin_supabase.table("profiles").select("*").eq("user_id", user.user.id).limit(1).execute()
        data = response.data[0] if response.data else {}
        metadata = (user.user.user_metadata or {}) if hasattr(user.user, "user_metadata") else {}

        return {
            "profile": UserProfile(
                user_id=user.user.id,
                name=data.get("name") or metadata.get("name", "Utilizador"),
                avatar_url=data.get("avatar_url") or metadata.get("avatar_url"),
                bio=data.get("bio") or metadata.get("bio"),
                location=data.get("location") or metadata.get("location"),
            )
        }
    except Exception as e:
        print(f"Erro ao obter perfil: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile")
def update_profile(data: UserProfileUpdate, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        admin_supabase = get_admin_client()
        profile_payload = {
            "user_id": user.user.id,
            "name": data.name,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
            "location": data.location,
            "updated_at": datetime.utcnow().isoformat()
        }

        admin_supabase.table("profiles").upsert(profile_payload).execute()

        # Mantém os metadados do Supabase em sync (útil para quick display em apps)
        admin_supabase.auth.admin.update_user_by_id(
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

        return {"profile": {**profile_payload}}

    except Exception as e:
        print(f"Erro ao atualizar perfil: {e}")
        raise HTTPException(status_code=500, detail=str(e))