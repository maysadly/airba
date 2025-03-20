from .. import db
from datetime import datetime

class City(db.Model):
    __tablename__ = 'cities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(100), nullable=True)
    population = db.Column(db.Integer, nullable=True)
    
    # Связь с магазинами
    stores = db.relationship('Store', backref='city', lazy=True)
    
    def __repr__(self):
        return f'<City {self.name}>'

class Store(db.Model):
    __tablename__ = 'stores'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    size = db.Column(db.Float, nullable=True)  # Размер магазина в кв. метрах
    opening_date = db.Column(db.Date, nullable=True)
    
    # Связь с продажами
    sales = db.relationship('Sale', backref='store', lazy=True)
    
    def __repr__(self):
        return f'<Store {self.name}>'

class CategoryGroup(db.Model):
    __tablename__ = 'category_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Связь с категориями
    categories = db.relationship('Category', backref='group', lazy=True)

    def __repr__(self):
        return f'<CategoryGroup {self.name}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('category_groups.id'), nullable=False)
    
    # Прямая связь с товарами (без подкатегорий)
    products = db.relationship('Product', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)  # Изменено с subcategory_id на category_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связь с продажами
    sales = db.relationship('Sale', backref='product', lazy=True)

    def __repr__(self):
        return f'<Product {self.name}>'

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Sale {self.id} of Product {self.product_id} in Store {self.store_id}>'