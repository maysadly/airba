from datetime import datetime, timedelta
from sqlalchemy import func, extract
import numpy as np
import pandas as pd
from statistics import mean, median, stdev, mode
import math
from .. import db
from ..models.catalog import Sale, Product, Category, Store, City

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
    """Рассчитывает тренд для временного ряда используя линейную регрессию"""
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

def calculate_statistics(data_series):
    """Вычисляет полную статистику для временного ряда"""
    if not data_series or len(data_series) < 2:
        return {
            'mean': 0,
            'median': 0,
            'min': 0,
            'max': 0,
            'std_dev': 0,
            'variance': 0,
            'range': 0,
            'quartiles': [0, 0, 0],
            'skewness': 0,
            'kurtosis': 0
        }
    
    # Преобразуем в numpy array для вычислений
    np_series = np.array(data_series)
    
    # Вычисляем основные статистики
    mean_val = np.mean(np_series)
    median_val = np.median(np_series)
    min_val = np.min(np_series)
    max_val = np.max(np_series)
    std_dev = np.std(np_series)
    variance = np.var(np_series)
    data_range = max_val - min_val
    
    # Вычисляем квартили
    q1 = np.percentile(np_series, 25)
    q2 = np.percentile(np_series, 50)
    q3 = np.percentile(np_series, 75)
    
    # Вычисляем асимметрию (skewness)
    n = len(np_series)
    if std_dev > 0:
        skewness = (np.sum((np_series - mean_val) ** 3) / n) / (std_dev ** 3)
    else:
        skewness = 0
    
    # Вычисляем эксцесс (kurtosis)
    if std_dev > 0:
        kurtosis = (np.sum((np_series - mean_val) ** 4) / n) / (std_dev ** 4) - 3
    else:
        kurtosis = 0
    
    return {
        'mean': float(mean_val),
        'median': float(median_val),
        'min': float(min_val),
        'max': float(max_val),
        'std_dev': float(std_dev),
        'variance': float(variance),
        'range': float(data_range),
        'quartiles': [float(q1), float(q2), float(q3)],
        'skewness': float(skewness),
        'kurtosis': float(kurtosis)
    }

def format_time_series_for_charts(data, date_key, value_key='total'):
    """
    Форматирует временные ряды для использования в графиках
    
    Args:
        data: Список словарей с данными
        date_key: Ключ или функция для извлечения даты
        value_key: Ключ для извлечения значения (по умолчанию 'total')
    """
    result = []
    
    for item in data:
        # Получаем значение даты (может быть функцией или ключом)
        if callable(date_key):
            x_value = date_key(item)
        else:
            x_value = item.get(date_key)
        
        # Получаем значение (всегда ключ)
        y_value = item.get(value_key)
        
        if x_value and y_value is not None:
            result.append({
                'x': x_value,
                'y': float(y_value)
            })
    
    return result

def get_top_entities(entity_type, start_date, end_date, limit=10, prev_start_date=None, prev_end_date=None):
    """
    Универсальная функция для получения топ-N сущностей (товары, категории, магазины)
    
    Args:
        entity_type: тип сущности ('product', 'category', 'store')
        start_date, end_date: период анализа
        limit: количество записей
        prev_start_date, prev_end_date: предыдущий период для сравнения
    """
    current_total_sales = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
        Sale.date.between(start_date, end_date)
    ).scalar() or 0
    
    if entity_type == 'product':
        query = db.session.query(
            Product.id,
            Product.name,
            func.sum(Sale.quantity).label('quantity'),
            func.sum(Sale.quantity * Sale.price).label('revenue'),
            func.avg(Sale.price).label('avg_price')
        ).join(
            Sale
        ).filter(
            Sale.date.between(start_date, end_date)
        ).group_by(
            Product.id,
            Product.name
        ).order_by(
            func.sum(Sale.quantity * Sale.price).desc()
        ).limit(limit)
        
        result = []
        for id, name, quantity, revenue, avg_price in query:
            # Получаем данные за предыдущий период для сравнения
            if prev_start_date and prev_end_date:
                prev_revenue = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
                    Sale.product_id == id,
                    Sale.date.between(prev_start_date, prev_end_date)
                ).scalar() or 0
            else:
                prev_revenue = 0
            
            growth = calculate_growth_rate(revenue, prev_revenue)
            percentage = (revenue / current_total_sales * 100) if current_total_sales > 0 else 0
            
            result.append({
                'id': id,
                'name': name,
                'quantity': int(quantity),
                'revenue': float(revenue),
                'percentage': round(percentage, 2),
                'growth': round(growth, 2),
                'avg_price': float(avg_price)
            })
        
        return result
        
    elif entity_type == 'category':
        query = db.session.query(
            Category.id,
            Category.name,
            func.sum(Sale.quantity * Sale.price).label('revenue'),
            func.count(func.distinct(Product.id)).label('products_count')
        ).join(
            Product, Category.id == Product.category_id
        ).join(
            Sale, Product.id == Sale.product_id
        ).filter(
            Sale.date.between(start_date, end_date)
        ).group_by(
            Category.id,
            Category.name
        ).order_by(
            func.sum(Sale.quantity * Sale.price).desc()
        ).limit(limit)
        
        result = []
        for id, name, revenue, products_count in query:
            # Получаем данные за предыдущий период для сравнения
            if prev_start_date and prev_end_date:
                prev_revenue = db.session.query(func.sum(Sale.quantity * Sale.price)).join(
                    Product, Sale.product_id == Product.id
                ).filter(
                    Product.category_id == id,
                    Sale.date.between(prev_start_date, prev_end_date)
                ).scalar() or 0
            else:
                prev_revenue = 0
            
            growth = calculate_growth_rate(revenue, prev_revenue)
            percentage = (revenue / current_total_sales * 100) if current_total_sales > 0 else 0
            
            result.append({
                'id': id,
                'name': name,
                'revenue': float(revenue),
                'percentage': round(percentage, 2),
                'growth': round(growth, 2),
                'products_count': int(products_count)
            })
        
        return result
        
    elif entity_type == 'store':
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
        ).group_by(
            Store.id,
            Store.name,
            City.name
        ).order_by(
            func.sum(Sale.quantity * Sale.price).desc()
        ).limit(limit)
        
        result = []
        for id, name, city, revenue, orders in query:
            # Получаем данные за предыдущий период для сравнения
            if prev_start_date and prev_end_date:
                prev_revenue = db.session.query(func.sum(Sale.quantity * Sale.price)).filter(
                    Sale.store_id == id,
                    Sale.date.between(prev_start_date, prev_end_date)
                ).scalar() or 0
            else:
                prev_revenue = 0
            
            growth = calculate_growth_rate(revenue, prev_revenue)
            percentage = (revenue / current_total_sales * 100) if current_total_sales > 0 else 0
            avg_order = revenue / orders if orders > 0 else 0
            
            result.append({
                'id': id,
                'name': name,
                'city': city,
                'revenue': float(revenue),
                'percentage': round(percentage, 2),
                'growth': round(growth, 2),
                'avg_order': float(avg_order),
                'orders': int(orders)
            })
        
        return result
    
    return []
