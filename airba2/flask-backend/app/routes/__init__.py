from flask import Blueprint

api = Blueprint('api', __name__)

from . import api  # Import routes from api.py to register them with the blueprint

def init_app(app):
    # Импортируем API ресурсы
    from .api import register_namespaces
    
    register_namespaces()