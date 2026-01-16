from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException, Body
import os
from database import get_user_from_token
from supabase import create_client

router = APIRouter()

# --- HELPER: Admin Client ---
def get_admin_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        print("❌ ERRO: SUPABASE_SERVICE_KEY não encontrada no .env")
        raise HTTPException(status_code=500, detail="Erro de configuração no servidor")
    return create_client(url, key)

# --- SCHEMAS ---
class CommentCreate(BaseModel):
    text: str

class CommentResponse(BaseModel):
    id: str
    user_id: str
    item_id: str
    text: str
    user_name: Optional[str] = "Utilizador"
    user_avatar: Optional[str] = ""
    created_at: str

# --- ENDPOINTS: LIKES ---

@router.post("/social/like/{item_id}")
def like_item(item_id: str, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()
    try:
        # Check if already liked to avoid error (though unique constraint handles it)
        # Using insert directly - Supabase will error if unique constraint violated
        res = admin_supabase.table("likes").insert({
            "user_id": user.user.id,
            "item_id": item_id
        }).execute()
        return {"success": True}
    except Exception as e:
        # Ignore duplicate errors (already liked)
        return {"success": False, "detail": str(e)}

@router.delete("/social/like/{item_id}")
def unlike_item(item_id: str, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()
    try:
        res = admin_supabase.table("likes").delete().match({
            "user_id": user.user.id, 
            "item_id": item_id
        }).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/social/likes/{item_id}")
def get_item_likes(item_id: str, authorization: str = Header(None)):
    admin_supabase = get_admin_client()
    user_id = None
    
    # Try get user if token provided, but don't fail if not
    if authorization:
        user = get_user_from_token(authorization)
        if user:
            user_id = user.user.id

    try:
        # Get count
        # Select count in Supabase-py is a bit tricky, usually just select id and count
        res_count = admin_supabase.table("likes").select("id", count="exact").eq("item_id", item_id).execute()
        count = res_count.count if res_count.count is not None else len(res_count.data)

        # Check if user liked
        is_liked = False
        if user_id:
            res_user = admin_supabase.table("likes").select("id").match({
                "item_id": item_id,
                "user_id": user_id
            }).execute()
            if res_user.data and len(res_user.data) > 0:
                is_liked = True

        return {"count": count, "isLiked": is_liked}
    except Exception as e:
        print(f"Error getting likes: {e}")
        return {"count": 0, "isLiked": False}




@router.get("/social/likes")
def get_liked_items(authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    admin_supabase = get_admin_client()
    try:
        # Get item IDs
        res = admin_supabase.table("likes").select("item_id").eq("user_id", user.user.id).execute()
        item_ids = [row["item_id"] for row in res.data]
        
        print(f"[DEBUG] User {user.user.id} has likes on items: {item_ids}") # DEBUG

        if not item_ids:
            return {"items": []}

        # Get actual items
        items_res = admin_supabase.table("clothes").select("*").in_("id", item_ids).execute()
        print(f"[DEBUG] Found {len(items_res.data)} items in clothes table matching likes.") # DEBUG
        
        items = []
        for item in items_res.data:
            owner_id = item["user_id"]
            owner_name = "Utilizador"
            owner_avatar = ""
            
            try:
                user_res = admin_supabase.auth.admin.get_user_by_id(owner_id)
                if user_res and user_res.user:
                    meta = user_res.user.user_metadata
                    email = user_res.user.email
                    email_name = email.split("@")[0] if email else "Utilizador"
                    owner_name = meta.get("name") or email_name
                    owner_avatar = meta.get("avatar_url", "")
            except Exception:
                pass

            items.append({
                "id": item["id"],
                "name": item["name"],
                "image": item["image"],
                "brand": item.get("brand", ""),
                "size": item.get("size", ""),
                "materials": item.get("materials", []),
                "seasons": item.get("seasons", []),
                "type": item.get("type", ""),
                "layer": item.get("layer", 1),
                "status": item["status"],
                "favorite": item["favorite"],
                "ownerId": owner_id,
                "ownerName": owner_name,
                "ownerAvatar": owner_avatar,
                "isLikedByMe": True
            })
            
        return {"items": items}
    except Exception as e:
        print(f"Error getting liked items: {e}")
        return {"items": []}


# --- ENDPOINTS: COMMENTS ---

@router.get("/social/comments/{item_id}")
def get_comments(item_id: str):
    admin_supabase = get_admin_client()
    try:
        res = admin_supabase.table("comments") \
            .select("*") \
            .eq("item_id", item_id) \
            .order("created_at", desc=True) \
            .execute()
        return {"comments": res.data}
    except Exception as e:
        print(f"Error getting comments: {e}")
        return {"comments": []}

@router.post("/social/comment/{item_id}")
def add_comment(item_id: str, comment: CommentCreate, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_supabase = get_admin_client()
    
    # Get user details for cache
    user_name = user.user.user_metadata.get("name", "Utilizador")
    user_avatar = user.user.user_metadata.get("avatar_url", "")

    try:
        res = admin_supabase.table("comments").insert({
            "user_id": user.user.id,
            "item_id": item_id,
            "text": comment.text,
            "user_name": user_name,
            "user_avatar": user_avatar
        }).execute()
        return {"comment": res.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINTS: WISHLIST ---

@router.post("/social/wishlist/{item_id}")
def add_to_wishlist(item_id: str, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    admin_supabase = get_admin_client()
    try:
        admin_supabase.table("wishlist").insert({
            "user_id": user.user.id, 
            "item_id": item_id
        }).execute()
        return {"success": True}
    except Exception:
        return {"success": False} # Likely already in wishlist

@router.delete("/social/wishlist/{item_id}")
def remove_from_wishlist(item_id: str, authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    admin_supabase = get_admin_client()
    try:
        admin_supabase.table("wishlist").delete().match({
            "user_id": user.user.id, 
            "item_id": item_id
        }).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/social/wishlist")
def get_wishlist(authorization: str = Header(None)):
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    admin_supabase = get_admin_client()
    try:
        # Get item IDs
        res = admin_supabase.table("wishlist").select("item_id").eq("user_id", user.user.id).execute()
        item_ids = [row["item_id"] for row in res.data]
        
        if not item_ids:
            return {"items": []}

        # Get actual items
        items_res = admin_supabase.table("clothes").select("*").in_("id", item_ids).execute()
        
        # Format items (reuse logic from items.py if possible, but keep simple here)
        items = []
        for item in items_res.data:
             items.append({
                "id": item["id"],
                "name": item["name"],
                "image": item["image"],
                "brand": item.get("brand", ""),
                "size": item.get("size", ""),
                # Minimal fields for list
            })
            
        return {"items": items}
    except Exception as e:
        print(f"Error getting wishlist: {e}")
        return {"items": []}
