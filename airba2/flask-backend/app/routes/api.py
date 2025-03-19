from flask_restx import Namespace, Resource, fields
from flask import request
from .. import api, db
from ..models.user import User
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity

# Создаем пространства имен для API ресурсов
user_ns = Namespace('users', description='Операции с пользователями')

# Модели данных для Swagger
user_model = user_ns.model('User', {
    'id': fields.Integer(readonly=True, description='Уникальный ID пользователя'),
    'username': fields.String(required=True, description='Имя пользователя'),
    'password_hash': fields.String(required=True, description='Хеш пароля пользователя')
})

def register_namespaces():
    # Импортируем из auth.py
    from .auth import auth_ns
    
    # Регистрируем пространства имен в api
    api.add_namespace(user_ns)
    api.add_namespace(auth_ns)

@user_ns.route('/')
class UserList(Resource):
    @user_ns.doc('list_users')
    @jwt_required()
    @user_ns.marshal_list_with(user_model)
    def get(self):
        """Получить список всех пользователей"""
        # Пользователь проходит аутентификацию с помощью токена
        # Получаем identity из JWT
        current_user_id = get_jwt_identity()
        # При необходимости можно проверить разрешения пользователя
        
        return User.query.all()
    
    @user_ns.doc('create_user')
    @user_ns.expect(user_model)
    @user_ns.marshal_with(user_model, code=201)
    def post(self):
        """Создать нового пользователя"""
        # Логика создания пользователя
        return {}, 201

@user_ns.route('/<int:id>')
@user_ns.param('id', 'ID пользователя')
class UserResource(Resource):
    @user_ns.doc('get_user')
    @jwt_required()  # Используем встроенный декоратор JWT
    @user_ns.marshal_with(user_model)
    def get(self, id):
        """Получить пользователя по ID"""
        return User.query.get_or_404(id)