from app import create_app, db
import os
import logging

# Импортируем функцию для генерации тестовых данных
from app.utils.mock_data import generate_mock_data

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

# При первом запуске создаем таблицы базы данных и заполняем тестовыми данными
with app.app_context():
    db.create_all()
    
    # Проверяем, есть ли уже данные в базе
    try:
        from app.models.catalog import CategoryGroup
        category_groups_count = CategoryGroup.query.count()
        
        if category_groups_count == 0:
            logger.info("База данных пуста. Инициализация тестовых данных...")
            generate_mock_data()
            logger.info("Тестовые данные успешно созданы!")
        else:
            logger.info(f"В базе уже есть данные: {category_groups_count} групп категорий. Пропускаем инициализацию.")
    except Exception as e:
        logger.error(f"Ошибка при инициализации тестовых данных: {str(e)}")

if __name__ == '__main__':
    # Проверяем, был ли уже выполнен импорт
    import_flag_file = os.path.join(os.path.dirname(__file__), '.import_completed')
    import_data = not os.path.exists(import_flag_file)
    
    # Если файл существует, используем параметр import_data=False
    app = create_app(import_data=import_data)
    
    # Получаем настройки из переменных окружения или используем значения по умолчанию
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5050))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Запуск Flask сервера на {host}:{port} (debug={debug})")
    app.run(host=host, port=port, debug=debug)