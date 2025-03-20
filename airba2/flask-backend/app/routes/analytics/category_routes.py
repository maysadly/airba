from flask_restx import Resource, Namespace, fields
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required
from flask import request
from ... import db
from ...models.catalog import CategoryGroup, Category, Product, Sale, City, Store
from .analytics import date_range_parser, top_category_model
from ...utils.analytics_utils import get_date_range, calculate_growth_rate
import calendar

def register_category_routes(ns: Namespace):
    """Регистрирует маршруты для аналитики по категориям"""
    
    # Правильная регистрация модели как самостоятельной модели, а не словаря
    top_categories_model = ns.model('TopCategoriesList', {
        'top_categories': fields.List(fields.Nested(top_category_model))
    })
    
    # Определение детальных моделей для категории
    category_detail_model = ns.model('CategoryDetail', {
        'id': fields.Integer(description='ID категории'),
        'name': fields.String(description='Название категории'),
        'description': fields.String(description='Описание категории'),
        'group_name': fields.String(description='Название группы категорий')
    })
    
    category_sales_stats_model = ns.model('CategorySalesStats', {
        'total_quantity': fields.Integer(description='Общее количество проданных единиц'),
        'total_revenue': fields.Float(description='Общая выручка'),
        'avg_price': fields.Float(description='Средняя цена'),
        'transactions_count': fields.Integer(description='Количество транзакций'),
        'stores_count': fields.Integer(description='Количество магазинов'),
        'products_count': fields.Integer(description='Количество товаров'),
        'growth': fields.Float(description='Рост по сравнению с предыдущим периодом')
    })
    
    category_monthly_data_model = ns.model('CategoryMonthlyData', {
        'year': fields.Integer(description='Год'),
        'month': fields.Integer(description='Месяц'),
        'month_name': fields.String(description='Название месяца'),
        'quantity': fields.Integer(description='Количество проданных единиц'),
        'revenue': fields.Float(description='Выручка')
    })
    
    category_top_product_model = ns.model('CategoryTopProduct', {
        'id': fields.Integer(description='ID товара'),
        'name': fields.String(description='Название товара'),
        'quantity': fields.Integer(description='Количество проданных единиц'),
        'revenue': fields.Float(description='Выручка'),
        'percentage': fields.Float(description='Процент от общей выручки'),
        'avg_price': fields.Float(description='Средняя цена')
    })
    
    category_charts_model = ns.model('CategoryCharts', {
        'time_series': fields.List(fields.Nested(ns.model('CategoryTimeSeries', {
            'x': fields.String(description='Период (месяц)'),
            'y': fields.Float(description='Значение')
        })))
    })
    
    # Полная модель ответа для детальной аналитики категории
    category_analytics_model = ns.model('CategoryAnalytics', {
        'category': fields.Nested(category_detail_model),
        'sales_stats': fields.Nested(category_sales_stats_model),
        'monthly_data': fields.List(fields.Nested(category_monthly_data_model)),
        'top_products': fields.List(fields.Nested(category_top_product_model)),
        'charts': fields.Nested(category_charts_model)
    })
    
    @ns.route('/categories/top')
    class TopCategories(Resource):
        @ns.doc('top_categories', 
                description='Получить топ категорий по продажам',
                tags=['Категории'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', top_categories_model)
        @jwt_required()
        def get(self):
            """Получить топ категорий по продажам"""
            args = date_range_parser.parse_args()
            period = args.get('period', 'month')
            limit = int(request.args.get('limit', 10))
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
                Category.id,
                Category.name,
                CategoryGroup.name.label('group_name'),
                func.sum(Sale.quantity * Sale.price).label('revenue'),
                func.count(func.distinct(Product.id)).label('products_count')
            ).join(
                Product, Category.id == Product.category_id
            ).join(
                CategoryGroup, Category.group_id == CategoryGroup.id
            ).join(
                Sale, Product.id == Sale.product_id
            ).filter(
                Sale.date.between(start_date, end_date)
            )
            
            # Применяем фильтры
            if store_id:
                query = query.filter(Sale.store_id == store_id)
            
            # Группируем и сортируем
            query = query.group_by(
                Category.id,
                Category.name,
                CategoryGroup.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).limit(limit)
            
            categories = query.all()
            
            # Подсчитываем общую выручку за период для вычисления процентов
            total_revenue_query = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
                Sale.date.between(start_date, end_date)
            )
            
            if store_id:
                total_revenue_query = total_revenue_query.filter(Sale.store_id == store_id)
            
            total_revenue = total_revenue_query.scalar() or 0
            
            # Форматируем результаты
            result = []
            
            for cat_id, name, group_name, revenue, products_count in categories:
                # Получаем данные за предыдущий период для вычисления роста
                prev_revenue_query = db.session.query(func.sum(Sale.quantity * Sale.price)).join(
                    Product, Sale.product_id == Product.id
                ).filter(
                    Product.category_id == cat_id,
                    Sale.date.between(prev_start_date, prev_end_date)
                )
                
                if store_id:
                    prev_revenue_query = prev_revenue_query.filter(Sale.store_id == store_id)
                
                prev_revenue = prev_revenue_query.scalar() or 0
                
                growth = calculate_growth_rate(revenue, prev_revenue)
                percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
                
                result.append({
                    'id': cat_id,
                    'name': name,
                    'group_name': group_name,
                    'revenue': float(revenue),
                    'percentage': round(percentage, 2),
                    'growth': round(growth, 2),
                    'products_count': int(products_count)
                })
            
            return {'top_categories': result}
    
    @ns.route('/categories/<int:category_id>/analytics')
    @ns.param('category_id', 'ID категории')
    class CategoryAnalytics(Resource):
        @ns.doc('category_analytics', 
                description='Получить подробную аналитику по конкретной категории',
                tags=['Категории'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', category_analytics_model)
        @jwt_required()
        def get(self, category_id):
            """Получить подробную аналитику по конкретной категории"""
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
            
            # Получаем информацию о категории
            category = db.session.query(
                Category.id,
                Category.name,
                Category.description,
                CategoryGroup.name.label('group_name')
            ).join(
                CategoryGroup, Category.group_id == CategoryGroup.id
            ).filter(
                Category.id == category_id
            ).first()
            
            if not category:
                return {'error': 'Категория не найдена'}, 404
            
            # Собираем статистику продаж
            sales_stats = db.session.query(
                func.sum(Sale.quantity).label('total_quantity'),
                func.sum(Sale.quantity * Sale.price).label('total_revenue'),
                func.avg(Sale.price).label('avg_price'),
                func.count(func.distinct(Sale.id)).label('transactions_count'),
                func.count(func.distinct(Sale.store_id)).label('stores_count'),
                func.count(func.distinct(Product.id)).label('products_count')
            ).join(
                Product, Sale.product_id == Product.id
            ).filter(
                Product.category_id == category_id,
                Sale.date.between(start_date, end_date)
            ).first()
            
            # Получаем помесячную динамику продаж
            monthly_sales = db.session.query(
                extract('year', Sale.date).label('year'),
                extract('month', Sale.date).label('month'),
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue')
            ).join(
                Product, Sale.product_id == Product.id
            ).filter(
                Product.category_id == category_id,
                Sale.date.between(start_date, end_date)
            ).group_by(
                extract('year', Sale.date),
                extract('month', Sale.date)
            ).all()
            
            monthly_data = []
            for year, month, quantity, revenue in monthly_sales:
                month_name = calendar.month_name[int(month)]
                monthly_data.append({
                    'year': int(year),
                    'month': int(month),
                    'month_name': month_name,
                    'quantity': int(quantity),
                    'revenue': float(revenue)
                })
            
            # Топ-10 товаров в этой категории
            top_products = db.session.query(
                Product.id,
                Product.name,
                func.sum(Sale.quantity).label('quantity'),
                func.sum(Sale.quantity * Sale.price).label('revenue'),
                func.avg(Sale.price).label('avg_price')
            ).join(
                Sale, Product.id == Sale.product_id
            ).filter(
                Product.category_id == category_id,
                Sale.date.between(start_date, end_date)
            ).group_by(
                Product.id,
                Product.name
            ).order_by(
                func.sum(Sale.quantity * Sale.price).desc()
            ).limit(10).all()
            
            top_products_data = []
            category_total_revenue = sales_stats.total_revenue or 0
            
            for product_id, name, quantity, revenue, avg_price in top_products:
                percentage = (revenue / category_total_revenue * 100) if category_total_revenue > 0 else 0
                
                top_products_data.append({
                    'id': product_id,
                    'name': name,
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
            
            # Формируем ответ
            result = {
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'group_name': category.group_name
                },
                'sales_stats': {
                    'total_quantity': int(sales_stats.total_quantity) if sales_stats.total_quantity else 0,
                    'total_revenue': float(sales_stats.total_revenue) if sales_stats.total_revenue else 0,
                    'avg_price': float(sales_stats.avg_price) if sales_stats.avg_price else 0,
                    'transactions_count': int(sales_stats.transactions_count) if sales_stats.transactions_count else 0,
                    'stores_count': int(sales_stats.stores_count) if sales_stats.stores_count else 0,
                    'products_count': int(sales_stats.products_count) if sales_stats.products_count else 0
                },
                'monthly_data': monthly_data,
                'top_products': top_products_data,
                'charts': {
                    'time_series': time_series_data
                }
            }
            
            # Для сравнения с предыдущим периодом
            prev_sales = db.session.query(
                func.sum(Sale.quantity * Sale.price).label('total_revenue')
            ).join(
                Product, Sale.product_id == Product.id
            ).filter(
                Product.category_id == category_id,
                Sale.date.between(prev_start_date, prev_end_date)
            ).scalar() or 0
            
            current_revenue = sales_stats.total_revenue or 0
            growth = calculate_growth_rate(current_revenue, prev_sales)
            
            result['sales_stats']['growth'] = round(growth, 2)
            
            return result
