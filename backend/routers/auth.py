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
# --- Rota de Obter Perfil ---
@router.get("/profile")
def get_profile(authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Configurar Admin para ler da BD (bypassing RLS)
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        url = os.environ.get("SUPABASE_URL")
        
        if not service_key:
             raise HTTPException(status_code=500, detail="Erro de configuração")

        admin_supabase = create_client(url, service_key)

        # Tenta ler da tabela 'profiles' (onde guardamos custom fields e URL da foto)
        # O user.user.id é o UUID do Supabase Auth
        res = admin_supabase.table("profiles").select("*").eq("user_id", user.user.id).execute()
        
        # Se existir perfil na tabela, devolve.
        if res.data and len(res.data) > 0:
            profile_data = res.data[0]
            # Mapear para o formato esperado pelo frontend se necessário, mas o schema UserProfile geralmente bate certo com as colunas
            return {"profile": profile_data}

        # Fallback: Se não houver registo na tabela 'profiles', tenta devolver meta-data do Auth
        # Isso acontece se o user criou conta mas nunca editou perfil
        meta = user.user.user_metadata or {}
        return {
            "profile": {
                "name": meta.get("name", "Utilizador"),
                "avatar_url": meta.get("avatar_url", ""),
                "bio": meta.get("bio", ""),
                "location": meta.get("location", "")
            }
        }
    except Exception as e:
        print(f"Erro ao obter perfil: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Rota de Atualizar Perfil ---
@router.put("/profile")
def update_profile(data: UserProfileUpdate, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Configurar Admin para escrever na BD (bypassing RLS se necessario)
        service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        url = os.environ.get("SUPABASE_URL")

        if not service_key:
             raise HTTPException(status_code=500, detail="Erro de configuração: SERVICE_KEY em falta")

        admin_supabase = create_client(url, service_key)

        # 1. Update na Tabela 'profiles' (Persistência Principal)
        profile_payload = {
            "user_id": user.user.id,
            "name": data.name,
            "avatar_url": data.avatar_url,
            "bio": data.bio,
            "location": data.location,
            "updated_at": "now()"
        }
        
        # Upsert: Cria se não existir, atualiza se existir (Usando Admin Client)
        res = admin_supabase.table("profiles").upsert(profile_payload).execute()

        # 2. (Opcional) Update no Auth Metadata para manter sincronizado 
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

        return {"success": True, "profile": profile_payload}

    except Exception as e:
        print(f"Erro ao atualizar perfil: {e}")
        raise HTTPException(status_code=500, detail=str(e))