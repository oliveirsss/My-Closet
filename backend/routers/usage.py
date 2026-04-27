"""
Usage History Routes

Endpoints for tracking what the user wore and when.
- POST /usage/record  - Record that items were worn today
- GET  /usage/history - Get the wear history (last N days)
"""

from datetime import datetime, timedelta
from typing import List, Optional

from database import get_user_from_token, supabase
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/usage", tags=["usage"])


class RecordUsageRequest(BaseModel):
    item_ids: List[str]
    occasion: Optional[str] = None
    worn_date: Optional[str] = None   # ISO date string, defaults to today


@router.post("/record")
async def record_outfit_usage(
    request: RecordUsageRequest,
    authorization: str = Header(None),
):
    """
    Record that the user wore a set of items today.
    Inserts one row per item into usage_history.
    """
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user.user.id
    worn_date = request.worn_date or datetime.now().isoformat()

    inserted = 0
    for item_id in request.item_ids:
        try:
            supabase.table("usage_history").insert({
                "user_id": user_id,
                "clothing_id": item_id,
                "worn_date": worn_date,
                "weather_condition": request.occasion,
            }).execute()
            inserted += 1
        except Exception as e:
            print(f"Could not record usage for item {item_id}: {e}")

    return {"success": True, "recorded": inserted, "total": len(request.item_ids)}


@router.get("/history")
async def get_wear_history(
    days: int = 30,
    authorization: str = Header(None),
):
    """
    Return a day-by-day list of outfits worn in the last `days` days.
    Groups usage_history rows by worn_date (date part only).
    """
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    user_id = user.user.id
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    try:
        usage_resp = (
            supabase.table("usage_history")
            .select("clothing_id, worn_date")
            .eq("user_id", user_id)
            .gte("worn_date", cutoff)
            .order("worn_date", desc=True)
            .execute()
        )
        rows = usage_resp.data or []

        # Group by date (YYYY-MM-DD)
        by_date: dict = {}
        for row in rows:
            day = row["worn_date"][:10]
            by_date.setdefault(day, []).append(row["clothing_id"])

        # Fetch item details for each unique item
        all_item_ids = list({item_id for ids in by_date.values() for item_id in ids})
        items_map = {}
        if all_item_ids:
            items_resp = (
                supabase.table("clothes")
                .select("id, name, type, image, layer")
                .in_("id", all_item_ids)
                .execute()
            )
            for item in (items_resp.data or []):
                items_map[item["id"]] = item

        history = []
        for day, item_ids in sorted(by_date.items(), reverse=True):
            history.append({
                "date": day,
                "items": [items_map[i] for i in item_ids if i in items_map],
            })

        return {"success": True, "history": history}

    except Exception as e:
        print(f"Error fetching wear history: {e}")
        return {"success": True, "history": []}
