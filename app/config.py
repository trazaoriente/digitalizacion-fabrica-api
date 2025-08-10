import os

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE: str = os.getenv("SUPABASE_SERVICE_ROLE", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "traza-docs")
    ALLOW_ORIGINS: str = os.getenv("ALLOW_ORIGINS", "*")

settings = Settings()
