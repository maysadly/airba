from flask_restx import Namespace, Resource, fields, reqparse
from datetime import datetime, timedelta
import calendar
import random

# Обновим путь для аналитики без дополнительного префикса /api
analytics_ns = Namespace(
    'analytics', 
    description='''
    Расширенная аналитика продаж и прогнозирование.
    
    Модуль предоставляет:
    * Анализ продаж по разным временным периодам
    * Статистику продаж по товарам, категориям и магазинам
    * Прогнозирование будущих продаж различными методами
    * Визуализацию данных для панелей управления
    * Формирование отчетов в различных форматах
    ''',
    path='/analytics'  # Изменено с /api/analytics на /analytics, так как /api уже есть в Blueprint
)

# Парсеры для запросов
date_range_parser = reqparse.RequestParser()
date_range_parser.add_argument('period', type=str, 
                              choices=['day', 'week', 'month', 'quarter', 'year', 'all'], 
                              default='month', 
                              help='Период для анализа: день, неделя, месяц, квартал, год или все данные')
date_range_parser.add_argument('start_date', type=str, help='Начальная дата (YYYY-MM-DD)')
date_range_parser.add_argument('end_date', type=str, help='Конечная дата (YYYY-MM-DD)')
date_range_parser.add_argument('prediction_periods', type=int, default=6, 
                              help='Количество периодов для прогноза')
date_range_parser.add_argument('prediction_method', type=str, 
                              choices=['linear', 'polynomial', 'seasonal', 'ensemble'], 
                              default='ensemble',
                              help='Метод прогнозирования: линейный, полиномиальный, сезонный или ансамбль')
date_range_parser.add_argument('category_id', type=int, help='ID категории для фильтрации')
date_range_parser.add_argument('store_id', type=int, help='ID магазина для фильтрации')
date_range_parser.add_argument('product_id', type=int, help='ID товара для фильтрации')

# Модели базовых данных
date_point_model = analytics_ns.model('DatePoint', {
    'x': fields.String(description='Дата в формате YYYY-MM-DD или YYYY-MM'),
    'y': fields.Float(description='Значение')
})

category_point_model = analytics_ns.model('CategoryPoint', {
    'label': fields.String(description='Название категории'),
    'value': fields.Float(description='Значение')
})

# Модель статистики
statistics_model = analytics_ns.model('Statistics', {
    'mean': fields.Float(description='Среднее значение'),
    'median': fields.Float(description='Медиана'),
    'min': fields.Float(description='Минимальное значение'),
    'max': fields.Float(description='Максимальное значение'),
    'std_dev': fields.Float(description='Стандартное отклонение'),
    'variance': fields.Float(description='Дисперсия'),
    'range': fields.Float(description='Разброс (max - min)'),
    'quartiles': fields.List(fields.Float, description='Квартили [25%, 50%, 75%]'),
    'skewness': fields.Float(description='Коэффициент асимметрии'),
    'kurtosis': fields.Float(description='Коэффициент эксцесса')
})

# Модель для прогнозов
prediction_data_model = analytics_ns.model('PredictionData', {
    'period': fields.String(description='Период прогноза (дата или месяц)'),
    'value': fields.Float(description='Прогнозируемое значение'),
    'growth': fields.Float(description='Процент роста относительно предыдущего периода'),
    'confidence': fields.Float(description='Коэффициент уверенности в прогнозе (0-1)')
})

# Модели для ежедневных, еженедельных и помесячных данных
daily_data_model = analytics_ns.model('DailyData', {
    'date': fields.String(description='Дата в формате YYYY-MM-DD'),
    'weekday': fields.Integer(description='День недели (0-6, где 0 - понедельник)'),
    'weekday_name': fields.String(description='Название дня недели'),
    'total': fields.Float(description='Сумма продаж'),
    'quantity': fields.Integer(description='Количество проданных товаров'),
    'orders': fields.Integer(description='Количество заказов')
})

weekly_data_model = analytics_ns.model('WeeklyData', {
    'year': fields.Integer(description='Год'),
    'week': fields.Integer(description='Номер недели в году'),
    'start_date': fields.String(description='Начальная дата недели'),
    'end_date': fields.String(description='Конечная дата недели'),
    'total': fields.Float(description='Сумма продаж'),
    'quantity': fields.Integer(description='Количество проданных товаров'),
    'orders': fields.Integer(description='Количество заказов'),
    'avg_order': fields.Float(description='Средний чек')
})

monthly_data_model = analytics_ns.model('MonthlyData', {
    'year': fields.Integer(description='Год'),
    'month': fields.Integer(description='Месяц (1-12)'),
    'month_name': fields.String(description='Название месяца'),
    'total': fields.Float(description='Сумма продаж'),
    'quantity': fields.Integer(description='Количество проданных товаров'),
    'orders': fields.Integer(description='Количество заказов'),
    'avg_order': fields.Float(description='Средний чек')
})

yearly_data_model = analytics_ns.model('YearlyData', {
    'year': fields.Integer(description='Год'),
    'total': fields.Float(description='Сумма продаж'),
    'quantity': fields.Integer(description='Количество проданных товаров'),
    'orders': fields.Integer(description='Количество заказов'),
    'avg_order': fields.Float(description='Средний чек'),
    'growth': fields.Float(description='Рост относительно предыдущего года (%)')
})

# Модель для общих показателей
summary_metrics_model = analytics_ns.model('SummaryMetrics', {
    'total_revenue': fields.Float(description='Общая выручка'),
    'total_quantity': fields.Integer(description='Общее количество проданных товаров'),
    'avg_order_value': fields.Float(description='Средний чек'),
    'avg_price': fields.Float(description='Средняя цена товара'),
    'sales_trend': fields.Float(description='Тренд продаж (%)'),
    'growth_rate': fields.Float(description='Коэффициент роста (%)'),
    'total_products': fields.Integer(description='Общее количество товаров'),
    'total_categories': fields.Integer(description='Общее количество категорий'),
    'total_stores': fields.Integer(description='Общее количество магазинов')
})

# Модель данных тепловой карты
heatmap_data_model = analytics_ns.model('HeatmapData', {
    'day': fields.String(description='День недели'),
    'hour': fields.Integer(description='Час (0-23)'),
    'value': fields.Float(description='Значение')
})

# Модель для топ товаров
top_product_model = analytics_ns.model('TopProduct', {
    'id': fields.Integer(description='ID товара'),
    'name': fields.String(description='Название товара'),
    'quantity': fields.Integer(description='Количество проданных единиц'),
    'revenue': fields.Float(description='Выручка'),
    'percentage': fields.Float(description='Процент от общей выручки'),
    'growth': fields.Float(description='Рост относительно предыдущего периода (%)'),
    'avg_price': fields.Float(description='Средняя цена')
})

# Модель для топ категорий
top_category_model = analytics_ns.model('TopCategory', {
    'id': fields.Integer(description='ID категории'),
    'name': fields.String(description='Название категории'),
    'group_name': fields.String(description='Название группы категорий', required=False),
    'revenue': fields.Float(description='Выручка'),
    'percentage': fields.Float(description='Процент от общей выручки'),
    'growth': fields.Float(description='Рост относительно предыдущего периода (%)'),
    'products_count': fields.Integer(description='Количество товаров')
})

# Модель для топ магазинов
top_store_model = analytics_ns.model('TopStore', {
    'id': fields.Integer(description='ID магазина'),
    'name': fields.String(description='Название магазина'),
    'city': fields.String(description='Город'),
    'revenue': fields.Float(description='Выручка'),
    'percentage': fields.Float(description='Процент от общей выручки'),
    'growth': fields.Float(description='Рост относительно предыдущего периода (%)'),
    'avg_order': fields.Float(description='Средний чек'),
    'orders': fields.Integer(description='Количество заказов')
})

# Модель воронки продаж
funnel_data_model = analytics_ns.model('FunnelData', {
    'funnel': fields.List(fields.Raw(description='Этап воронки')),
    'conversion': fields.Raw(description='Данные о конверсии')
})

# Модель географических данных
geo_data_model = analytics_ns.model('GeoData', {
    'id': fields.Integer(description='ID города'),
    'name': fields.String(description='Название города'),
    'revenue': fields.Float(description='Выручка'),
    'orders': fields.Integer(description='Количество заказов'),
    'customers': fields.Integer(description='Количество клиентов')
})

# Модель сегментации клиентов
customer_segment_model = analytics_ns.model('CustomerSegment', {
    'name': fields.String(description='Название сегмента'),
    'description': fields.String(description='Описание сегмента'),
    'count': fields.Integer(description='Количество клиентов'),
    'avg_order': fields.Float(description='Средний чек'),
    'revenue': fields.Float(description='Общая выручка'),
    'percentage': fields.Float(description='Процент от общей выручки')
})

# Модель для предсказаний
prediction_model = analytics_ns.model('Prediction', {
    'method': fields.String(description='Метод предсказания'),
    'description': fields.String(description='Описание предсказания'),
    'daily': fields.List(fields.Nested(prediction_data_model), description='Ежедневные предсказания'),
    'weekly': fields.List(fields.Nested(prediction_data_model), description='Еженедельные предсказания'),
    'monthly': fields.List(fields.Nested(prediction_data_model), description='Ежемесячные предсказания'),
    'yearly': fields.List(fields.Nested(prediction_data_model), description='Ежегодные предсказания')
})

# Модель для чарт-данных
chart_data_model = analytics_ns.model('ChartData', {
    'time_series': fields.List(fields.Nested(date_point_model), description='Временные ряды для линейных графиков'),
    'category_distribution': fields.List(fields.Nested(category_point_model), description='Данные для круговых и столбчатых диаграмм'),
    'heatmap_data': fields.List(fields.Nested(heatmap_data_model), description='Данные для тепловой карты'),
    'funnel_data': fields.Nested(funnel_data_model, description='Данные для воронки продаж'),
    'customer_segments': fields.Raw(description='Данные о сегментации клиентов'),
    'geo_data': fields.List(fields.Nested(geo_data_model), description='Географические данные')
})

# Модель общей аналитики в обновленном формате
advanced_analytics_model = analytics_ns.model('AdvancedAnalytics', {
    'data': fields.Raw(description='Фактические аналитические данные'),
    'predict': fields.Raw(description='Предсказания на будущие периоды'),
    'charts': fields.Nested(chart_data_model, description='Данные для построения графиков'),
    'statistics': fields.Nested(statistics_model, description='Статистические показатели')
})
