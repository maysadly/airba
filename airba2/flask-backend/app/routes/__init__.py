from flask import Blueprint, redirect, url_for
from flask_restx import Api

api = Blueprint('api', __name__)

def init_app(app):
    # Регистрация blueprint для API
    from .. import api as flask_restx_api
    
    # Добавляем перенаправление с корневого пути на документацию API
    @app.route('/')
    def index():
        return redirect('/api/docs')
    
    # Обновляем порядок регистрации - регистрируем маршруты через register_routes
    register_routes(flask_restx_api)

def register_routes(api):
    """
    Регистрирует все маршруты API
    
    Args:
        api: Flask-RESTX API экземпляр
    """
    # Импорт здесь для избежания циклических зависимостей
    from .auth import register_auth_routes  # Используем существующий auth.py вместо user_routes
    from .analytics import setup_analytics_routes
    
    # Регистрация маршрутов
    register_auth_routes(api)  # Предполагаем, что auth.py содержит функцию register_auth_routes
    
    # Регистрация аналитического модуля со всеми подмодулями
    setup_analytics_routes(api)
    
    return api