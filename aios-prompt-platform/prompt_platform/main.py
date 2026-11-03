"""ASGI entry point: `uvicorn prompt_platform.main:app`."""
from prompt_platform.prompt_api.application_factory import create_app

app = create_app()
