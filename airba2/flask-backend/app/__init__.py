from datetime import datetime
from flask import Flask, Blueprint
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api
from flask_jwt_extended import JWTManager
from .config import Config
import os
import logging


# Настройка базового логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('app')

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

# Создаем экземпляр API с настройками авторизации
api = Api(api_bp,
    title="Airba Analytics API",
    version="1.0",
    description="API для аналитики продаж и прогнозирования",
    doc='/docs',  # Путь к документации относительно URL_PREFIX
    authorizations=authorizations,
    security='Bearer Auth'
)

def create_app(import_data=True):
    app = Flask(__name__, instance_relative_config=True)
    
    # Загрузка конфигурации
    app.config.from_object(Config)
    
    # Получаем настройки CORS из конфигурации или .env
    cors_origins = app.config.get('CORS_ORIGINS', '*')
    if cors_origins and cors_origins != '*':
        origins = cors_origins.split(',')
    else:
        origins = "*"  # Разрешаем все источники, если не указано иное
    
    # Настраиваем CORS с детальными параметрами
    CORS(app, resources={r"/api/*": {
        "origins": origins,
        "allow_headers": [
            "Content-Type", 
            "Authorization", 
            "Access-Control-Allow-Credentials",
            "Access-Control-Allow-Origin"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "supports_credentials": True  # Поддержка cookies и авторизации
    }})
    
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
        from .models.catalog import City, Store, CategoryGroup, Category, Product, Sale

        # Инициализируем маршруты
        routes.init_app(app)
        
        # Выводим все зарегистрированные маршруты для отладки
        logger.info("Зарегистрированные URL маршруты:")
        for rule in app.url_map.iter_rules():
            logger.info(f"{rule.endpoint}: {rule.rule}")
        
        # Важно: сначала создаем таблицы в базе данных
        logger.info("Проверка и создание структуры базы данных...")
        try:
            db.create_all()
            logger.info("Структура базы данных успешно создана/проверена")
        except Exception as e:
            logger.error(f"Ошибка при создании структуры базы данных: {str(e)}", exc_info=True)
            # В случае ошибки пытаемся продолжить работу
        
        # Проверяем, нужно ли импортировать данные
        if import_data:
            logger.info("Проверка необходимости импорта данных")
            
            # Улучшенная проверка с использованием транзакции и очисткой кэша
            try:
                # Фиксируем любые незавершенные транзакции
                db.session.commit()
                
                # Очищаем кэш сессии перед проверкой
                db.session.remove()  # Используем правильный метод вместо create_scoped_session()
                
                # Проверяем наличие данных
                data_exists = db.session.query(db.func.count(Product.id)).scalar() > 0
                
                if data_exists:
                    products_count = db.session.query(db.func.count(Product.id)).scalar()
                    stores_count = db.session.query(db.func.count(Store.id)).scalar()
                    sales_count = db.session.query(db.func.count(Sale.id)).scalar()
                    sales = db.session.query(Sale).limit(5).all()
                    print(f"\n===== ПЕРВЫЕ 5 ПРОДАЖ =====")
                    for sale in sales:
                        product = db.session.query(Product).get(sale.product_id)
                        store = db.session.query(Store).get(sale.store_id)
                        print(f"ID: {sale.id}, Дата: {sale.date}, Товар: {product.name}, Магазин: {store.name}, Количество: {sale.quantity}, Цена: {sale.price}")
                    
                    # Проверяем наличие товаров с нулевыми ценами
                    zero_price_count = db.session.query(db.func.count(Product.id)).filter(Product.price == 0).scalar()
                    
                    logger.info(f"Данные уже существуют в базе: найдено {products_count} товаров ({zero_price_count} с нулевой ценой), {stores_count} магазинов, {sales_count} записей о продажах.")
                    
                    # Если есть товары с нулевыми ценами, запускаем обновление цен
                    if zero_price_count > 0:
                        logger.info(f"Найдено {zero_price_count} товаров с нулевой ценой, запускаем обновление цен...")
                        from app.utils.import_data import import_only_prices_and_sales
                        import_only_prices_and_sales()
                    else:
                        logger.info("Все товары имеют ненулевые цены. Импорт пропущен.")
                    
                    # Добавляем файл-флаг, который покажет, что импорт уже был выполнен
                    import_flag_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.import_completed')
                    if not os.path.exists(import_flag_file):
                        with open(import_flag_file, 'w') as f:
                            f.write(f"Import completed at {datetime.now().isoformat()}")
                else:
                    # Проверяем, существует ли флаг завершенного импорта
                    import_flag_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.import_completed')
                    if os.path.exists(import_flag_file):
                        logger.info("Обнаружен флаг завершенного импорта. Повторный импорт пропущен.")
                        return app
                    
                    logger.info("Данные в базе отсутствуют, требуется импорт")
                    
                    # Импортируем функции после инициализации приложения
                    from .utils.import_data import import_all_data
                    
                    # Проверяем, существует ли директория с данными
                    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
                    data_dir_exists = os.path.exists(base_dir)
                    
                    if data_dir_exists:
                        logger.info(f"Найдена директория с данными: {base_dir}")
                        # Проверяем наличие всех необходимых файлов
                        files_exist = True
                        for subdir, filename in [
                            ('info', 'store_info.xlsx'),
                            ('stock', "Stock'22 (1).csv"),
                            ('sales', 'sales22-1.xlsx')
                        ]:
                            file_path = os.path.join(base_dir, subdir, filename)
                            if os.path.exists(file_path):
                                logger.info(f"Файл найден: {file_path}")
                            else:
                                logger.warning(f"Файл не найден: {file_path}")
                                if subdir != 'sales':  # Продажи не обязательны
                                    files_exist = False
                        
                        if files_exist:
                            try:
                                # Проверяем, нужно ли импортировать все данные или только продажи и цены
                                all_data_imported = os.path.exists(os.path.join(os.path.dirname(__file__), '..', '.all_data_imported'))
                                
                                if all_data_imported:
                                    logger.info("Основные данные уже импортированы, проверяем цены и продажи...")
                                    from app.utils.import_data import import_only_prices_and_sales
                                    import_only_prices_and_sales()
                                else:
                                    logger.info("Начинаем импорт всех данных...")
                                    from app.utils.import_data import import_all_data
                                    import_all_data()
                                    
                                    # Создаем файл-флаг, указывающий что основные данные импортированы
                                    with open(os.path.join(os.path.dirname(__file__), '..', '.all_data_imported'), 'w') as f:
                                        f.write(f"All data imported at {datetime.now().isoformat()}")
                                    
                                logger.info("Импорт данных успешно завершен")
                            except Exception as e:
                                logger.error(f"Ошибка при импорте данных: {str(e)}", exc_info=True)
                                # Если не удалось импортировать реальные данные, генерируем тестовые
                                from .utils.mock_data import generate_mock_data
                                logger.info("Генерация тестовых данных...")
                                generate_mock_data()
                                logger.info("Тестовые данные успешно сгенерированы")
                        else:
                            # Если необходимых файлов нет, генерируем тестовые данные
                            from .utils.mock_data import generate_mock_data
                            logger.info("Необходимые файлы данных не найдены. Генерация тестовых данных...")
                            generate_mock_data()
                            logger.info("Тестовые данные успешно сгенерированы")
                    else:
                        # Если директории нет, генерируем тестовые данные
                        from .utils.mock_data import generate_mock_data
                        logger.info(f"Директория с реальными данными не найдена: {base_dir}. Генерация тестовых данных...")
                        generate_mock_data()
                        logger.info("Тестовые данные успешно сгенерированы")
            except Exception as e:
                logger.error(f"Ошибка при проверке данных: {str(e)}", exc_info=True)
                # Если произошла ошибка, перегенерируем тестовые данные
                try:
                    from .utils.mock_data import generate_mock_data
                    logger.info("Генерация тестовых данных из-за ошибки...")
                    generate_mock_data()
                    logger.info("Тестовые данные успешно сгенерированы")
                except Exception as inner_e:
                    logger.error(f"Ошибка при генерации тестовых данных: {str(inner_e)}", exc_info=True)

    return app