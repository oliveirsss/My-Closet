from fastapi import APIRouter, Header, HTTPException
from database import get_user_from_token
from schemas import ClothingItem
from supabase import create_client
import os

router = APIRouter()


# --- Helper Admin ---
def get_admin_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        print("❌ ERRO: SUPABASE_SERVICE_KEY não encontrada no .env")
        raise HTTPException(status_code=500, detail="Erro de configuração no servidor")
    return create_client(url, key)


# --- GET PUBLIC ITEMS ---
@router.get("/public-items")
def get_public_items():
    admin_supabase = get_admin_client()
    try:
        response = admin_supabase.table("clothes").select("*").eq("is_public", True).execute()
        items = []
        for item in response.data:
            # (Lógica de ir buscar o dono - podes manter a tua versão anterior se já tinhas)
            # Vou simplificar aqui para focar no update, mas mantém o teu código de owner se já o tinhas
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
                "ownerId": item["user_id"]
            })
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 1. GET ITEMS
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
            "isPublic": item.get("is_public", False)
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
        print(f"Erro ao criar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 3. UPDATE ITEM (CORRIGIDO: Agora atualiza TUDO, incluindo a imagem)
@router.put("/items/{item_id}")
def update_item(item_id: str, item: ClothingItem, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()

    # AQUI ESTAVA O ERRO: Faltavam campos!
    data_to_update = {
        "name": item.name,
        "brand": item.brand,  # Novo
        "size": item.size,  # Novo
        "type": item.type,  # Novo
        "layer": item.layer,  # Novo
        "materials": item.materials,  # Novo
        "weight": item.weight,  # Novo
        "temp_min": item.tempMin,  # Novo
        "temp_max": item.tempMax,  # Novo
        "waterproof": item.waterproof,  # Novo
        "windproof": item.windproof,  # Novo
        "seasons": item.seasons,  # Novo
        "image": item.image,  # <--- O MAIS IMPORTANTE (A FOTO)
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