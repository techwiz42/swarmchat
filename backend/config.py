import os
from dotenv import load_dotenv
import secrets

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# Database URLs for different environments
DATABASE_URLS = {
    "development": "postgresql+asyncpg://postgres:postgres@localhost:5432/swarmchat_dev",
    "production": "postgresql+asyncpg://postgres:postgres@localhost:5432/swarmchat"
}

# Get the appropriate database URL based on environment
DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_URLS[ENVIRONMENT])

