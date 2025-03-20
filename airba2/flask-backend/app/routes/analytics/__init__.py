"""
Инициализационный файл для аналитического модуля.
Объединяет все маршруты и namespace в один модуль.
"""
from flask_restx import Api
from .analytics import analytics_ns
from .dashboard_routes import register_dashboard_routes
from .predictions_routes import register_prediction_routes
from .reports_routes import register_report_routes
from .product_routes import register_product_routes
from .category_routes import register_category_routes
from .store_routes import register_store_routes

def register_analytics_namespace():
    """Регистрирует namespace для аналитики"""
    # Эта функция должна фактически добавлять namespace в API
    from .. import api  # Импортируем api из корневого пакета routes
    api.add_namespace(analytics_ns)
    
    # Регистрируем все маршруты в namespace
    register_dashboard_routes(analytics_ns)
    register_prediction_routes(analytics_ns)
    register_report_routes(analytics_ns)
    register_product_routes(analytics_ns)
    register_category_routes(analytics_ns)
    register_store_routes(analytics_ns)

def setup_analytics_routes(api: Api):
    """
    Настраивает все маршруты аналитического модуля
    
    Args:
        api: Flask-RESTX API экземпляр
    """
    # Регистрируем namespace с тегами для группировки в Swagger UI
    api.add_namespace(analytics_ns)
    
    # Регистрируем все маршруты в namespace
    register_dashboard_routes(analytics_ns)
    register_prediction_routes(analytics_ns)
    register_report_routes(analytics_ns)
    register_product_routes(analytics_ns)
    register_category_routes(analytics_ns)
    register_store_routes(analytics_ns)
    
    return api
