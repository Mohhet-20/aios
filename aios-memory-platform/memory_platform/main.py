"""ASGI entry point: `uvicorn memory_platform.main:app`."""
from memory_platform.memory_api.application_factory import create_app

app = create_app()
