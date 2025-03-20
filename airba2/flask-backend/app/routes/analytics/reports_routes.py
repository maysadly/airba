from flask_restx import Resource, Namespace, fields
from sqlalchemy import func, extract, desc
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required
from flask import request, send_file
from io import BytesIO
import pandas as pd
import json
import calendar

from ... import db
from ...models.catalog import CategoryGroup, Category, Product, Sale, City, Store
from .analytics import date_range_parser
from ...utils.analytics_utils import get_date_range

def register_report_routes(ns: Namespace):
    """Регистрирует маршруты для получения отчетов"""
    
    # Модель для запроса отчета - регистрируем правильно
    report_request_model = ns.model('ReportRequest', {
        'format': fields.String(required=True, enum=['csv', 'excel', 'json', 'pdf'], description='Формат отчета'),
        'report_type': fields.String(required=True, description='Тип отчета: sales, categories, products, stores'),
        'include_charts': fields.Boolean(default=False, description='Включать ли графики в отчет (для PDF)'),
        'group_by': fields.String(enum=['day', 'week', 'month', 'year'], description='Группировка данных'),
        'columns': fields.List(fields.String, description='Список столбцов для включения в отчет')
    })
    
    # Модель для ответа с шаблонами отчетов
    report_template_model = ns.model('ReportTemplate', {
        'id': fields.String(description='Идентификатор шаблона'),
        'name': fields.String(description='Название шаблона'),
        'description': fields.String(description='Описание шаблона'),
        'report_type': fields.String(description='Тип отчета'),
        'default_format': fields.String(description='Формат по умолчанию'),
        'group_by': fields.String(description='Группировка данных', required=False),
        'columns': fields.List(fields.String, description='Столбцы отчета')
    })
    
    templates_response_model = ns.model('ReportTemplatesResponse', {
        'templates': fields.List(fields.Nested(report_template_model))
    })
    
    # Модель для ответа в формате JSON
    json_report_model = ns.model('JsonReport', {
        'report_type': fields.String(description='Тип отчета'),
        'start_date': fields.String(description='Начальная дата'),
        'end_date': fields.String(description='Конечная дата'),
        'group_by': fields.String(description='Группировка данных'),
        'data': fields.List(fields.Raw(description='Данные отчета'))
    })
    
    @ns.route('/reports')
    class GenerateReport(Resource):
        @ns.doc('generate_report', 
                description='Сгенерировать аналитический отчет',
                tags=['Отчеты'])
        @ns.expect(date_range_parser, report_request_model)
        @ns.response(200, 'Успешный запрос', json_report_model)
        @jwt_required()
        def post(self):
            """Сгенерировать аналитический отчет в выбранном формате"""
            args = date_range_parser.parse_args()
            period = args.get('period', 'month')
            
            # Получаем параметры отчета из запроса
            report_params = request.json
            report_format = report_params.get('format', 'csv')
            report_type = report_params.get('report_type', 'sales')
            group_by = report_params.get('group_by', 'day')
            
            # Получаем диапазон дат на основе периода или пользовательских дат
            if args.get('start_date') and args.get('end_date'):
                try:
                    start_date = datetime.strptime(args['start_date'], '%Y-%m-%d')
                    end_date = datetime.strptime(args['end_date'], '%Y-%m-%d')
                except ValueError:
                    start_date, end_date = get_date_range(period)
            else:
                start_date, end_date = get_date_range(period)
                
            # Собираем данные в зависимости от типа отчета
            if report_type == 'sales':
                df = generate_sales_report(start_date, end_date, group_by)
            elif report_type == 'categories':
                df = generate_categories_report(start_date, end_date)
            elif report_type == 'products':
                df = generate_products_report(start_date, end_date)
            elif report_type == 'stores':
                df = generate_stores_report(start_date, end_date)
            else:
                return {'error': 'Неизвестный тип отчета'}, 400
            
            # Применяем фильтры из запроса
            if 'columns' in report_params and report_params['columns']:
                columns = [col for col in report_params['columns'] if col in df.columns]
                if columns:
                    df = df[columns]
            
            # Отправляем отчет в выбранном формате
            if report_format == 'csv':
                output = BytesIO()
                df.to_csv(output, index=False, encoding='utf-8')
                output.seek(0)
                return send_file(
                    output,
                    mimetype='text/csv',
                    as_attachment=True,
                    attachment_filename=f'{report_type}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv'
                )
            
            elif report_format == 'excel':
                output = BytesIO()
                df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                return send_file(
                    output, 
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    attachment_filename=f'{report_type}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.xlsx'
                )
            
            elif report_format == 'json':
                # Преобразуем DataFrame в список словарей
                records = df.to_dict('records')
                return {
                    'report_type': report_type,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'group_by': group_by,
                    'data': records
                }
            
            elif report_format == 'pdf':
                # Для PDF потребуется дополнительная библиотека, например, reportlab или weasyprint
                # Здесь демонстрируем только заготовку функционала
                return {
                    'error': 'Формат PDF временно недоступен',
                    'status': 'not_implemented'
                }, 501
            
            return {'error': 'Неизвестный формат отчета'}, 400
    
    @ns.route('/reports/templates')
    class ReportTemplates(Resource):
        @ns.doc('report_templates', 
                description='Получить доступные шаблоны отчетов',
                tags=['Отчеты'])
        @ns.response(200, 'Успешный запрос', templates_response_model)
        @jwt_required()
        def get(self):
            """Получить список доступных шаблонов отчетов"""
            templates = [
                {
                    'id': 'sales_summary',
                    'name': 'Сводка по продажам',
                    'description': 'Общая сводка продаж по дням, неделям или месяцам',
                    'report_type': 'sales',
                    'default_format': 'excel',
                    'group_by': 'day',
                    'columns': ['date', 'total_revenue', 'total_quantity', 'avg_price']
                },
                {
                    'id': 'top_products',
                    'name': 'Топ продуктов',
                    'description': 'Отчет по самым продаваемым продуктам',
                    'report_type': 'products',
                    'default_format': 'excel',
                    'columns': ['id', 'name', 'category', 'quantity', 'revenue', 'avg_price']
                },
                {
                    'id': 'category_performance',
                    'name': 'Эффективность категорий',
                    'description': 'Анализ продаж по категориям товаров',
                    'report_type': 'categories',
                    'default_format': 'excel',
                    'columns': ['id', 'name', 'revenue', 'percentage', 'growth', 'products_count']
                },
                {
                    'id': 'store_performance',
                    'name': 'Эффективность магазинов',
                    'description': 'Анализ продаж по магазинам',
                    'report_type': 'stores',
                    'default_format': 'excel',
                    'columns': ['id', 'name', 'city', 'revenue', 'orders', 'avg_order']
                }
            ]
            
            return {'templates': templates}

# Вспомогательные функции для генерации отчетов

def generate_sales_report(start_date, end_date, group_by='day'):
    """Генерирует отчет по продажам с группировкой по дням, неделям или месяцам"""
    
    if group_by == 'day':
        # Группировка по дням
        sales = db.session.query(
            Sale.date,
            func.sum(Sale.quantity * Sale.price).label('total_revenue'),
            func.sum(Sale.quantity).label('total_quantity'),
            func.avg(Sale.price).label('avg_price'),
            func.count(func.distinct(Sale.id)).label('orders_count')
        ).filter(
            Sale.date.between(start_date, end_date)
        ).group_by(
            Sale.date
        ).all()
        
        data = []
        for date, revenue, quantity, avg_price, orders in sales:
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'total_revenue': float(revenue),
                'total_quantity': int(quantity),
                'avg_price': float(avg_price),
                'orders_count': int(orders),
                'avg_order_value': float(revenue) / int(orders) if orders else 0
            })
        
    elif group_by == 'week':
        # Группировка по неделям
        sales = db.session.query(
            extract('year', Sale.date).label('year'),
            extract('week', Sale.date).label('week'),
            func.min(Sale.date).label('start_date'),
            func.max(Sale.date).label('end_date'),
            func.sum(Sale.quantity * Sale.price).label('total_revenue'),
            func.sum(Sale.quantity).label('total_quantity'),
            func.avg(Sale.price).label('avg_price'),
            func.count(func.distinct(Sale.id)).label('orders_count')
        ).filter(
            Sale.date.between(start_date, end_date)
        ).group_by(
            extract('year', Sale.date),
            extract('week', Sale.date)
        ).all()
        
        data = []
        for year, week, start_date, end_date, revenue, quantity, avg_price, orders in sales:
            data.append({
                'year': int(year),
                'week': int(week),
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_revenue': float(revenue),
                'total_quantity': int(quantity),
                'avg_price': float(avg_price),
                'orders_count': int(orders),
                'avg_order_value': float(revenue) / int(orders) if orders else 0
            })
        
    elif group_by == 'month':
        # Группировка по месяцам
        sales = db.session.query(
            extract('year', Sale.date).label('year'),
            extract('month', Sale.date).label('month'),
            func.sum(Sale.quantity * Sale.price).label('total_revenue'),
            func.sum(Sale.quantity).label('total_quantity'),
            func.avg(Sale.price).label('avg_price'),
            func.count(func.distinct(Sale.id)).label('orders_count')
        ).filter(
            Sale.date.between(start_date, end_date)
        ).group_by(
            extract('year', Sale.date),
            extract('month', Sale.date)
        ).all()
        
        data = []
        for year, month, revenue, quantity, avg_price, orders in sales:
            month_name = calendar.month_name[int(month)]
            data.append({
                'year': int(year),
                'month': int(month),
                'month_name': month_name,
                'total_revenue': float(revenue),
                'total_quantity': int(quantity),
                'avg_price': float(avg_price),
                'orders_count': int(orders),
                'avg_order_value': float(revenue) / int(orders) if orders else 0
            })
            
    else:  # group_by == 'year'
        # Группировка по годам
        sales = db.session.query(
            extract('year', Sale.date).label('year'),
            func.sum(Sale.quantity * Sale.price).label('total_revenue'),
            func.sum(Sale.quantity).label('total_quantity'),
            func.avg(Sale.price).label('avg_price'),
            func.count(func.distinct(Sale.id)).label('orders_count')
        ).filter(
            Sale.date.between(start_date, end_date)
        ).group_by(
            extract('year', Sale.date)
        ).all()
        
        data = []
        for year, revenue, quantity, avg_price, orders in sales:
            data.append({
                'year': int(year),
                'total_revenue': float(revenue),
                'total_quantity': int(quantity),
                'avg_price': float(avg_price),
                'orders_count': int(orders),
                'avg_order_value': float(revenue) / int(orders) if orders else 0
            })
    
    # Преобразуем в DataFrame
    df = pd.DataFrame(data)
    return df

def generate_categories_report(start_date, end_date):
    """Генерирует отчет по категориям"""
    
    categories = db.session.query(
        Category.id,
        Category.name,
        CategoryGroup.name.label('group_name'),
        func.sum(Sale.quantity * Sale.price).label('revenue'),
        func.sum(Sale.quantity).label('quantity'),
        func.count(func.distinct(Product.id)).label('products_count')
    ).join(
        Product, Category.id == Product.category_id
    ).join(
        CategoryGroup, Category.group_id == CategoryGroup.id
    ).join(
        Sale, Product.id == Sale.product_id
    ).filter(
        Sale.date.between(start_date, end_date)
    ).group_by(
        Category.id,
        Category.name,
        CategoryGroup.name
    ).order_by(
        func.sum(Sale.quantity * Sale.price).desc()
    ).all()
    
    data = []
    total_revenue = sum(cat.revenue for cat in categories) if categories else 0
    
    for cat in categories:
        percentage = (cat.revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # Получаем данные за предыдущий период для сравнения
        prev_end_date = start_date - timedelta(days=1)
        period_days = (end_date - start_date).days
        prev_start_date = prev_end_date - timedelta(days=period_days)
        
        prev_revenue = db.session.query(func.sum(Sale.quantity * Sale.price)).join(
            Product, Sale.product_id == Product.id
        ).filter(
            Product.category_id == cat.id,
            Sale.date.between(prev_start_date, prev_end_date)
        ).scalar() or 0
        
        growth = ((cat.revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        data.append({
            'id': cat.id,
            'name': cat.name,
            'group_name': cat.group_name,
            'revenue': float(cat.revenue),
            'quantity': int(cat.quantity),
            'percentage': round(percentage, 2),
            'growth': round(growth, 2),
            'products_count': int(cat.products_count),
            'avg_price': float(cat.revenue) / float(cat.quantity) if cat.quantity > 0 else 0
        })
    
    df = pd.DataFrame(data)
    return df

def generate_products_report(start_date, end_date):
    """Генерирует отчет по товарам"""
    
    products = db.session.query(
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
        Sale.date.between(start_date, end_date)
    ).group_by(
        Product.id,
        Product.name,
        Category.name
    ).order_by(
        func.sum(Sale.quantity * Sale.price).desc()
    ).all()
    
    data = []
    total_revenue = sum(prod.revenue for prod in products) if products else 0
    
    for prod in products:
        percentage = (prod.revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # Получаем данные за предыдущий период для сравнения
        prev_end_date = start_date - timedelta(days=1)
        period_days = (end_date - start_date).days
        prev_start_date = prev_end_date - timedelta(days=period_days)
        
        prev_revenue = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
            Sale.product_id == prod.id,
            Sale.date.between(prev_start_date, prev_end_date)
        ).scalar() or 0
        
        growth = ((prod.revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        data.append({
            'id': prod.id,
            'name': prod.name,
            'category': prod.category,
            'quantity': int(prod.quantity),
            'revenue': float(prod.revenue),
            'percentage': round(percentage, 2),
            'growth': round(growth, 2),
            'avg_price': float(prod.avg_price)
        })
    
    df = pd.DataFrame(data)
    return df

def generate_stores_report(start_date, end_date):
    """Генерирует отчет по магазинам"""
    
    stores = db.session.query(
        Store.id,
        Store.name,
        City.name.label('city'),
        func.sum(Sale.quantity * Sale.price).label('revenue'),
        func.sum(Sale.quantity).label('quantity'),
        func.count(func.distinct(Sale.id)).label('orders')
    ).join(
        Sale, Store.id == Sale.store_id
    ).join(
        City, Store.city_id == City.id
    ).filter(
        Sale.date.between(start_date, end_date)
    ).group_by(
        Store.id,
        Store.name,
        City.name
    ).order_by(
        func.sum(Sale.quantity * Sale.price).desc()
    ).all()
    
    data = []
    total_revenue = sum(store.revenue for store in stores) if stores else 0
    
    for store in stores:
        percentage = (store.revenue / total_revenue * 100) if total_revenue > 0 else 0
        avg_order = (store.revenue / store.orders) if store.orders > 0 else 0
        
        # Получаем данные за предыдущий период для сравнения
        prev_end_date = start_date - timedelta(days=1)
        period_days = (end_date - start_date).days
        prev_start_date = prev_end_date - timedelta(days=period_days)
        
        prev_revenue = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
            Sale.store_id == store.id,
            Sale.date.between(prev_start_date, prev_end_date)
        ).scalar() or 0
        
        growth = ((store.revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        data.append({
            'id': store.id,
            'name': store.name,
            'city': store.city,
            'revenue': float(store.revenue),
            'quantity': int(store.quantity),
            'orders': int(store.orders),
            'percentage': round(percentage, 2),
            'growth': round(growth, 2),
            'avg_order': float(avg_order)
        })
    
    df = pd.DataFrame(data)
    return df
