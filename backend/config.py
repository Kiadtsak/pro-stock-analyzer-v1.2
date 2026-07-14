"""Backend configuration."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Data storage
DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8300))          # different from other systems

# APIs (optional — used if user wants live data)
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
