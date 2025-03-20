from flask_restx import Resource, Namespace
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required
from ... import db
from ...models.catalog import CategoryGroup, Category, Product, Sale, City, Store
from .analytics import date_range_parser, advanced_analytics_model
from ...utils.analytics_utils import (get_date_range, calculate_trend, calculate_growth_rate, 
                                    calculate_statistics, format_time_series_for_charts, get_top_entities)
from ...utils.analytics_visualizations import (generate_daily_data, generate_weekly_data, 
                                            generate_yearly_data, generate_hourly_heatmap_data,
                                            get_conversion_stats, get_customer_segments, get_geographic_data)

def register_dashboard_routes(ns: Namespace):
    """Регистрирует маршруты для панели управления"""
    
    @ns.route('/dashboard')
    class DashboardStats(Resource):
        @ns.doc('dashboard_analytics', 
                description='Получить комплексную аналитику для панели управления',
                tags=['Панель управления'])  # Используем тег здесь
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', advanced_analytics_model)
        @jwt_required()
        def get(self):
            """Получить полную аналитику для панели управления"""
            args = date_range_parser.parse_args()
            period = args.get('period', 'month')
            category_id = args.get('category_id')
            store_id = args.get('store_id')
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
            
            # Результирующий объект в обновленном формате
            result = {
                'data': {},      # Фактические данные
                'predict': {},   # Предсказания
                'charts': {},    # Данные для графиков
                'statistics': {} # Общая статистика
            }
            
            # Базовый запрос с примененными фильтрами
            base_query = db.session.query(Sale)
            
            if category_id:
                base_query = base_query.join(Product).filter(Product.category_id == category_id)
            
            if store_id:
                base_query = base_query.filter(Sale.store_id == store_id)
                
            if product_id:
                base_query = base_query.filter(Sale.product_id == product_id)
            
            # Получаем и структурируем фактические данные
            
            # 1. Суммарные метрики текущего периода
            sales_subquery = base_query.filter(Sale.date.between(start_date, end_date)).subquery()
            
            current_metrics = db.session.query(
                func.sum(sales_subquery.c.quantity * sales_subquery.c.price).label('total_revenue'),
                func.sum(sales_subquery.c.quantity).label('total_quantity'),
                func.avg(sales_subquery.c.price).label('avg_price'),
                func.count(func.distinct(sales_subquery.c.id)).label('orders_count')
            ).first()
            
            current_total_sales = float(current_metrics.total_revenue) if current_metrics.total_revenue else 0
            current_total_quantity = int(current_metrics.total_quantity) if current_metrics.total_quantity else 0
            avg_price = float(current_metrics.avg_price) if current_metrics.avg_price else 0
            sales_count = int(current_metrics.orders_count) if current_metrics.orders_count else 0
            
            # Вычисляем средний чек
            avg_order_value = current_total_sales / sales_count if sales_count > 0 else 0
            
            # Общие количества
            total_products = db.session.query(func.count(Product.id)).scalar() or 0
            total_categories = db.session.query(func.count(Category.id)).scalar() or 0
            total_stores = db.session.query(func.count(Store.id)).scalar() or 0
            
            # 2. Получаем суммарные метрики предыдущего периода для сравнения
            prev_sales_subquery = base_query.filter(Sale.date.between(prev_start_date, prev_end_date)).subquery()
            
            previous_metrics = db.session.query(
                func.sum(prev_sales_subquery.c.quantity * prev_sales_subquery.c.price).label('total_revenue')
            ).first()
            
            previous_total_sales = float(previous_metrics.total_revenue) if previous_metrics.total_revenue else 0
            
            # Вычисляем рост продаж
            sales_growth_rate = calculate_growth_rate(current_total_sales, previous_total_sales)
            
            # Добавляем суммарные метрики в результат
            result['data']['summary'] = {
                'total_revenue': current_total_sales,
                'total_quantity': current_total_quantity,
                'avg_order_value': avg_order_value,
                'avg_price': avg_price,
                'sales_trend': 0,  # Заполним позже
                'growth_rate': sales_growth_rate,
                'total_products': total_products,
                'total_categories': total_categories,
                'total_stores': total_stores
            }
            
            # 3. Получаем данные по разным временным масштабам
            
            # Получаем помесячные данные
            monthly_sales = db.session.query(
                extract('year', Sale.date).label('year'),
                extract('month', Sale.date).label('month'),
                func.sum(Sale.quantity * Sale.price).label('total'),
                func.sum(Sale.quantity).label('quantity'),
                func.count(func.distinct(Sale.id)).label('orders')
            ).filter(
                Sale.date.between(start_date, end_date)
            )
            
            # Применяем фильтры
            if category_id:
                monthly_sales = monthly_sales.join(Product).filter(Product.category_id == category_id)
            
            if store_id:
                monthly_sales = monthly_sales.filter(Sale.store_id == store_id)
                
            if product_id:
                monthly_sales = monthly_sales.filter(Sale.product_id == product_id)
            
            monthly_sales = monthly_sales.group_by(
                extract('year', Sale.date),
                extract('month', Sale.date)
            ).all()
            
            monthly_data = []
            for year, month, total, quantity, orders in monthly_sales:
                month_name = datetime(int(year), int(month), 1).strftime('%B')
                avg_order = total / orders if orders > 0 else 0
                
                monthly_data.append({
                    'year': int(year),
                    'month': int(month),
                    'month_name': month_name,
                    'total': float(total),
                    'quantity': int(quantity),
                    'orders': int(orders),
                    'avg_order': float(avg_order)
                })
            
            # Сортируем данные по дате
            monthly_data.sort(key=lambda x: (x['year'], x['month']))
            
            # Вычисляем тренд на основе месячных данных
            if monthly_data:
                monthly_values = [item['total'] for item in monthly_data]
                sales_trend = calculate_trend(monthly_values)
                # Обновляем информацию о тренде в суммарных метриках
                result['data']['summary']['sales_trend'] = sales_trend
            
            # Добавляем ежемесячные данные в результат
            result['data']['monthly'] = monthly_data
            
            # Генерируем или получаем ежедневные данные
            daily_data = generate_daily_data(monthly_data, start_date, end_date)
            result['data']['daily'] = daily_data
            
            # Генерируем еженедельные данные
            weekly_data = generate_weekly_data(daily_data)
            result['data']['weekly'] = weekly_data
            
            # Генерируем ежегодные данные
            yearly_data = generate_yearly_data(monthly_data)
            result['data']['yearly'] = yearly_data
            
            # 4. Получаем топ товаров, категорий и магазинов
            
            # Топ-10 продаваемых товаров
            top_products_data = get_top_entities('product', start_date, end_date, 10, prev_start_date, prev_end_date)
            result['data']['top_products'] = top_products_data
            
            # Топ-10 категорий
            top_categories_data = get_top_entities('category', start_date, end_date, 10, prev_start_date, prev_end_date)
            result['data']['top_categories'] = top_categories_data
            
            # Топ-10 магазинов
            top_stores_data = get_top_entities('store', start_date, end_date, 10, prev_start_date, prev_end_date)
            result['data']['top_stores'] = top_stores_data
            
            # 5. Генерируем данные для графиков
            
            # Данные для линейного графика (временные ряды продаж)
            time_series_data = format_time_series_for_charts(monthly_data, 
                                                          date_key=lambda x: f"{x['year']}-{x['month']:02d}", 
                                                          value_key='total')
            
            # Данные для круговых диаграмм (распределение по категориям)
            category_distribution = [{'label': item['name'], 'value': item['revenue']} 
                                  for item in top_categories_data]
            
            # Данные для тепловой карты (продажи по часам и дням недели)
            heatmap_data = generate_hourly_heatmap_data(start_date, end_date)
            
            # Данные по конверсии и воронке продаж
            funnel_data = get_conversion_stats(start_date, end_date)
            
            # Данные по сегментации клиентов
            customer_segments = get_customer_segments()
            
            # Географические данные
            geo_data = get_geographic_data()
            
            # Добавляем данные для графиков в результат
            result['charts'] = {
                'time_series': time_series_data,
                'category_distribution': category_distribution,
                'heatmap_data': heatmap_data,
                'funnel_data': funnel_data,
                'customer_segments': customer_segments,
                'geo_data': geo_data
            }
            
            # 6. Добавляем статистику
            if monthly_data:
                result['statistics'] = calculate_statistics([item['total'] for item in monthly_data])
            else:
                result['statistics'] = calculate_statistics([])
            
            return result
