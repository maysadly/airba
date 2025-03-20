from flask_restx import Resource, Namespace, fields
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required
from flask import request
from ... import db
from ...models.catalog import Category, Product, Sale, Store, City
from .analytics import date_range_parser, top_product_model
from ...utils.analytics_utils import get_date_range, calculate_growth_rate
import calendar

def register_product_routes(ns: Namespace):
    """Регистрирует маршруты для аналитики по товарам"""
    
    # Правильная регистрация модели - не словарь, а прямая модель
    top_products_model = ns.model('TopProductsList', {
        'top_products': fields.List(fields.Nested(top_product_model))
    })
    
    # Определение модели для детальной аналитики без вложенных Raw полей
    product_detail_model = ns.model('ProductDetail', {
        'id': fields.Integer(description='ID товара'),
        'name': fields.String(description='Название товара'),
        'description': fields.String(description='Описание товара'),
        'category': fields.String(description='Категория товара')
    })
    
    sales_stats_model = ns.model('ProductSalesStats', {
        'total_quantity': fields.Integer(description='Общее количество проданных единиц'),
        'total_revenue': fields.Float(description='Общая выручка'),
        'avg_price': fields.Float(description='Средняя цена'),
        'transactions_count': fields.Integer(description='Количество транзакций'),
        'stores_count': fields.Integer(description='Количество магазинов'),
        'growth': fields.Float(description='Рост по сравнению с предыдущим периодом')
    })
    
    monthly_data_item_model = ns.model('ProductMonthlyDataItem', {
        'year': fields.Integer(description='Год'),
        'month': fields.Integer(description='Месяц'),
        'month_name': fields.String(description='Название месяца'),
        'quantity': fields.Integer(description='Количество проданных единиц'),
        'revenue': fields.Float(description='Выручка')
    })
    
    top_store_item_model = ns.model('ProductTopStoreItem', {
        'id': fields.Integer(description='ID магазина'),
        'name': fields.String(description='Название магазина'),
        'city': fields.String(description='Город'),
        'quantity': fields.Integer(description='Количество проданных единиц'),
        'revenue': fields.Float(description='Выручка'),
        'percentage': fields.Float(description='Процент от общей выручки')
    })
    
    charts_model = ns.model('ProductCharts', {
        'time_series': fields.List(fields.Nested(ns.model('ProductTimeSeries', {
            'x': fields.String(description='Период (месяц)'),
            'y': fields.Float(description='Значение')
        })))
    })
    
    # Полная модель ответа для детальной аналитики продукта
    product_analytics_model = ns.model('ProductAnalytics', {
        'product': fields.Nested(product_detail_model),
        'sales_stats': fields.Nested(sales_stats_model),
        'monthly_data': fields.List(fields.Nested(monthly_data_item_model)),
        'top_stores': fields.List(fields.Nested(top_store_item_model)),
        'charts': fields.Nested(charts_model)
    })
    
    @ns.route('/products/top')
    class TopProducts(Resource):
        @ns.doc('top_products', 
                description='Получить топ продаваемых товаров',
                tags=['Товары'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', top_products_model)
        @jwt_required()
        def get(self):
            """Получить топ продаваемых товаров"""
            args = date_range_parser.parse_args()
            period = args.get('period', 'month')
            limit = int(request.args.get('limit', 10))
            category_id = args.get('category_id')
            store_id = args.get('store_id')
            
            # Получаем диапазон дат на основе периода или пользовательских дат
            if args.get('start_date') and args.get('end_date'):
                try:
                    start_date = datetime.strptime(args['start_date'], '%Y-%m-%d')
                    end_date = datetime.strptime(args['end_date'], '%Y-%m-%d')
                except ValueError:
                    start_date, end_date = get_date_range(period)
            else:
                start_date, end_date = get_date_range(period)
            
            # Для сравнения трендов берем предыдущий аналогичный период
            period_days = (end_date - start_date).days
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - timedelta(days=period_days)
            
            # Базовый запрос
            query = db.session.query(
                Product.id,
                Product.name,
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue'),
                func.avg(Sale.price).label('avg_price')
            ).join(
                Sale, Product.id == Sale.product_id
            ).filter(
                Sale.date.between(start_date, end_date)
            )
            
            # Применяем фильтры
            if category_id:
                query = query.filter(Product.category_id == category_id)
            
            if store_id:
                query = query.filter(Sale.store_id == store_id)
            
            # Группируем и сортируем
            query = query.group_by(
                Product.id,
                Product.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).limit(limit)
            
            products = query.all()
            
            # Подсчитываем общую выручку за период для вычисления процентов
            total_revenue_query = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
                Sale.date.between(start_date, end_date)
            )
            
            if category_id:
                total_revenue_query = total_revenue_query.filter(Product.category_id == category_id)
            
            if store_id:
                total_revenue_query = total_revenue_query.filter(Sale.store_id == store_id)
            
            total_revenue = total_revenue_query.scalar() or 0
            
            # Форматируем результаты
            result = []
            
            for prod_id, name, quantity, revenue, avg_price in products:
                # Получаем данные за предыдущий период для вычисления роста
                prev_revenue_query = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
                    Sale.product_id == prod_id,
                    Sale.date.between(prev_start_date, prev_end_date)
                )
                
                if category_id:
                    prev_revenue_query = prev_revenue_query.filter(Product.category_id == category_id)
                
                if store_id:
                    prev_revenue_query = prev_revenue_query.filter(Sale.store_id == store_id)
                
                prev_revenue = prev_revenue_query.scalar() or 0
                
                growth = calculate_growth_rate(revenue, prev_revenue)
                percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
                
                result.append({
                    'id': prod_id,
                    'name': name,
                    'quantity': int(quantity),
                    'revenue': float(revenue),
                    'percentage': round(percentage, 2),
                    'growth': round(growth, 2),
                    'avg_price': float(avg_price)
                })
            
            return {'top_products': result}
    
    @ns.route('/products/<int:product_id>/analytics')
    @ns.param('product_id', 'ID товара')
    class ProductAnalytics(Resource):
        @ns.doc('product_analytics', 
                description='Получить подробную аналитику по конкретному товару',
                tags=['Товары'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', product_analytics_model)
        @jwt_required()
        def get(self, product_id):
            """Получить подробную аналитику по конкретному товару"""
            args = date_range_parser.parse_args()
            period = args.get('period', 'month')
            
            # Получаем диапазон дат
            if args.get('start_date') and args.get('end_date'):
                try:
                    start_date = datetime.strptime(args['start_date'], '%Y-%m-%d')
                    end_date = datetime.strptime(args['end_date'], '%Y-%m-%d')
                except ValueError:
                    start_date, end_date = get_date_range(period)
            else:
                start_date, end_date = get_date_range(period)
            
            # Получаем информацию о товаре
            product = db.session.query(
                Product.id,
                Product.name,
                Product.description,
                Category.name.label('category')
            ).join(
                Category, Product.category_id == Category.id
            ).filter(
                Product.id == product_id
            ).first()
            
            if not product:
                return {'error': 'Товар не найден'}, 404
            
            # Собираем статистику продаж
            sales_stats = db.session.query(
                func.sum(Sale.quantity).label('total_quantity'),
                func.sum(Sale.quantity * Sale.price).label('total_revenue'),
                func.avg(Sale.price).label('avg_price'),
                func.count(func.distinct(Sale.id)).label('transactions_count'),
                func.count(func.distinct(Sale.store_id)).label('stores_count')
            ).filter(
                Sale.product_id == product_id,
                Sale.date.between(start_date, end_date)
            ).first()
            
            # Получаем помесячную динамику продаж
            monthly_sales = db.session.query(
                extract('year', Sale.date).label('year'),
                extract('month', Sale.date).label('month'),
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue')
            ).filter(
                Sale.product_id == product_id,
                Sale.date.between(start_date, end_date)
            ).group_by(
                extract('year', Sale.date),
                extract('month', Sale.date)
            ).all()
            
            monthly_data = []
            for year, month, quantity, revenue in monthly_sales:
                month_name = datetime(int(year), int(month), 1).strftime('%B')
                monthly_data.append({
                    'year': int(year),
                    'month': int(month),
                    'month_name': month_name,
                    'quantity': int(quantity),
                    'revenue': float(revenue)
                })
            
            # Топ-10 магазинов, продающих этот товар
            top_stores = db.session.query(
                Store.id,
                Store.name,
                City.name.label('city'),
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue')
            ).join(
                Sale, Store.id == Sale.store_id
            ).join(
                City, Store.city_id == City.id
            ).filter(
                Sale.product_id == product_id,
                Sale.date.between(start_date, end_date)
            ).group_by(
                Store.id,
                Store.name,
                City.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).limit(10).all()
            
            top_stores_data = []
            product_total_revenue = sales_stats.total_revenue or 0
            
            for store_id, name, city, quantity, revenue in top_stores:
                percentage = (revenue / product_total_revenue * 100) if product_total_revenue > 0 else 0
                
                top_stores_data.append({
                    'id': store_id,
                    'name': name,
                    'city': city,
                    'quantity': int(quantity),
                    'revenue': float(revenue),
                    'percentage': round(percentage, 2)
                })
            
            # Собираем данные для графиков
            time_series_data = []
            for item in monthly_data:
                time_series_data.append({
                    'x': f"{item['year']}-{item['month']:02d}",
                    'y': item['revenue']
                })
            
            # Формируем ответ
            result = {
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'category': product.category
                },
                'sales_stats': {
                    'total_quantity': int(sales_stats.total_quantity) if sales_stats.total_quantity else 0,
                    'total_revenue': float(sales_stats.total_revenue) if sales_stats.total_revenue else 0,
                    'avg_price': float(sales_stats.avg_price) if sales_stats.avg_price else 0,
                    'transactions_count': int(sales_stats.transactions_count) if sales_stats.transactions_count else 0,
                    'stores_count': int(sales_stats.stores_count) if sales_stats.stores_count else 0
                },
                'monthly_data': monthly_data,
                'top_stores': top_stores_data,
                'charts': {
                    'time_series': time_series_data
                }
            }
            
            # Для сравнения с предыдущим периодом
            prev_sales = db.session.query(
                func.sum(Sale.quantity * Sale.price).label('total_revenue')
            ).filter(
                Sale.product_id == product_id,
                Sale.date.between(prev_start_date, prev_end_date)
            ).scalar() or 0
            
            current_revenue = sales_stats.total_revenue or 0
            growth = calculate_growth_rate(current_revenue, prev_sales)
            
            result['sales_stats']['growth'] = round(growth, 2)
            
            return result