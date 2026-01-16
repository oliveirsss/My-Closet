from fastapi import APIRouter, Header, HTTPException
from database import get_user_from_token
from schemas import ClothingItem
from supabase import create_client
import os

router = APIRouter()


# --- Helper para criar o "Super Cliente" (Admin) ---
def get_admin_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not key:
        print("❌ ERRO: SUPABASE_SERVICE_KEY não encontrada no .env")
        raise HTTPException(status_code=500, detail="Erro de configuração no servidor")

    return create_client(url, key)


# --- Endpoint para Itens Públicos (Visitantes) ---
@router.get("/public-items")
def get_public_items(authorization: str = Header(None)):
    admin_supabase = get_admin_client()
    
    # Check if user is logged in to fetch likes
    liked_item_ids = set()
    if authorization:
        user = get_user_from_token(authorization)
        if user:
            try:
                likes_res = admin_supabase.table("likes").select("item_id").eq("user_id", user.user.id).execute()
                liked_item_ids = {row["item_id"] for row in likes_res.data}
            except Exception:
                pass

    try:
        response = admin_supabase.table("clothes").select("*").eq("is_public", True).execute()

        items = []
        for item in response.data:
            owner_id = item["user_id"]
            owner_name = "Utilizador"
            owner_avatar = ""

            try:
                # Buscar dados do dono da peça
                user_res = admin_supabase.auth.admin.get_user_by_id(owner_id)
                if user_res and user_res.user:
                    meta = user_res.user.user_metadata
                    email = user_res.user.email

                    # LÓGICA MELHORADA:
                    # 1. Tenta o nome no perfil
                    # 2. Se não houver, usa o email antes do @
                    # 3. Se tudo falhar, usa "Utilizador"
                    email_name = email.split("@")[0] if email else "Utilizador"
                    owner_name = meta.get("name") or email_name
                    owner_avatar = meta.get("avatar_url", "")
            except Exception as e:
                print(f"Erro a ler user {owner_id}: {e}")

            items.append({
                "id": item["id"],
                "name": item["name"],
                "brand": item.get("brand", ""),
                "size": item.get("size", ""),
                "type": item["type"],
                "layer": item["layer"],
                "materials": item["materials"] or [],
                "weight": item["weight"],
                "tempMin": item["temp_min"],
                "tempMax": item["temp_max"],
                "waterproof": item["waterproof"],
                "windproof": item["windproof"],
                "seasons": item["seasons"] or [],
                "image": item["image"],
                "status": item["status"],
                "favorite": item["favorite"],
                "isPublic": item.get("is_public", False),
                "ownerName": owner_name,
                "ownerAvatar": owner_avatar,
                "ownerId": owner_id,
                "isLikedByMe": item["id"] in liked_item_ids
            })
        return {"items": items}
    except Exception as e:
        print(f"Erro ao buscar itens públicos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 1. GET ITEMS (Privado - Os teus itens)
@router.get("/items")
def get_items(authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()

    response = admin_supabase.table("clothes").select("*").eq("user_id", user.user.id).execute()

    items = []
    for item in response.data:
        items.append({
            "id": item["id"],
            "name": item["name"],
            "brand": item["brand"],
            "size": item["size"],
            "type": item["type"],
            "layer": item["layer"],
            "materials": item["materials"],
            "weight": item["weight"],
            "tempMin": item["temp_min"],
            "tempMax": item["temp_max"],
            "waterproof": item["waterproof"],
            "windproof": item["windproof"],
            "seasons": item["seasons"],
            "image": item["image"],
            "status": item["status"],
            "favorite": item["favorite"],
            "isPublic": item.get("is_public", False),
            "ownerId": item["user_id"]
        })

    return {"items": items}


# 2. CREATE ITEM
@router.post("/items")
def create_item(item: ClothingItem, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()

    data_to_insert = {
        "user_id": user.user.id,
        "name": item.name,
        "brand": item.brand,
        "size": item.size,
        "type": item.type,
        "layer": item.layer,
        "materials": item.materials,
        "weight": item.weight,
        "temp_min": item.tempMin,
        "temp_max": item.tempMax,
        "waterproof": item.waterproof,
        "windproof": item.windproof,
        "seasons": item.seasons,
        "image": item.image,
        "status": item.status,
        "favorite": item.favorite,
        "is_public": item.is_public
    }

    try:
        response = admin_supabase.table("clothes").insert(data_to_insert).execute()
        new_item_db = response.data[0]
        item.id = new_item_db["id"]
        return {"item": item}
    except Exception as e:
        print(f"Erro ao criar item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 3. UPDATE ITEM
@router.put("/items/{item_id}")
def update_item(item_id: str, item: ClothingItem, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()

    data_to_update = {
        "name": item.name,
        "brand": item.brand,
        "size": item.size,
        "type": item.type,
        "layer": item.layer,
        "materials": item.materials,
        "weight": item.weight,
        "temp_min": item.tempMin,
        "temp_max": item.tempMax,
        "waterproof": item.waterproof,
        "windproof": item.windproof,
        "seasons": item.seasons,
        "image": item.image,
        "status": item.status,
        "favorite": item.favorite,
        "is_public": item.is_public
    }

    try:
        admin_supabase.table("clothes").update(data_to_update).eq("id", item_id).execute()
        return {"item": item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 4. DELETE ITEM
@router.delete("/items/{item_id}")
def delete_item(item_id: str, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()

    try:
        admin_supabase.table("clothes").delete().eq("id", item_id).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))