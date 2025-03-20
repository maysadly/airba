from flask_restx import Resource, Namespace, fields
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required
from flask import request
from ... import db
from ...models.catalog import CategoryGroup, Category, Product, Sale, City, Store
from .analytics import date_range_parser, top_store_model, geo_data_model
from ...utils.analytics_utils import get_date_range, calculate_growth_rate
import calendar

def register_store_routes(ns: Namespace):
    """Регистрирует маршруты для аналитики по магазинам"""
    
    # Корректная регистрация модели
    top_stores_model = ns.model('TopStoresList', {
        'top_stores': fields.List(fields.Nested(top_store_model))
    })
    
    # Определение детальных моделей для магазина
    store_detail_model = ns.model('StoreDetail', {
        'id': fields.Integer(description='ID магазина'),
        'name': fields.String(description='Название магазина'),
        'address': fields.String(description='Адрес магазина'),
        'city': fields.String(description='Город')
    })
    
    store_sales_stats_model = ns.model('StoreSalesStats', {
        'total_quantity': fields.Integer(description='Общее количество проданных единиц'),
        'total_revenue': fields.Float(description='Общая выручка'),
        'avg_price': fields.Float(description='Средняя цена'),
        'transactions_count': fields.Integer(description='Количество транзакций'),
        'products_count': fields.Integer(description='Количество товаров'),
        'growth': fields.Float(description='Рост по сравнению с предыдущим периодом')
    })
    
    store_monthly_data_model = ns.model('StoreMonthlyData', {
        'year': fields.Integer(description='Год'),
        'month': fields.Integer(description='Месяц'),
        'month_name': fields.String(description='Название месяца'),
        'quantity': fields.Integer(description='Количество проданных единиц'),
        'revenue': fields.Float(description='Выручка'),
        'orders': fields.Integer(description='Количество заказов'),
        'avg_order': fields.Float(description='Средний чек')
    })
    
    store_top_category_model = ns.model('StoreTopCategory', {
        'id': fields.Integer(description='ID категории'),
        'name': fields.String(description='Название категории'),
        'quantity': fields.Integer(description='Количество проданных единиц'),
        'revenue': fields.Float(description='Выручка'),
        'percentage': fields.Float(description='Процент от общей выручки')
    })
    
    store_top_product_model = ns.model('StoreTopProduct', {
        'id': fields.Integer(description='ID товара'),
        'name': fields.String(description='Название товара'),
        'category': fields.String(description='Категория'),
        'quantity': fields.Integer(description='Количество проданных единиц'),
        'revenue': fields.Float(description='Выручка'),
        'percentage': fields.Float(description='Процент от общей выручки'),
        'avg_price': fields.Float(description='Средняя цена')
    })
    
    store_charts_model = ns.model('StoreCharts', {
        'time_series': fields.List(fields.Nested(ns.model('StoreTimeSeries', {
            'x': fields.String(description='Период (месяц)'),
            'y': fields.Float(description='Значение')
        }))),
        'category_distribution': fields.List(fields.Nested(ns.model('StoreCategoryDistribution', {
            'label': fields.String(description='Метка'),
            'value': fields.Float(description='Значение')
        })))
    })
    
    # Полная модель ответа для детальной аналитики магазина
    store_analytics_model = ns.model('StoreAnalytics', {
        'store': fields.Nested(store_detail_model),
        'sales_stats': fields.Nested(store_sales_stats_model),
        'monthly_data': fields.List(fields.Nested(store_monthly_data_model)),
        'top_categories': fields.List(fields.Nested(store_top_category_model)),
        'top_products': fields.List(fields.Nested(store_top_product_model)),
        'charts': fields.Nested(store_charts_model)
    })
    
    # Модель для географических данных
    geo_analytics_model = ns.model('GeoAnalytics', {
        'geo_data': fields.List(fields.Nested(geo_data_model))
    })
    
    @ns.route('/stores/top')
    class TopStores(Resource):
        @ns.doc('top_stores', 
                description='Получить топ магазинов по продажам',
                tags=['Магазины'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', top_stores_model)
        @jwt_required()
        def get(self):
            """Получить топ магазинов по продажам"""
            args = date_range_parser.parse_args()
            period = args.get('period', 'month')
            limit = int(request.args.get('limit', 10))
            category_id = args.get('category_id')
            product_id = args.get('product_id')
            
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
                Store.id,
                Store.name,
                City.name.label('city'),
                func.sum(Sale.quantity * Sale.price).label('revenue'),
                func.count(func.distinct(Sale.id)).label('orders')
            ).join(
                Sale, Store.id == Sale.store_id
            ).join(
                City, Store.city_id == City.id
            ).filter(
                Sale.date.between(start_date, end_date)
            )
            
            # Применяем фильтры
            if category_id:
                query = query.join(Product, Sale.product_id == Product.id).filter(
                    Product.category_id == category_id
                )
                
            if product_id:
                query = query.filter(Sale.product_id == product_id)
            
            # Группируем и сортируем
            query = query.group_by(
                Store.id,
                Store.name,
                City.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).limit(limit)
            
            stores = query.all()
            
            # Подсчитываем общую выручку за период для вычисления процентов
            total_revenue_query = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
                Sale.date.between(start_date, end_date)
            )
            
            if category_id:
                total_revenue_query = total_revenue_query.join(Product).filter(
                    Product.category_id == category_id
                )
                
            if product_id:
                total_revenue_query = total_revenue_query.filter(Sale.product_id == product_id)
            
            total_revenue = total_revenue_query.scalar() or 0
            
            # Форматируем результаты
            result = []
            
            for store_id, name, city, revenue, orders in stores:
                # Получаем данные за предыдущий период для вычисления роста
                prev_revenue_query = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
                    Sale.store_id == store_id,
                    Sale.date.between(prev_start_date, prev_end_date)
                )
                
                if category_id:
                    prev_revenue_query = prev_revenue_query.join(Product).filter(
                        Product.category_id == category_id
                    )
                    
                if product_id:
                    prev_revenue_query = prev_revenue_query.filter(Sale.product_id == product_id)
                
                prev_revenue = prev_revenue_query.scalar() or 0
                
                growth = calculate_growth_rate(revenue, prev_revenue)
                percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
                avg_order = revenue / orders if orders > 0 else 0
                
                result.append({
                    'id': store_id,
                    'name': name,
                    'city': city,
                    'revenue': float(revenue),
                    'percentage': round(percentage, 2),
                    'growth': round(growth, 2),
                    'avg_order': float(avg_order),
                    'orders': int(orders)
                })
            
            return {'top_stores': result}
    
    @ns.route('/stores/<int:store_id>/analytics')
    @ns.param('store_id', 'ID магазина')
    class StoreAnalytics(Resource):
        @ns.doc('store_analytics', 
                description='Получить подробную аналитику по конкретному магазину',
                tags=['Магазины'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', store_analytics_model)
        @jwt_required()
        def get(self, store_id):
            """Получить подробную аналитику по конкретному магазину"""
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
            
            # Получаем информацию о магазине
            store = db.session.query(
                Store.id,
                Store.name,
                Store.address,
                City.name.label('city')
            ).join(
                City, Store.city_id == City.id
            ).filter(
                Store.id == store_id
            ).first()
            
            if not store:
                return {'error': 'Магазин не найден'}, 404
            
            # Собираем статистику продаж
            sales_stats = db.session.query(
                func.sum(Sale.quantity).label('total_quantity'),
                func.sum(Sale.quantity * Sale.price).label('total_revenue'),
                func.avg(Sale.price).label('avg_price'),
                func.count(func.distinct(Sale.id)).label('transactions_count'),
                func.count(func.distinct(Sale.product_id)).label('products_count')
            ).filter(
                Sale.store_id == store_id,
                Sale.date.between(start_date, end_date)
            ).first()
            
            # Получаем помесячную динамику продаж
            monthly_sales = db.session.query(
                extract('year', Sale.date).label('year'),
                extract('month', Sale.date).label('month'),
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue'),
                func.count(func.distinct(Sale.id)).label('orders')
            ).filter(
                Sale.store_id == store_id,
                Sale.date.between(start_date, end_date)
            ).group_by(
                extract('year', Sale.date),
                extract('month', Sale.date)
            ).all()
            
            monthly_data = []
            for year, month, quantity, revenue, orders in monthly_sales:
                month_name = calendar.month_name[int(month)]
                monthly_data.append({
                    'year': int(year),
                    'month': int(month),
                    'month_name': month_name,
                    'quantity': int(quantity),
                    'revenue': float(revenue),
                    'orders': int(orders),
                    'avg_order': float(revenue) / int(orders) if orders > 0 else 0
                })
            
            # Топ-10 категорий в этом магазине
            top_categories = db.session.query(
                Category.id,
                Category.name,
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue')
            ).join(
                Product, Category.id == Product.category_id
            ).join(
                Sale, Product.id == Sale.product_id
            ).filter(
                Sale.store_id == store_id,
                Sale.date.between(start_date, end_date)
            ).group_by(
                Category.id,
                Category.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).limit(10).all()
            
            top_categories_data = []
            store_total_revenue = sales_stats.total_revenue or 0
            
            for category_id, name, quantity, revenue in top_categories:
                percentage = (revenue / store_total_revenue * 100) if store_total_revenue > 0 else 0
                
                top_categories_data.append({
                    'id': category_id,
                    'name': name,
                    'quantity': int(quantity),
                    'revenue': float(revenue),
                    'percentage': round(percentage, 2)
                })
            
            # Топ-10 товаров в этом магазине
            top_products = db.session.query(
                Product.id,
                Product.name,
                Category.name.label('category'),
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue'),
                func.avg(Sale.price).label('avg_price')
            ).join(
                Sale, Product.id == Sale.product_id
            ).join(
                Category, Product.category_id == Category.id
            ).filter(
                Sale.store_id == store_id,
                Sale.date.between(start_date, end_date)
            ).group_by(
                Product.id,
                Product.name,
                Category.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).limit(10).all()
            
            top_products_data = []
            
            for product_id, name, category, quantity, revenue, avg_price in top_products:
                percentage = (revenue / store_total_revenue * 100) if store_total_revenue > 0 else 0
                
                top_products_data.append({
                    'id': product_id,
                    'name': name,
                    'category': category,
                    'quantity': int(quantity),
                    'revenue': float(revenue),
                    'percentage': round(percentage, 2),
                    'avg_price': float(avg_price)
                })
            
            # Собираем данные для графиков
            time_series_data = []
            for item in monthly_data:
                time_series_data.append({
                    'x': f"{item['year']}-{item['month']:02d}",
                    'y': item['revenue']
                })
            
            # Данные для круговых диаграмм (распределение по категориям)
            category_distribution = [{'label': item['name'], 'value': item['revenue']} 
                                    for item in top_categories_data]
            
            # Формируем ответ
            result = {
                'store': {
                    'id': store.id,
                    'name': store.name,
                    'address': store.address,
                    'city': store.city
                },
                'sales_stats': {
                    'total_quantity': int(sales_stats.total_quantity) if sales_stats.total_quantity else 0,
                    'total_revenue': float(sales_stats.total_revenue) if sales_stats.total_revenue else 0,
                    'avg_price': float(sales_stats.avg_price) if sales_stats.avg_price else 0,
                    'transactions_count': int(sales_stats.transactions_count) if sales_stats.transactions_count else 0,
                    'products_count': int(sales_stats.products_count) if sales_stats.products_count else 0
                },
                'monthly_data': monthly_data,
                'top_categories': top_categories_data,
                'top_products': top_products_data,
                'charts': {
                    'time_series': time_series_data,
                    'category_distribution': category_distribution
                }
            }
            
            # Для сравнения с предыдущим периодом
            prev_sales = db.session.query(
                func.sum(Sale.quantity * Sale.price).label('total_revenue')
            ).filter(
                Sale.store_id == store_id,
                Sale.date.between(prev_start_date, prev_end_date)
            ).scalar() or 0
            
            current_revenue = sales_stats.total_revenue or 0
            growth = calculate_growth_rate(current_revenue, prev_sales)
            
            result['sales_stats']['growth'] = round(growth, 2)
            
            return result
    
    @ns.route('/stores/geo')
    class StoresGeoAnalytics(Resource):
        @ns.doc('stores_geo_analytics', 
                description='Получить географические данные о магазинах и продажах',
                tags=['Магазины'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', geo_analytics_model)
        @jwt_required()
        def get(self):
            """Получить географические данные о магазинах и продажах"""
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
            
            # Получаем данные по городам
            cities_data = db.session.query(
                City.id,
                City.name,
                func.sum(Sale.quantity * Sale.price).label('revenue'),
                func.count(func.distinct(Sale.id)).label('orders'),
                func.count(func.distinct(Store.id)).label('stores_count')
            ).join(
                Store, City.id == Store.city_id
            ).join(
                Sale, Store.id == Sale.store_id
            ).filter(
                Sale.date.between(start_date, end_date)
            ).group_by(
                City.id,
                City.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).all()
            
            # Форматируем ответ
            result = []
            
            for city_id, name, revenue, orders, stores_count in cities_data:
                result.append({
                    'id': city_id,
                    'name': name,
                    'revenue': float(revenue),
                    'orders': int(orders),
                    'stores_count': int(stores_count),
                    'avg_store_revenue': float(revenue) / int(stores_count) if stores_count > 0 else 0
                })
            
            return {'geo_data': result}
