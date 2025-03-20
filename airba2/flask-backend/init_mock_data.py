from app import create_app, db
from app.utils.mock_data import generate_mock_data

def init_mock_data():
    app = create_app()
    with app.app_context():
        # Генерируем тестовые данные
        generate_mock_data()

if __name__ == "__main__":
    init_mock_data()