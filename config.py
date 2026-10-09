import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-fallback-secret-key-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLite Database default location in instance/ directory
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{INSTANCE_DIR / 'expense_detector.db'}"
    )

    # ML Configuration
    ML_MODELS_DIR = Path(os.getenv("ML_MODELS_DIR", INSTANCE_DIR / "models"))
    MIN_TRANSACTIONS_FOR_ML = int(os.getenv("MIN_TRANSACTIONS_FOR_ML", 15))
    CONTAMINATION_RATE = float(os.getenv("CONTAMINATION_RATE", 0.08))

    # Scheduler Configuration
    ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "true").lower() in ("true", "1", "yes")
    SCHEDULER_INTERVAL_HOURS = int(os.getenv("SCHEDULER_INTERVAL_HOURS", 6))

    # CORS settings
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


from sqlalchemy.pool import StaticPool


class TestingConfig(Config):
    """Testing configuration with in-memory or isolated SQLite."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }
    ENABLE_SCHEDULER = False
    MIN_TRANSACTIONS_FOR_ML = 10
    ML_MODELS_DIR = INSTANCE_DIR / "test_models"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # Ensure a secure secret key is set in production
    SECRET_KEY = os.getenv("SECRET_KEY")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
