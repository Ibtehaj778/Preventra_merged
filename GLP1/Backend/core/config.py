from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

# Backend/ — resolved from this file so the default works regardless of the
# process working directory (uvicorn from Backend/, or a serverless runtime
# that starts in /var/task).
_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    mongodb_uri:     str
    mongodb_db_name: str = "glp1_analytics"
    data_dir:        str = str(_BACKEND_DIR / "data")
    cors_origins:    List[str] = ["http://localhost:5173", "http://localhost:4173"]

    shared_secret_key:       str
    shared_identity_db_name: str = "shared_identity"
    google_api_key:  str  = ""
    gemini_model:    str  = "gemini-3.6-flash"
    chatbot_enabled: bool = True


    class Config:
        env_file = ".env"


settings = Settings()
