"""Shared Supabase helpers for the ingestion scripts."""
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def get_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
    return create_client(url, key)


def owner_map(sb, platform):
    """platform_user_id -> owner_id for a platform."""
    rows = sb.table("owner_identities").select("owner_id, platform_user_id") \
        .eq("platform", platform).execute().data
    return {r["platform_user_id"]: r["owner_id"] for r in rows}


def ensure_owner(sb, platform, platform_user_id, name, cache):
    """Return owner_id for a platform account, creating owner+identity if new.

    `cache` is a dict (platform_user_id -> owner_id) kept across calls so an
    owner already merged/known on another platform is reused, never duplicated.
    """
    if platform_user_id in cache:
        return cache[platform_user_id]
    # Maybe the identity exists but wasn't in the initial cache.
    existing = sb.table("owner_identities").select("owner_id") \
        .eq("platform", platform).eq("platform_user_id", platform_user_id).execute().data
    if existing:
        oid = existing[0]["owner_id"]
    else:
        oid = sb.table("owners").insert({"display_name": name}).execute().data[0]["owner_id"]
        sb.table("owner_identities").insert({
            "owner_id": oid, "platform": platform,
            "platform_user_id": platform_user_id, "platform_name": name,
        }).execute()
    cache[platform_user_id] = oid
    return oid


def upsert_season(sb, platform, league_id, year, name, settings=None):
    sb.table("seasons").upsert(
        {"platform": platform, "league_id": str(league_id), "year": int(year),
         "name": name, "settings": settings or {}},
        on_conflict="platform,league_id,year",
    ).execute()
    return sb.table("seasons").select("season_id") \
        .eq("platform", platform).eq("league_id", str(league_id)).eq("year", int(year)) \
        .execute().data[0]["season_id"]
