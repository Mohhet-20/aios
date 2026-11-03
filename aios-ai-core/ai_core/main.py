"""ASGI entrypoint: `uvicorn ai_core.main:app`."""
from ai_core.gateway.app import create_app

app = create_app()
