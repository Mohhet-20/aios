"""ASGI entry point: `uvicorn app.main:app`. Kept to a single line of real
logic — all configuration lives in `app.core.application_factory` — so
this file never needs to change as the app grows.
"""

from app.core.application_factory import create_app

app = create_app()
