"""ASGI entry point: `uvicorn agent_platform.main:app`."""
from agent_platform.agent_api.application_factory import create_app

app = create_app()
