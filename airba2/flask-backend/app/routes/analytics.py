from flask_restx import Namespace, Resource, fields, reqparse
from flask import request
from sqlalchemy import func, extract, desc, asc, and_, or_, text
from datetime import datetime, timedelta, date
from .. import api, db
from ..models.catalog import CategoryGroup, Category, Product, Sale, City, Store
from flask_jwt_extended import jwt_required
import numpy as np
import pandas as pd
import json
import calendar
from collections import defaultdict
import random
from statistics import mean, median
import math

# Вспомогательные функции для анализа

def get_date_range(time_range=None):
    """
    Возвращает диапазон дат для запросов в зависимости от запрошенного периода
    time_range: day, week, month, quarter, year, all
    """
    # Проверим даты существующих продаж в базе
    min_date = db.session.query(db.func.min(Sale.date)).scalar()
    max_date = db.session.query(db.func.max(Sale.date)).scalar()
    
    # Если данных о продажах нет, используем последний год
    if not min_date or not max_date:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365)
        return start_date, end_date
    
    end_date = max_date
    
    # Определяем начальную дату в зависимости от указанного периода
    if not time_range or time_range == 'all':
        start_date = min_date
    elif time_range == 'day':
        start_date = end_date - timedelta(days=1)
    elif time_range == 'week':
        start_date = end_date - timedelta(days=7)
    elif time_range == 'month':
        start_date = end_date - timedelta(days=30)
    elif time_range == 'quarter':
        start_date = end_date - timedelta(days=90)
    elif time_range == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        # По умолчанию - все данные
        start_date = min_date
    
    return start_date, end_date

def calculate_trend(data_series):
    """Рассчитывает тренд для временного ряда"""
    if not data_series or len(data_series) < 2:
        return 0
    
    x = list(range(len(data_series)))
    y = data_series
    
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
    
    # Избегаем деления на ноль
    if denominator == 0:
        return 0
    
    slope = numerator / denominator
    return slope

def calculate_growth_rate(current, previous):
    """Рассчитывает процент роста между двумя значениями"""
    if previous == 0:
        return 100 if current > 0 else 0
    return ((current - previous) / previous) * 100

def predict_future_values(historical_data, periods=12):
    """
    Прогнозирует будущие значения на основе исторических данных
    Использует простую линейную модель для демонстрации
    """
    if not historical_data or len(historical_data) < 2:
        return [0] * periods
    
    # Вычисляем скользящее среднее для сглаживания
    window_size = min(3, len(historical_data))
    smoothed_data = []
    
    for i in range(len(historical_data)):
        start_idx = max(0, i - window_size + 1)
        window_values = historical_data[start_idx:i+1]
        smoothed_data.append(sum(window_values) / len(window_values))
    
    # Вычисляем тренд
    trend = calculate_trend(smoothed_data)
    
    # Находим сезонность (если данные охватывают более 1 года)
    has_seasonality = len(historical_data) >= 12
    seasonality = []
    
    if has_seasonality:
        # Упрощенный расчет сезонности по месяцам
        monthly_avg = {}
        for i in range(min(12, len(historical_data))):
            month = i % 12 + 1
            if month not in monthly_avg:
                monthly_avg[month] = []
            monthly_avg[month].append(historical_data[i])
        
        # Усредняем значения по каждому месяцу
        for month in range(1, 13):
            if month in monthly_avg and monthly_avg[month]:
                seasonality.append(sum(monthly_avg[month]) / len(monthly_avg[month]))
            else:
                seasonality.append(mean(historical_data))
        
        # Нормализуем сезонные коэффициенты
        overall_mean = mean(historical_data)
        if overall_mean != 0:
            seasonality = [s / overall_mean for s in seasonality]
        else:
            seasonality = [1] * 12
    else:
        seasonality = [1] * 12
    
    # Прогнозируем будущие значения
    last_value = historical_data[-1]
    predictions = []
    
    for i in range(periods):
        # Базовый прогноз на основе тренда
        base_prediction = last_value + (trend * (i + 1))
        
        # Применяем сезонный коэффициент
        if has_seasonality:
            month_idx = (len(historical_data) + i) % 12
            seasonal_factor = seasonality[month_idx]
            prediction = base_prediction * seasonal_factor
        else:
            prediction = base_prediction
        
        # Добавляем случайный компонент (шум)
        noise = random.uniform(-0.05, 0.05) * last_value
        prediction += noise
        
        # Не допускаем отрицательных значений
        prediction = max(0, prediction)
        
        predictions.append(prediction)
    
    return predictions

def generate_daily_data(monthly_data, start_date, end_date):
    """Генерирует ежедневные данные на основе месячных данных"""
    if not monthly_data:
        return []
    
    # Создаем словарь {(год, месяц): сумма} из месячных данных
    monthly_dict = {(item['year'], item['month']): item['total'] for item in monthly_data}
    
    # Генерируем ежедневные данные
    current_date = start_date
    daily_data = []
    
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        
        # Получаем месячную сумму
        monthly_total = monthly_dict.get((year, month), 0)
        
        # Определяем количество дней в месяце
        days_in_month = calendar.monthrange(year, month)[1]
        
        # Распределяем месячную сумму по дням (с небольшой вариацией)
        if monthly_total > 0:
            # Базовая сумма на день
            base_daily = monthly_total / days_in_month
            
            # Применяем вариацию по дням недели
            weekday = current_date.weekday()
            
            # Коэффициенты по дням недели: выходные выше, понедельник ниже
            day_coefficients = [0.85, 0.9, 1.0, 1.05, 1.1, 1.2, 1.15]  # Пн, Вт, Ср, Чт, Пт, Сб, Вс
            daily_total = base_daily * day_coefficients[weekday]
            
            # Добавляем небольшой случайный фактор
            daily_total *= random.uniform(0.9, 1.1)
        else:
            daily_total = 0
        
        daily_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'weekday': weekday,
            'weekday_name': calendar.day_name[weekday],
            'total': round(daily_total, 2)
        })
        
        current_date += timedelta(days=1)
    
    return daily_data

def generate_weekly_data(daily_data):
    """Генерирует еженедельные данные на основе ежедневных данных"""
    if not daily_data:
        return []
    
    # Группируем данные по неделям
    weekly_dict = {}
    
    for item in daily_data:
        date_obj = datetime.strptime(item['date'], '%Y-%m-%d')
        year = date_obj.year
        week = date_obj.isocalendar()[1]  # Номер недели в году
        
        key = (year, week)
        if key not in weekly_dict:
            weekly_dict[key] = {
                'year': year,
                'week': week,
                'total': 0,
                'start_date': item['date'],
                'end_date': item['date']
            }
        
        weekly_dict[key]['total'] += item['total']
        weekly_dict[key]['end_date'] = item['date']
    
    # Преобразуем словарь в список
    weekly_data = list(weekly_dict.values())
    weekly_data.sort(key=lambda x: (x['year'], x['week']))
    
    return weekly_data

def format_time_series_for_charts(data, date_key, value_key):
    """Форматирует временные ряды для использования в графиках"""
    return [
        {'x': item[date_key], 'y': item[value_key]} 
        for item in data if item.get(date_key) and item.get(value_key) is not None
    ]

# Создаем пространство имен для аналитики с расширенным описанием
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
    path='/api/analytics'
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

# Создаем модели данных для Swagger

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
