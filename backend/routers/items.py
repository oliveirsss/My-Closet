from fastapi import APIRouter, Header, HTTPException
from database import get_user_from_token
from schemas import ClothingItem
from supabase import create_client
import os

router = APIRouter()


# --- Helper para criar o "Super Cliente" (Admin) ---
def get_admin_client():
    url = os.environ.get("SUPABASE_URL")
    # Usa a mesma chave poderosa que usaste para as imagens
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not key:
        print("❌ ERRO: SUPABASE_SERVICE_KEY não encontrada no .env")
        raise HTTPException(status_code=500, detail="Erro de configuração no servidor")

    return create_client(url, key)


# 1. GET ITEMS
@router.get("/items")
def get_items(authorization: str = Header(None)):
    # Validar quem é o utilizador
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()

    # IMPORTANTE: Como somos Admin, temos de filtrar manualmente pelo ID do user
    response = admin_supabase.table("clothes").select("*").eq("user_id", user.user.id).execute()

    # Converter snake_case (DB) para camelCase (Frontend)
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
            "favorite": item["favorite"]
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
        "favorite": item.favorite
    }

    try:
        # Inserir como Admin (Ignora RLS)
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
        "status": item.status,
        "favorite": item.favorite,
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