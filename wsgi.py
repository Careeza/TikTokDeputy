"""
WSGI wrapper for PythonAnywhere
This converts the FastAPI ASGI app to WSGI for compatibility with PythonAnywhere
"""
from main import app
from asgiref.wsgi import ASGIHandler

# Convert ASGI application to WSGI
application = ASGIHandler(app)