from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env from project root if present
PROJECT_ROOT = Path(__file__).resolve().parents[1]
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

APP_NAME = os.getenv("APP_NAME")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))
