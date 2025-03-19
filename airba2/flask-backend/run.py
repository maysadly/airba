from app import create_app, db
import os

app = create_app()

# При первом запуске создаем таблицы базы данных
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Получаем настройки из переменных окружения или используем значения по умолчанию
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5050))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)