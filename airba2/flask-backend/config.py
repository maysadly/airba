import os

class Config:
    """Базовая конфигурация приложения"""
    # Основные параметры
    SECRET_KEY = os.environ.get('SECRET_KEY', 'hard_to_guess_string')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Параметры JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'super-secret')
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24  # 1 day
    
    # Параметры Swagger UI
    SWAGGER_UI_DOC_EXPANSION = 'list'  # none, list, full
    SWAGGER_UI_OPERATION_ID = True
    SWAGGER_UI_REQUEST_DURATION = True
    SWAGGER_UI_JSONEDITOR = True
    SWAGGER_UI_DEEP_LINKING = True
    RESTX_MASK_SWAGGER = False  # Показывать полные модели
    SWAGGER_UI_BUNDLE_JS = '/static/swagger-ui-bundle.js'  # Убедитесь, что эти файлы существуют
    SWAGGER_UI_STANDALONE_PRESET_JS = '/static/swagger-ui-standalone-preset.js'  # или удалите эти строки
    SWAGGER_UI_CSS = '/static/swagger-ui.css'  # если вы не используете локальные ресурсы Swagger
    
    # Дополнительные параметры
    RESTX_JSON = {'ensure_ascii': False}  # Для корректной работы с кириллицей
