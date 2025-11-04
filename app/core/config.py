import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Project Info
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Spotive API")
    API_V1_STR: str = "/api/v1"
    
    # Environment Detection
    IS_VERCEL: bool = os.getenv("VERCEL", "").lower() in ["1", "true"]
    IS_PRODUCTION: bool = os.getenv("PRODUCTION", "").lower() in ["1", "true"] or os.getenv("VERCEL", "").lower() in ["1", "true"]
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://wopjezlgtborpnhcfvoc.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndvcGplemxndGJvcnBuaGNmdm9jIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjIyNjUyOTcsImV4cCI6MjA3Nzg0MTI5N30.FAQkFVZSqOAe4bsvxNJ0LPOFXbKVaxxZ10OfzZvfRnk")
    
    # LLM Configuration
    # Auto-detect: Use OpenAI in production/Vercel, Ollama locally
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai" if os.getenv("VERCEL", "").lower() in ["1", "true"] else "ollama")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo" if os.getenv("VERCEL", "").lower() in ["1", "true"] else "gemma3")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

settings = Settings()