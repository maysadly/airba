from flask_restx import Namespace, Resource, fields
from flask import request
from .. import api, db
from ..models.user import User
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    jwt_required, 
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash

# Создаем пространство имен для авторизации
auth_ns = Namespace('auth', description='Операции авторизации')

# Модель для запроса логина/регистрации
login_model = auth_ns.model('Login', {
    'username': fields.String(required=True, description='Имя пользователя'),
    'password': fields.String(required=True, description='Пароль пользователя')
})

# Модель ответа с токенами
tokens_model = auth_ns.model('Tokens', {
    'access_token': fields.String(description='JWT токен доступа'),
    'refresh_token': fields.String(description='JWT токен обновления')
})

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.doc('user_login')
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(tokens_model)
    def post(self):
        """Авторизация пользователя и получение JWT токенов"""
        data = request.json
        
        user = User.query.filter_by(username=data['username']).first()
        
        if not user or not check_password_hash(user.password_hash, data['password']):
            auth_ns.abort(401, 'Неверное имя пользователя или пароль')
            
        # Используем строку для identity, а не число
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.doc('user_register')
    @auth_ns.expect(login_model)
    def post(self):
        """Регистрация нового пользователя"""
        data = request.json
        
        if User.query.filter_by(username=data['username']).first():
            auth_ns.abort(409, 'Пользователь с таким именем уже существует')
            
        new_user = User(
            username=data['username'],
            password_hash=generate_password_hash(data['password'])
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return {'message': 'Пользователь успешно зарегистрирован'}, 201
        except:
            db.session.rollback()
            auth_ns.abort(500, 'Произошла ошибка при регистрации пользователя')

@auth_ns.route('/refresh')
class RefreshToken(Resource):
    @auth_ns.doc('refresh_token')
    @jwt_required(refresh=True)
    @auth_ns.marshal_with(tokens_model)
    def post(self):
        """Обновление токена доступа с помощью токена обновления"""
        current_user = get_jwt_identity()
        # Преобразуем identity в строку для безопасности
        access_token = create_access_token(identity=str(current_user))
        refresh_token = create_refresh_token(identity=str(current_user))
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }