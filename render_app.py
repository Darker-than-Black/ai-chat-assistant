"""WSGI entrypoint for Render/Gunicorn deployments."""

from main import create_web_app

app = create_web_app()
