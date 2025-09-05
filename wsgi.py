# wsgi.py
import os
from app import app as application  # 'application' es el nombre WSGI estándar

# Opcional: variables de entorno para producción
os.environ.setdefault("FLASK_ENV", "production")
