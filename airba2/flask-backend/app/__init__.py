from flask import Flask, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
from flask_jwt_extended import JWTManager
from .config import Config

db = SQLAlchemy()
jwt = JWTManager()

# Создаем экземпляр API с настройками авторизации
authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': "Введите токен в формате: 'Bearer ваш_токен'",
    }
}

# Используем Blueprint для более гибкой настройки API
api_bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(api_bp,
    title="Airba API",
    version="1.0",
    description="API документация для Airba Backend",
    doc='/docs',
    authorizations=authorizations,
    security='Bearer Auth'
)

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    CORS(app)
    
    # Загрузка конфигурации
    app.config.from_object(Config)
    
    # Дополнительные настройки JWT
    app.config['JWT_HEADER_TYPE'] = ''  # Убираем префикс Bearer для возможности отправки только токена
    app.config['JWT_IDENTITY_CLAIM'] = 'sub'  # Указываем стандартное утверждение sub для identity
    
    db.init_app(app)
    jwt.init_app(app)
    
    # Добавляем обработчики ошибок JWT
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return {'msg': 'Invalid token: ' + error_string}, 401
    
    @jwt.unauthorized_loader
    def unauthorized_callback(error_string):
        return {'msg': 'Missing Authorization header: ' + error_string}, 401
    
    # Регистрируем blueprint для API
    app.register_blueprint(api_bp)

    with app.app_context():
        from . import routes
        from .models import user

        routes.init_app(app)

    return app