from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    """Get Supabase client for REST API operations"""
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )

# Create a single instance
supabase = get_supabase_client()