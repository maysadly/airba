from app import create_app, db
from app.models.user import User
from werkzeug.security import generate_password_hash

def init_db():
    app = create_app()
    with app.app_context():
        # Пересоздаем все таблицы
        db.drop_all()
        db.create_all()
        
        # Создаем тестового пользователя
        if not User.query.filter_by(username='admin').first():
            user = User(
                username='admin',
                password_hash=generate_password_hash('admin')
            )
            db.session.add(user)
            db.session.commit()
            print("Admin user created successfully!")

if __name__ == "__main__":
    init_db()