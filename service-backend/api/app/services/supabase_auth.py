from supabase import create_client
from app.core.config import settings


def get_supabase_public():
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_supabase_admin():
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
