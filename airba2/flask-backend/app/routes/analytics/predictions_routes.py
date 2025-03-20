from flask_restx import Resource, Namespace
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required
from ... import db
from ...models.catalog import Product, Sale
from .analytics import date_range_parser, prediction_model
from ...utils.analytics_utils import get_date_range, calculate_growth_rate, format_time_series_for_charts
from ...utils.simple_analytics import generate_simple_prediction, format_predictions_for_api
from ...utils.analytics_visualizations import generate_daily_data, generate_weekly_data, generate_yearly_data

def register_prediction_routes(ns: Namespace):
    """Регистрирует маршруты для прогнозов"""
    
    @ns.route('/predictions')
    class SalesPredictions(Resource):
        @ns.doc('sales_predictions', 
                description='Получить прогнозы продаж на будущие периоды',
                tags=['Прогнозы'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', prediction_model)
        @jwt_required()
        def get(self):
            """Получить прогнозы продаж на будущие периоды"""
            args = date_range_parser.parse_args()
            period = args.get('period', 'month')
            prediction_periods = args.get('prediction_periods', 6)
            prediction_method = args.get('prediction_method', 'ensemble')
            category_id = args.get('category_id')
            store_id = args.get('store_id')
            product_id = args.get('product_id')
            
            # Получаем диапазон дат для анализа
            if args.get('start_date') and args.get('end_date'):
                try:
                    start_date = datetime.strptime(args['start_date'], '%Y-%m-%d')
                    end_date = datetime.strptime(args['end_date'], '%Y-%m-%d')
                except ValueError:
                    start_date, end_date = get_date_range(period)
            else:
                start_date, end_date = get_date_range(period)
            
            # Базовый запрос с примененными фильтрами
            base_query = db.session.query(Sale)
            
            if category_id:
                base_query = base_query.join(Product).filter(Product.category_id == category_id)
            
            if store_id:
                base_query = base_query.filter(Sale.store_id == store_id)
                
            if product_id:
                base_query = base_query.filter(Sale.product_id == product_id)
            
            # Получаем исторические данные для прогнозирования
            # Для более качественных прогнозов берем данные за более длительный период
            historical_start_date = start_date - timedelta(days=365)
            
            # Получаем помесячные данные
            monthly_sales = db.session.query(
                extract('year', Sale.date).label('year'),
                extract('month', Sale.date).label('month'),
                func.sum(Sale.quantity * Sale.price).label('total')
            ).filter(
                Sale.date.between(historical_start_date, end_date)
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
            for year, month, total in monthly_sales:
                month_name = datetime(int(year), int(month), 1).strftime('%B')
                
                monthly_data.append({
                    'year': int(year),
                    'month': int(month),
                    'month_name': month_name,
                    'total': float(total)
                })
            
            # Сортируем данные по дате
            monthly_data.sort(key=lambda x: (x['year'], x['month']))
            
            # Генерируем ежедневные и еженедельные данные
            daily_data = generate_daily_data(monthly_data, historical_start_date, end_date)
            weekly_data = generate_weekly_data(daily_data)
            yearly_data = generate_yearly_data(monthly_data)
            
            # Преобразуем методы прогнозирования для совместимости с новой функцией
            simple_method = 'average'
            if prediction_method == 'linear':
                simple_method = 'linear'
            elif prediction_method in ['seasonal', 'ensemble']:
                simple_method = 'seasonal'
            
            # Создаем прогнозы
            prediction_results = {
                'method': prediction_method,
                'description': f'Прогноз на основе данных за период с {historical_start_date.strftime("%Y-%m-%d")} по {end_date.strftime("%Y-%m-%d")} с использованием простого метода {simple_method}',
                'daily': [],
                'weekly': [],
                'monthly': [],
                'yearly': []
            }
            
            # Дневные предсказания
            if daily_data:
                daily_values = [item['total'] for item in daily_data]
                last_date = datetime.strptime(daily_data[-1]['date'], '%Y-%m-%d')
                daily_pred = generate_simple_prediction(daily_values, prediction_periods, simple_method)
                prediction_results['daily'] = format_predictions_for_api(
                    daily_values, daily_pred, 'day', last_date
                )
            
            # Недельные предсказания
            if weekly_data:
                weekly_values = [item['total'] for item in weekly_data]
                last_date = datetime.strptime(weekly_data[-1]['end_date'], '%Y-%m-%d')
                weekly_pred = generate_simple_prediction(weekly_values, prediction_periods, simple_method)
                prediction_results['weekly'] = format_predictions_for_api(
                    weekly_values, weekly_pred, 'week', last_date
                )
            
            # Месячные предсказания
            if monthly_data:
                monthly_values = [item['total'] for item in monthly_data]
                last_month = monthly_data[-1]
                last_date = datetime(last_month['year'], last_month['month'], 1)
                monthly_pred = generate_simple_prediction(monthly_values, prediction_periods, simple_method)
                prediction_results['monthly'] = format_predictions_for_api(
                    monthly_values, monthly_pred, 'month', last_date
                )
            
            # Годовые предсказания
            if yearly_data:
                yearly_values = [item['total'] for item in yearly_data]
                last_year = yearly_data[-1]['year']
                last_date = datetime(last_year, 1, 1)
                yearly_pred = generate_simple_prediction(yearly_values, min(3, prediction_periods), simple_method)
                prediction_results['yearly'] = format_predictions_for_api(
                    yearly_values, yearly_pred, 'year', last_date
                )
            
            return prediction_results
    
    @ns.route('/forecast/<string:forecast_type>')
    @ns.param('forecast_type', 'Тип прогноза: sales, revenue, growth')
    class CustomForecast(Resource):
        @ns.doc('custom_forecast', 
                description='Получить специализированный прогноз определенного типа',
                tags=['Прогнозы'])
        @ns.expect(date_range_parser)
        @ns.response(200, 'Успешный запрос', prediction_model)
        @jwt_required()
        def get(self, forecast_type):
            """Получить специализированный прогноз определенного типа"""
            # Маршрут для более специализированных прогнозов
            args = date_range_parser.parse_args()
            
            # Аналогично основному маршруту прогнозов,
            # но с разными моделями и настройками в зависимости от forecast_type
            
            # Здесь можно реализовать различные типы прогнозов:
            # - sales: объем продаж в единицах товара
            # - revenue: выручка в денежном выражении
            # - growth: прогноз роста в процентах
            
            # В качестве примера вернем базовый прогноз
            return {
                'method': 'specialized',
                'description': f'Специализированный прогноз типа {forecast_type}',
                'daily': [],
                'weekly': [],
                'monthly': [],
                'yearly': []
            }
