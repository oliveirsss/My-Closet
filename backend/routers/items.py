from fastapi import APIRouter, Header, HTTPException
from database import get_user_from_token
from schemas.clothing import ClothingItem
from supabase import create_client
from pydantic import ValidationError
import os

router = APIRouter()


COLOR_ALIASES = {
    "amarelo": "yellow",
    "amarelos": "yellow",
    "amarela": "yellow",
    "amarelas": "yellow",
    "azul": "blue",
    "azuis": "blue",
    "vermelho": "red",
    "vermelhos": "red",
    "vermelha": "red",
    "vermelhas": "red",
    "verde": "green",
    "verdes": "green",
    "preto": "black",
    "pretos": "black",
    "preta": "black",
    "pretas": "black",
    "branco": "white",
    "brancos": "white",
    "branca": "white",
    "brancas": "white",
    "cinza": "gray",
    "cinzas": "gray",
    "rosa": "pink",
    "rosas": "pink",
    "roxo": "purple",
    "roxos": "purple",
    "roxa": "purple",
    "roxas": "purple",
    "laranja": "orange",
    "laranjas": "orange",
    "marrom": "brown",
    "marrons": "brown",
    "bege": "beige",
    "beges": "beige",
    "creme": "cream",
    "cremes": "cream",
    "ouro": "gold",
    "ouros": "gold",
    "prata": "silver",
    "pratas": "silver",
    "grey": "gray",
}


def normalize_optional_text(value):
    if value is None:
        return None

    normalized = str(value).strip().lower()
    return normalized or None


def normalize_optional_color(value):
    normalized = normalize_optional_text(value)
    if not normalized:
        return None

    return COLOR_ALIASES.get(normalized, normalized)


def metadata_fields_from_db(item):
    return {
        "color": normalize_optional_color(item.get("color")),
        "style": normalize_optional_text(item.get("style")),
        "occasion": normalize_optional_text(item.get("occasion")),
    }


def metadata_fields_for_db(item: ClothingItem):
    return {
        "color": normalize_optional_color(item.color),
        "style": normalize_optional_text(item.style),
        "occasion": normalize_optional_text(item.occasion),
    }


def remove_metadata_columns(data):
    return {
        key: value
        for key, value in data.items()
        if key not in {"color", "style", "occasion"}
    }


def is_missing_metadata_column_error(error):
    text = str(error).lower()
    return (
        "pgrst204" in text
        or "schema cache" in text
    ) and any(column in text for column in ("'color'", "'style'", "'occasion'"))


def log_supabase_payload(action, payload):
    safe_payload = sanitize_payload_for_log(payload)
    print(f"[items.py] Supabase {action} payload: {safe_payload}")


def sanitize_payload_for_log(payload):
    safe_payload = dict(payload)
    image = safe_payload.get("image")
    if image and len(str(image)) > 120:
        safe_payload["image"] = f"{str(image)[:80]}...({len(str(image))} chars)"

    return safe_payload


def value_or_default(data, key, fallback, fallback_key=None, default=None):
    value = data.get(key)
    if value is not None:
        return value

    fallback_value = fallback.get(fallback_key or key)
    if fallback_value is not None:
        return fallback_value

    return default


def frontend_item_from_db(db_item, fallback_item: ClothingItem = None):
    fallback = fallback_item.model_dump(by_alias=True) if fallback_item else {}
    metadata_source = {
        "color": value_or_default(db_item, "color", fallback),
        "style": value_or_default(db_item, "style", fallback),
        "occasion": value_or_default(db_item, "occasion", fallback),
    }

    return {
        "id": value_or_default(db_item, "id", fallback),
        "name": value_or_default(db_item, "name", fallback, default=""),
        "brand": value_or_default(db_item, "brand", fallback, default=""),
        "size": value_or_default(db_item, "size", fallback, default=""),
        "type": value_or_default(db_item, "type", fallback, default=""),
        **metadata_fields_from_db(metadata_source),
        "layer": value_or_default(db_item, "layer", fallback, default=1),
        "materials": value_or_default(db_item, "materials", fallback, default=[]) or [],
        "weight": value_or_default(db_item, "weight", fallback, default=0),
        "tempMin": value_or_default(db_item, "temp_min", fallback, "tempMin", -10),
        "tempMax": value_or_default(db_item, "temp_max", fallback, "tempMax", 30),
        "waterproof": value_or_default(db_item, "waterproof", fallback, default=False),
        "windproof": value_or_default(db_item, "windproof", fallback, default=False),
        "seasons": value_or_default(db_item, "seasons", fallback, default=[]) or [],
        "image": value_or_default(db_item, "image", fallback, default=""),
        "status": value_or_default(db_item, "status", fallback, default="clean"),
        "favorite": value_or_default(db_item, "favorite", fallback, default=False),
        "isPublic": value_or_default(db_item, "is_public", fallback, "isPublic", False),
        "ownerId": value_or_default(db_item, "user_id", fallback, "ownerId"),
    }


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
            owner_id = item.get("user_id")
            owner_name = "Utilizador"
            owner_avatar = ""

            try:
                # Buscar dados do dono da peça
                user_res = admin_supabase.auth.admin.get_user_by_id(owner_id)
                if user_res and user_res.user:
                    meta = user_res.user.user_metadata or {}
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

            frontend_item = frontend_item_from_db(item)
            frontend_item.update({
                "isPublic": item.get("is_public", False),
                "ownerName": owner_name,
                "ownerAvatar": owner_avatar,
                "ownerId": owner_id,
                "isLikedByMe": item.get("id") in liked_item_ids
            })
            items.append(frontend_item)
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
        frontend_item = frontend_item_from_db(item)
        print(f"[items.py] Item loaded from Supabase: {sanitize_payload_for_log(frontend_item)}")
        items.append(frontend_item)

    return {"items": items}


@router.get("/items/debug/wardrobe")
def debug_user_wardrobe(authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()
    response = (
        admin_supabase.table("clothes")
        .select("*")
        .eq("user_id", user.user.id)
        .execute()
    )

    debug_items = []
    for item in response.data:
        debug_item = {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": item.get("type"),
            "color": normalize_optional_color(item.get("color")),
            "raw_color": item.get("color"),
            "style": normalize_optional_text(item.get("style")),
            "occasion": normalize_optional_text(item.get("occasion")),
            "status": item.get("status"),
            "layer": item.get("layer"),
            "user_id": item.get("user_id"),
            "temp_min": item.get("temp_min"),
            "temp_max": item.get("temp_max"),
        }
        print(f"[items.py] Debug wardrobe item: {debug_item}")
        debug_items.append(debug_item)

    return {"items": debug_items}


# 2. CREATE ITEM
@router.post("/items")
def create_item(item: ClothingItem, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()
    print(f"[items.py] Received create payload: {sanitize_payload_for_log(item.model_dump(by_alias=True))}")

    data_to_insert = {
        "user_id": user.user.id,
        "name": item.name,
        "brand": item.brand,
        "size": item.size,
        "type": item.type,
        **metadata_fields_for_db(item),
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
        log_supabase_payload("insert", data_to_insert)
        try:
            response = admin_supabase.table("clothes").insert(data_to_insert).execute()
        except Exception as schema_error:
            if not is_missing_metadata_column_error(schema_error):
                print(f"[items.py] Supabase insert error: {schema_error}")
                raise

            print(f"[items.py] Supabase insert schema error: {schema_error}")
            raise HTTPException(
                status_code=500,
                detail=(
                    "Supabase clothes table is missing color/style/occasion columns. "
                    "Run backend/supabase_add_clothing_metadata.sql and reload schema."
                ),
            )

        if not response.data:
            print("[items.py] Supabase insert returned no rows")
            raise HTTPException(status_code=500, detail="Item created but no row was returned")
        new_item_db = response.data[0]
        print(f"[items.py] Supabase inserted row: {sanitize_payload_for_log(new_item_db)}")
        loaded_item = frontend_item_from_db(new_item_db, item)
        print(f"[items.py] Item loaded from Supabase: {sanitize_payload_for_log(loaded_item)}")
        return {"item": loaded_item}
    except ValidationError as e:
        print(f"[items.py] Create item validation error: {e}")
        raise HTTPException(status_code=422, detail=e.errors())
    except HTTPException:
        raise
    except Exception as e:
        print(f"[items.py] Erro ao criar item: {e}")
        print(f"[items.py] Failed create payload: {sanitize_payload_for_log(data_to_insert)}")
        raise HTTPException(status_code=500, detail=str(e))


# 3. UPDATE ITEM
@router.put("/items/{item_id}")
def update_item(item_id: str, item: ClothingItem, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()
    print(f"[items.py] Received update payload for {item_id}: {sanitize_payload_for_log(item.model_dump(by_alias=True))}")

    data_to_update = {
        "name": item.name,
        "brand": item.brand,
        "size": item.size,
        "type": item.type,
        **metadata_fields_for_db(item),
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
        log_supabase_payload("update", data_to_update)
        try:
            response = (
                admin_supabase.table("clothes")
                .update(data_to_update)
                .eq("id", item_id)
                .execute()
            )
        except Exception as schema_error:
            if not is_missing_metadata_column_error(schema_error):
                print(f"[items.py] Supabase update error: {schema_error}")
                raise

            print(f"[items.py] Supabase update schema error: {schema_error}")
            raise HTTPException(
                status_code=500,
                detail=(
                    "Supabase clothes table is missing color/style/occasion columns. "
                    "Run backend/supabase_add_clothing_metadata.sql and reload schema."
                ),
            )

        updated_item_db = response.data[0] if response.data else {
            **data_to_update,
            "id": item_id,
            "user_id": user.user.id,
        }
        print(f"[items.py] Supabase updated row: {sanitize_payload_for_log(updated_item_db)}")
        loaded_item = frontend_item_from_db(updated_item_db, item)
        print(f"[items.py] Item loaded from Supabase: {sanitize_payload_for_log(loaded_item)}")
        return {"item": loaded_item}
    except ValidationError as e:
        print(f"[items.py] Update item validation error: {e}")
        raise HTTPException(status_code=422, detail=e.errors())
    except HTTPException:
        raise
    except Exception as e:
        print(f"[items.py] Erro ao atualizar item {item_id}: {e}")
        print(f"[items.py] Failed update payload: {sanitize_payload_for_log(data_to_update)}")
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
