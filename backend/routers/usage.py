"""
Usage History Routes

Endpoints for tracking what the user wore and when.
- POST /usage/record  - Record that items were worn today
- GET  /usage/history - Get the wear history (last N days)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from database import get_user_from_token, supabase
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from services.wardrobe_service import WardrobeService

router = APIRouter(prefix="/usage", tags=["usage"])
wardrobe_service = WardrobeService()

KNOWN_TABLE_COLUMNS = {
    "outfits": ["id", "user_id", "name", "description", "is_favorite", "created_at"],
    "outfit_items": ["id", "outfit_id", "clothing_id"],
    "usage_history": ["id", "user_id", "clothing_id", "worn_date", "weather_condition"],
}


def _history_db():
    return wardrobe_service.supabase


class RecordUsageRequest(BaseModel):
    item_ids: List[str]
    occasion: Optional[str] = None
    worn_date: Optional[str] = None   # ISO date string, defaults to today


class UseTodayRequest(BaseModel):
    outfit_items: List[str]
    source: Optional[str] = "ai_suggestion"
    used_at: Optional[str] = None


def _dedupe_item_ids(item_ids: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for item_id in item_ids:
        item_id = str(item_id)
        if item_id and item_id not in seen:
            deduped.append(item_id)
            seen.add(item_id)
    return deduped


def _raise_history_error(
    status_code: int,
    reason: str,
    detail: str,
    debug_details: Any = None,
) -> None:
    print(f"[OutfitHistory][ERROR] reason={reason}")
    print(f"[OutfitHistory][ERROR] details={debug_details}")
    raise HTTPException(
        status_code=status_code,
        detail={
            "detail": detail,
            "debug_reason": reason,
            "debug_details": debug_details,
        },
    )


def _safe_payload(payload: Any) -> Any:
    if isinstance(payload, list):
        return [_safe_payload(item) for item in payload]
    if isinstance(payload, dict):
        return dict(payload)
    return payload


def _filter_payload_for_columns(payload: Dict[str, Any], columns: List[str]) -> Dict[str, Any]:
    if not columns:
        return payload
    return {
        key: value
        for key, value in payload.items()
        if key in columns
    }


def _log_table_columns(table_name: str) -> List[str]:
    try:
        response = (
            _history_db()
            .schema("information_schema")
            .table("columns")
            .select("column_name")
            .eq("table_schema", "public")
            .eq("table_name", table_name)
            .execute()
        )
        columns = [row.get("column_name") for row in (response.data or []) if row.get("column_name")]
        print(f"[OutfitHistory] table_columns table={table_name} columns={columns}")
        if columns:
            return columns
    except Exception as exc:
        print(f"[OutfitHistory] table_columns_probe_failed table={table_name} error={exc}")

    try:
        response = _history_db().table(table_name).select("*").limit(1).execute()
        rows = response.data or []
        columns = list(rows[0].keys()) if rows else []
        print(f"[OutfitHistory] table_sample_columns table={table_name} columns={columns}")
        return columns or KNOWN_TABLE_COLUMNS.get(table_name, [])
    except Exception as exc:
        print(f"[OutfitHistory] table_sample_probe_failed table={table_name} error={exc}")
        return KNOWN_TABLE_COLUMNS.get(table_name, [])


async def _load_user_wardrobe_same_as_ai(user_id: str) -> List[Dict[str, Any]]:
    try:
        items = await wardrobe_service.get_user_wardrobe(
            user_id=user_id,
            only_clean=False,
            exclude_item_ids=None,
        )
        print(f"[OutfitHistory] current_user_id={user_id}")
        print(f"[OutfitHistory] total_loaded_user_items={len(items)}")
        print(
            "[OutfitHistory] loaded_user_item_ids="
            f"{[str(item.get('id')) for item in items if item.get('id')]}"
        )
        return items
    except Exception as exc:
        _raise_history_error(
            500,
            "invalid_item_ids",
            "Could not load wardrobe for ownership validation.",
            {
                "user_id": user_id,
                "query_source": "same_as_ai_outfit_today",
                "error": str(exc),
            },
        )


def _fetch_user_items(user_id: str, item_ids: List[str]) -> List[Dict[str, Any]]:
    if not item_ids:
        return []
    try:
        response = (
            _history_db().table("clothes")
            .select("*")
            .eq("user_id", user_id)
            .in_("id", item_ids)
            .execute()
        )
        return response.data or []
    except Exception as exc:
        _raise_history_error(
            500,
            "invalid_item_ids",
            "Could not load outfit item details.",
            {"item_ids": item_ids, "error": str(exc)},
        )


def _item_sort_key(item: Dict[str, Any]) -> Tuple[int, str]:
    layer = item.get("layer")
    try:
        layer_value = int(layer)
    except (TypeError, ValueError):
        layer_value = 99
    return layer_value, str(item.get("name") or "")


def _same_outfit(left: List[str], right: List[str]) -> bool:
    return sorted(str(item_id) for item_id in left) == sorted(str(item_id) for item_id in right)


def _invalid_uuid_ids(item_ids: List[str]) -> List[str]:
    invalid = []
    for item_id in item_ids:
        try:
            UUID(str(item_id))
        except (TypeError, ValueError):
            invalid.append(str(item_id))
    return invalid


def _row_item_id(row: Dict[str, Any]) -> Optional[str]:
    return (
        row.get("clothing_item_id")
        or row.get("clothes_id")
        or row.get("clothing_id")
        or row.get("item_id")
    )


def _row_item_ids(row: Dict[str, Any]) -> List[str]:
    explicit_items = (
        row.get("outfit_items")
        or row.get("item_ids")
        or row.get("clothing_ids")
    )
    if isinstance(explicit_items, list):
        return [str(item_id) for item_id in explicit_items if item_id]
    item_id = _row_item_id(row)
    return [str(item_id)] if item_id else []


def _fetch_outfit_item_ids(outfit_ids: List[str]) -> Dict[str, List[str]]:
    if not outfit_ids:
        return {}

    for item_column in ("clothing_item_id", "clothes_id", "clothing_id", "item_id"):
        try:
            response = (
                _history_db().table("outfit_items")
                .select(f"outfit_id, {item_column}")
                .in_("outfit_id", outfit_ids)
                .execute()
            )
            rows = response.data or []
            result: Dict[str, List[str]] = {}
            for row in rows:
                outfit_id = row.get("outfit_id")
                item_id = row.get(item_column)
                if outfit_id and item_id:
                    result.setdefault(str(outfit_id), []).append(str(item_id))
            if result:
                return result
        except Exception as exc:
            print(f"[OutfitHistory] outfit_items_fetch_failed column={item_column} error={exc}")
    return {}


def _find_existing_usage_for_day(
    user_id: str,
    outfit_item_ids: List[str],
    used_day: str,
) -> Optional[Dict[str, Any]]:
    start = f"{used_day}T00:00:00"
    end = f"{used_day}T23:59:59.999999"
    try:
        response = (
            _history_db().table("usage_history")
            .select("*")
            .eq("user_id", user_id)
            .gte("worn_date", start)
            .lte("worn_date", end)
            .execute()
        )
        rows = response.data or []
    except Exception:
        rows = []
    if not rows:
        try:
            response = (
                _history_db().table("usage_history")
                .select("*")
                .eq("user_id", user_id)
                .gte("used_at", start)
                .lte("used_at", end)
                .execute()
            )
            rows = response.data or []
        except Exception:
            rows = []

    outfit_ids = [
        str(row.get("outfit_id"))
        for row in rows
        if row.get("outfit_id")
    ]
    outfit_items_by_id = _fetch_outfit_item_ids(outfit_ids)

    for row in rows:
        row_item_ids = _row_item_ids(row)
        outfit_id = row.get("outfit_id")
        if not row_item_ids and outfit_id:
            row_item_ids = outfit_items_by_id.get(str(outfit_id), [])
        if row_item_ids and _same_outfit(row_item_ids, outfit_item_ids):
            return {
                "outfit_id": outfit_id,
                "usage_history_id": row.get("id"),
                "rows": [row],
            }

    by_outfit: Dict[str, List[Dict[str, Any]]] = {}
    no_outfit_rows = []
    for row in rows:
        outfit_id = row.get("outfit_id")
        if outfit_id:
            by_outfit.setdefault(str(outfit_id), []).append(row)
        else:
            no_outfit_rows.append(row)

    for outfit_id, outfit_rows in by_outfit.items():
        row_item_ids = [str(_row_item_id(row)) for row in outfit_rows if _row_item_id(row)]
        if _same_outfit(row_item_ids, outfit_item_ids):
            return {
                "outfit_id": outfit_id,
                "usage_history_id": outfit_rows[0].get("id"),
                "rows": outfit_rows,
            }

    no_outfit_item_ids = [str(_row_item_id(row)) for row in no_outfit_rows if _row_item_id(row)]
    if no_outfit_item_ids and _same_outfit(no_outfit_item_ids, outfit_item_ids):
        return {
            "outfit_id": None,
            "usage_history_id": no_outfit_rows[0].get("id"),
            "rows": no_outfit_rows,
        }
    return None


def _create_outfit(user_id: str, source: str, used_at: str) -> Optional[str]:
    columns = _log_table_columns("outfits")
    base_payload = {
        "id": str(uuid4()),
        "user_id": user_id,
        "source": source,
        "created_at": used_at,
    }
    for payload in (
        {
            "id": base_payload["id"],
            "user_id": user_id,
            "name": f"Outfit {used_at[:10]}",
            "source": source,
            "created_at": used_at,
        },
        {
            "id": base_payload["id"],
            "user_id": user_id,
            "name": f"Outfit {used_at[:10]}",
            "created_at": used_at,
        },
        base_payload,
        {key: value for key, value in base_payload.items() if key != "source"},
        {"user_id": user_id},
    ):
        if columns:
            payload = _filter_payload_for_columns(payload, columns)
            if "user_id" not in payload:
                continue
        try:
            print(f"[OutfitHistory] inserting_outfit payload={_safe_payload(payload)}")
            response = _history_db().table("outfits").insert(payload).execute()
            print(f"[OutfitHistory] outfit_insert_response={response.data}")
            row = (response.data or [{}])[0]
            return str(row.get("id") or payload.get("id"))
        except Exception as exc:
            print(
                "[OutfitHistory][ERROR] reason=supabase_outfit_insert_failed"
            )
            print(
                "[OutfitHistory][ERROR] details="
                f"payload_keys={list(payload.keys())} error={exc}"
            )
    return None


def _save_outfit_items(outfit_id: Optional[str], item_ids: List[str]) -> bool:
    if not outfit_id:
        return False
    columns = _log_table_columns("outfit_items")
    item_columns = ["clothing_item_id", "clothes_id", "clothing_id", "item_id"]
    if columns:
        item_columns = [column for column in item_columns if column in columns]
    attempts = []
    for item_column in item_columns:
        rows = []
        for item_id in item_ids:
            payload = {
                "id": str(uuid4()),
                "outfit_id": outfit_id,
                item_column: item_id,
            }
            rows.append(_filter_payload_for_columns(payload, columns))
        if rows and all("outfit_id" in row and item_column in row for row in rows):
            attempts.append(rows)
    for rows in attempts:
        try:
            print(f"[OutfitHistory] inserting_outfit_items payload={_safe_payload(rows)}")
            _history_db().table("outfit_items").insert(rows).execute()
            print("[OutfitHistory] outfit_items_insert_response=success")
            return True
        except Exception as exc:
            print(
                "[OutfitHistory][ERROR] reason=supabase_outfit_items_insert_failed"
            )
            print(
                "[OutfitHistory][ERROR] details="
                f"keys={list(rows[0].keys())} error={exc}"
            )
    return False


def _insert_usage_rows(
    user_id: str,
    outfit_id: Optional[str],
    item_ids: List[str],
    source: str,
    used_at: str,
) -> List[Dict[str, Any]]:
    columns = _log_table_columns("usage_history")
    usage_id = str(uuid4())
    attempts = []
    if not columns or "outfit_items" in columns:
        for date_column in ("used_at", "worn_date"):
            payload = {
                "id": usage_id,
                "user_id": user_id,
                "outfit_id": outfit_id,
                "outfit_items": item_ids,
                date_column: used_at,
                "source": source,
            }
            filtered = _filter_payload_for_columns(payload, columns)
            if "user_id" in filtered and "outfit_items" in filtered:
                attempts.append([filtered])

    item_columns = ["clothing_item_id", "clothes_id", "clothing_id", "item_id"]
    if columns:
        item_columns = [column for column in item_columns if column in columns]
    for item_column in item_columns:
        date_columns = [column for column in ("used_at", "worn_date") if not columns or column in columns]
        if not date_columns:
            date_columns = [None]
        for date_column in date_columns:
            rows = []
            for item_id in item_ids:
                payload = {
                    "id": str(uuid4()),
                    "user_id": user_id,
                    "outfit_id": outfit_id,
                    item_column: item_id,
                    "source": source,
                    "weather_condition": source,
                }
                if date_column:
                    payload[date_column] = used_at
                rows.append(_filter_payload_for_columns(payload, columns))
            if rows and all("user_id" in row and item_column in row for row in rows):
                attempts.append(rows)
    for rows in attempts:
        try:
            print(f"[OutfitHistory] inserting_usage_history payload={_safe_payload(rows)}")
            response = _history_db().table("usage_history").insert(rows).execute()
            print(f"[OutfitHistory] usage_history_insert_response={response.data}")
            print(f"[OutfitHistory] created usage_history_id={(response.data or rows)[0].get('id')}")
            return response.data or rows
        except Exception as exc:
            print("[OutfitHistory][ERROR] reason=supabase_usage_insert_failed")
            print(
                "[OutfitHistory][ERROR] details="
                f"keys={list(rows[0].keys())} error={exc}"
            )
    _raise_history_error(
        500,
        "supabase_usage_insert_failed",
        "Could not save outfit usage history.",
        {"item_ids": item_ids, "outfit_id": outfit_id},
    )


def _format_history_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "type": item.get("type"),
        "color": item.get("color"),
        "style": item.get("style"),
        "occasion": item.get("occasion"),
        "status": item.get("status"),
        "image": item.get("image") or item.get("image_url"),
        "layer": item.get("layer"),
    }


async def _save_outfit_usage(
    user_id: str,
    outfit_item_ids: List[str],
    source: str,
    used_at: str,
) -> Dict[str, Any]:
    item_ids = _dedupe_item_ids(outfit_item_ids)
    print(f"[OutfitHistory] use_today request user_id={user_id}")
    print(f"[OutfitHistory] item_ids={item_ids}")
    if not item_ids:
        _raise_history_error(
            400,
            "no_item_ids",
            "outfit_items cannot be empty",
            {"payload_item_ids": outfit_item_ids},
        )
    invalid_ids = _invalid_uuid_ids(item_ids)
    if invalid_ids:
        _raise_history_error(
            400,
            "invalid_item_ids",
            "Some outfit item IDs are invalid UUIDs.",
            {"invalid_item_ids": invalid_ids, "requested_item_ids": item_ids},
        )

    user_items = await _load_user_wardrobe_same_as_ai(user_id)
    owned_ids = {
        str(item.get("id"))
        for item in user_items
        if item.get("id")
    }
    missing_ids = [item_id for item_id in item_ids if item_id not in owned_ids]
    if missing_ids:
        _raise_history_error(
            400,
            "items_not_owned_by_user",
            "Some outfit items do not belong to this user.",
            {
                "requested_item_ids": item_ids,
                "owned_item_ids": sorted(owned_ids),
                "missing_item_ids": missing_ids,
                "user_id": user_id,
                "loaded_user_item_ids": sorted(owned_ids),
                "query_source": "same_as_ai_outfit_today",
            },
        )
    print("[OutfitHistory] validation_passed")

    user_items = [
        item for item in user_items
        if str(item.get("id")) in set(item_ids)
    ]
    used_day = used_at[:10]
    existing = _find_existing_usage_for_day(user_id, item_ids, used_day)
    if existing:
        print("[OutfitHistory] duplicate_outfit_today")
        print(f"[OutfitHistory] duplicate_details={existing}")
        saved_outfit_id = existing.get("outfit_id")
        usage_history_id = existing.get("usage_history_id")
        duplicate = True
    else:
        saved_outfit_id = _create_outfit(user_id, source, used_at)
        if not saved_outfit_id:
            _raise_history_error(
                500,
                "supabase_outfit_insert_failed",
                "Could not create outfit record.",
                {"user_id": user_id, "source": source, "used_at": used_at},
            )
        print(f"[OutfitHistory] created outfit_id={saved_outfit_id}")
        if not _save_outfit_items(saved_outfit_id, item_ids):
            _raise_history_error(
                500,
                "supabase_outfit_items_insert_failed",
                "Could not save outfit items.",
                {"outfit_id": saved_outfit_id, "item_ids": item_ids},
            )
        usage_rows = _insert_usage_rows(user_id, saved_outfit_id, item_ids, source, used_at)
        usage_history_id = (usage_rows[0] or {}).get("id") if usage_rows else None
        duplicate = False

    ordered_items = sorted(user_items, key=_item_sort_key)
    print(f"[OutfitHistory] accepted_outfit_item_ids={item_ids}")
    print(f"[OutfitHistory] saved_outfit_id={saved_outfit_id}")
    print(f"[OutfitHistory] usage_history_id={usage_history_id}")

    return {
        "success": True,
        "duplicate": duplicate,
        "outfit_id": saved_outfit_id,
        "usage_saved": True,
        "items_count": len(item_ids),
        "outfit": {
            "id": saved_outfit_id,
            "source": source,
            "used_at": used_at,
            "items": [_format_history_item(item) for item in ordered_items],
            "item_ids": item_ids,
        },
        "usage_history_id": usage_history_id,
    }


@router.post("/use-today")
async def use_outfit_today(
    request: UseTodayRequest,
    authorization: str = Header(None),
):
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

    used_at = request.used_at or datetime.now().isoformat()
    return await _save_outfit_usage(
        user_id=user.user.id,
        outfit_item_ids=request.outfit_items,
        source=request.source or "ai_suggestion",
        used_at=used_at,
    )


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

    saved = await _save_outfit_usage(
        user_id=user.user.id,
        outfit_item_ids=request.item_ids,
        source=request.occasion or "manual",
        used_at=request.worn_date or datetime.now().isoformat(),
    )
    return {
        **saved,
        "recorded": len(saved["outfit"]["item_ids"]),
        "total": len(request.item_ids),
    }


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
        try:
            usage_resp = (
                _history_db().table("usage_history")
                .select("*")
                .eq("user_id", user_id)
                .gte("worn_date", cutoff)
                .order("worn_date", desc=True)
                .execute()
            )
            rows = usage_resp.data or []
        except Exception:
            rows = []
        if not rows:
            try:
                usage_resp = (
                    _history_db().table("usage_history")
                    .select("*")
                    .eq("user_id", user_id)
                    .gte("used_at", cutoff)
                    .order("used_at", desc=True)
                    .execute()
                )
                rows = usage_resp.data or []
            except Exception:
                rows = []

        outfit_ids = [
            str(row.get("outfit_id"))
            for row in rows
            if row.get("outfit_id")
        ]
        outfit_items_by_id = _fetch_outfit_item_ids(outfit_ids)

        by_date: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            date_value = row.get("worn_date") or row.get("used_at") or row.get("created_at")
            row_item_ids = _row_item_ids(row)
            outfit_id = row.get("outfit_id")
            if not row_item_ids and outfit_id:
                row_item_ids = outfit_items_by_id.get(str(outfit_id), [])
            if not date_value or not row_item_ids:
                continue
            day = str(date_value)[:10]
            entry = by_date.setdefault(day, {
                "date": day,
                "outfit_id": outfit_id,
                "usage_history_id": row.get("id"),
                "source": row.get("source") or row.get("weather_condition"),
                "item_ids": [],
            })
            for item_id in row_item_ids:
                if item_id not in entry["item_ids"]:
                    entry["item_ids"].append(item_id)
            if outfit_id:
                entry["outfit_id"] = outfit_id
            if row.get("source"):
                entry["source"] = row.get("source")

        # Fetch item details for each unique item
        all_item_ids = list({
            item_id for entry in by_date.values() for item_id in entry["item_ids"]
        })
        items_map = {}
        if all_item_ids:
            items_resp = (
                _history_db().table("clothes")
                .select("id, name, type, color, style, occasion, status, image, layer")
                .eq("user_id", user_id)
                .in_("id", all_item_ids)
                .execute()
            )
            for item in (items_resp.data or []):
                items_map[item["id"]] = item

        history = []
        for day, entry in sorted(by_date.items(), reverse=True):
            history.append({
                "date": day,
                "outfit_id": entry.get("outfit_id"),
                "usage_history_id": entry.get("usage_history_id"),
                "source": entry.get("source"),
                "item_ids": entry["item_ids"],
                "items": [
                    _format_history_item(items_map[i])
                    for i in entry["item_ids"]
                    if i in items_map
                ],
            })

        print(f"[OutfitHistory] refreshed_history_count={len(history)}")
        return {"success": True, "history": history}

    except Exception as e:
        print(f"[OutfitHistory] Error fetching wear history: {e}")
        return {"success": True, "history": []}
