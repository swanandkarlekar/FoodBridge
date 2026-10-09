import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "foodbridge-dev-secret-key-change-in-production-2026")
    
    # SQLite Database location
    DATABASE = os.environ.get(
        "DATABASE_PATH",
        os.path.join(BASE_DIR, "instance", "foodbridge.sqlite")
    )
    
    # Session security settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Application settings
    SITE_NAME = "FoodBridge"
    ITEMS_PER_PAGE = 12
