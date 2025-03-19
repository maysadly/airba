import pytest
from app import create_app, db
from app.models.user import User

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_create_user(client):
    response = client.post('/api/users', json={
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'password123'
    })
    assert response.status_code == 201
    assert response.json['username'] == 'testuser'

def test_get_user(client):
    client.post('/api/users', json={
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'password123'
    })
    response = client.get('/api/users/testuser')
    assert response.status_code == 200
    assert response.json['username'] == 'testuser'

def test_user_not_found(client):
    response = client.get('/api/users/nonexistent')
    assert response.status_code == 404
    assert response.json['message'] == 'User not found'