"""Root application entry point.

Exposes the FastAPI application instance for uvicorn:
    uvicorn main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Ensure root directory is on sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from webapp.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
