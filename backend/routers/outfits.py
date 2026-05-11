"""
Outfit Routes

Provides outfit-level actions such as saving the accepted AI outfit as worn.
"""

import traceback
from datetime import datetime

from database import get_user_from_token
from fastapi import APIRouter, Header, HTTPException

from routers.usage import UseTodayRequest, _raise_history_error, _save_outfit_usage


router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.post("/use-today")
async def use_outfit_today(
    request: UseTodayRequest,
    authorization: str = Header(None),
):
    try:
        if not isinstance(request.outfit_items, list):
            _raise_history_error(
                400,
                "invalid_payload",
                "outfit_items must be a list of item IDs.",
                {"payload": request.dict()},
            )
        user = get_user_from_token(authorization)
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        return await _save_outfit_usage(
            user_id=user.user.id,
            outfit_item_ids=request.outfit_items,
            source=request.source or "ai_suggestion",
            used_at=request.used_at or datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        print("[OutfitHistory][EXCEPTION]", repr(e))
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to save outfit usage",
                "error": str(e),
                "type": type(e).__name__,
            },
        )
