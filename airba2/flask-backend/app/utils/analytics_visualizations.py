from datetime import datetime, timedelta
from sqlalchemy import func, extract, desc
import numpy as np
import pandas as pd
import calendar
import random
from collections import defaultdict
from .. import db
from ..models.catalog import Sale, Product, Category, Store, City

def generate_daily_data(monthly_data, start_date, end_date):
    """
    Генерирует ежедневные данные на основе месячных данных или извлекает из базы при наличии
    
    Args:
        monthly_data: Список словарей с месячными данными
        start_date: Начальная дата
        end_date: Конечная дата
    
    Returns:
        Список словарей с ежедневными данными
    """
    # Пробуем получить реальные ежедневные данные из базы
    daily_sales = db.session.query(
        Sale.date,
        func.sum(Sale.quantity * Sale.price).label('total'),
        func.sum(Sale.quantity).label('quantity'),
        func.count(func.distinct(Sale.id)).label('orders')
    ).filter(
        Sale.date.between(start_date, end_date)
    ).group_by(
        Sale.date
    ).all()
    
    # Если есть реальные данные в базе, используем их
    if daily_sales:
        daily_data = []
        for sale_date, total, quantity, orders in daily_sales:
            weekday = sale_date.weekday()
            daily_data.append({
                'date': sale_date.strftime('%Y-%m-%d'),
                'weekday': weekday,
                'weekday_name': calendar.day_name[weekday],
                'total': float(total),
                'quantity': int(quantity),
                'orders': int(orders)
            })
        
        # Сортируем по дате
        daily_data.sort(key=lambda x: x['date'])
        return daily_data
    
    # Если реальных данных нет, генерируем на основе месячных данных
    if not monthly_data:
        return []
    
    # Создаем словарь {(год, месяц): данные} из месячных данных
    monthly_dict = {(item['year'], item['month']): item for item in monthly_data}
    
    # Генерируем ежедневные данные
    current_date = start_date
    daily_data = []
    
    while current_date <= end_date:
        year = current_date.year
        month = current_date.month
        
        # Получаем месячные данные
        monthly_item = monthly_dict.get((year, month), {
            'total': 0,
            'quantity': 0,
            'orders': 0
        })
        
        monthly_total = monthly_item.get('total', 0)
        monthly_quantity = monthly_item.get('quantity', 0)
        monthly_orders = monthly_item.get('orders', 0)
        
        # Определяем количество дней в месяце
        days_in_month = calendar.monthrange(year, month)[1]
        
        # Распределяем месячную сумму по дням (с учетом дня недели)
        if monthly_total > 0:
            # Коэффициенты по дням недели: выходные выше, понедельник ниже
            weekday = current_date.weekday()
            day_coefficients = [0.85, 0.9, 1.0, 1.05, 1.1, 1.2, 1.15]  # Пн-Вс
            
            # Базовые суммы на день (с учетом коэффициента дня недели)
            daily_coef = day_coefficients[weekday]
            
            # Вычисляем суммарный коэффициент для всех дней месяца
            month_start = datetime(year, month, 1)
            month_end = datetime(year, month, days_in_month)
            total_coef = 0
            
            temp_date = month_start
            while temp_date <= month_end:
                total_coef += day_coefficients[temp_date.weekday()]
                temp_date += timedelta(days=1)
            
            # Распределяем значения пропорционально коэффициентам
            base_daily_total = monthly_total / total_coef * daily_coef
            base_daily_quantity = monthly_quantity / total_coef * daily_coef
            base_daily_orders = monthly_orders / total_coef * daily_coef
            
            # Добавляем небольшой случайный фактор
            random_factor = random.uniform(0.9, 1.1)
            daily_total = base_daily_total * random_factor
            daily_quantity = base_daily_quantity * random_factor
            daily_orders = max(1, int(base_daily_orders * random_factor))
        else:
            daily_total = 0
            daily_quantity = 0
            daily_orders = 0
        
        daily_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'weekday': current_date.weekday(),
            'weekday_name': calendar.day_name[current_date.weekday()],
            'total': round(daily_total, 2),
            'quantity': round(daily_quantity),
            'orders': daily_orders
        })
        
        current_date += timedelta(days=1)
    
    return daily_data

def generate_weekly_data(daily_data):
    """
    Генерирует еженедельные данные на основе ежедневных данных
    
    Args:
        daily_data: Список словарей с ежедневными данными
        
    Returns:
        Список словарей с еженедельными данными
    """
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
                'quantity': 0,
                'orders': 0,
                'start_date': item['date'],
                'end_date': item['date']
            }
        
        weekly_dict[key]['total'] += item['total']
        weekly_dict[key]['quantity'] += item['quantity']
        weekly_dict[key]['orders'] += item['orders']
        weekly_dict[key]['end_date'] = item['date']
    
    # Преобразуем словарь в список
    weekly_data = list(weekly_dict.values())
    
    # Добавляем средний чек
    for item in weekly_data:
        item['avg_order'] = item['total'] / item['orders'] if item['orders'] > 0 else 0
    
    # Сортируем данные по году и неделе
    weekly_data.sort(key=lambda x: (x['year'], x['week']))
    
    return weekly_data

def generate_yearly_data(monthly_data):
    """
    Генерирует ежегодные данные на основе помесячных данных
    
    Args:
        monthly_data: Список словарей с помесячными данными
        
    Returns:
        Список словарей с ежегодными данными
    """
    if not monthly_data:
        return []
    
    # Группируем данные по годам
    yearly_dict = {}
    
    for item in monthly_data:
        year = item['year']
        
        if year not in yearly_dict:
            yearly_dict[year] = {
                'year': year,
                'total': 0,
                'quantity': 0,
                'orders': 0
            }
        
        yearly_dict[year]['total'] += item['total']
        yearly_dict[year]['quantity'] += item.get('quantity', 0)
        yearly_dict[year]['orders'] += item.get('orders', 0)
    
    # Преобразуем словарь в список
    yearly_data = list(yearly_dict.values())
    
    # Добавляем средний чек и рост
    for i, item in enumerate(yearly_data):
        item['avg_order'] = item['total'] / item['orders'] if item['orders'] > 0 else 0
        
        # Вычисляем рост относительно предыдущего года
        if i > 0:
            prev_total = yearly_data[i-1]['total']
            growth = ((item['total'] - prev_total) / prev_total * 100) if prev_total > 0 else 0
        else:
            growth = 0
        
        item['growth'] = round(growth, 2)
    
    # Сортируем данные по году
    yearly_data.sort(key=lambda x: x['year'])
    
    return yearly_data

def generate_hourly_heatmap_data(start_date, end_date):
    """
    Генерирует данные для тепловой карты по часам и дням недели
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
        
    Returns:
        Список словарей для тепловой карты
    """
    # Пробуем получить данные о продажах по часам (если такая информация есть)
    # В данном случае мы генерируем синтетические данные
    
    # Проверим, есть ли колонка 'hour' в таблице Sale
    has_hour_column = False
    try:
        test_query = db.session.query(Sale.hour).limit(1)
        test_query.all()
        has_hour_column = True
    except:
        has_hour_column = False
    
    # Если у нас есть данные по часам в базе, используем их
    if has_hour_column:
        hourly_sales = db.session.query(
            extract('dow', Sale.date).label('day'),
            Sale.hour,
            func.sum(Sale.quantity * Sale.price).label('total')
        ).filter(
            Sale.date.between(start_date, end_date)
        ).group_by(
            extract('dow', Sale.date),
            Sale.hour
        ).all()
        
        result = []
        for day, hour, total in hourly_sales:
            day_name = calendar.day_name[int(day)]
            result.append({
                'day': day_name,
                'hour': int(hour),
                'value': float(total)
            })
            
        return result
    
    # Если данных по часам нет, генерируем синтетические данные
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hours = range(8, 23)  # Предполагаем рабочее время с 8 до 22
    
    result = []
    
    # Коэффициенты для дней недели
    day_coefficients = {
        "Monday": 0.7,
        "Tuesday": 0.8,
        "Wednesday": 0.9,
        "Thursday": 1.0,
        "Friday": 1.2,
        "Saturday": 1.5,
        "Sunday": 1.3
    }
    
    # Коэффициенты для часов (имитация пиков в обед и вечером)
    hour_coefficients = {}
    for h in hours:
        if h < 10:  # Утро
            hour_coefficients[h] = 0.5 + (h - 8) * 0.1
        elif 10 <= h < 14:  # Обед
            hour_coefficients[h] = 1.0 + (h - 10) * 0.1
        elif 14 <= h < 17:  # После обеда
            hour_coefficients[h] = 0.9 - (h - 14) * 0.05
        elif 17 <= h < 20:  # Вечер
            hour_coefficients[h] = 1.2 + (h - 17) * 0.1
        else:  # Поздний вечер
            hour_coefficients[h] = 0.9 - (h - 20) * 0.2
    
    # Базовое значение для нормализации
    base_value = 100
    
    for day in days:
        for hour in hours:
            # Применяем коэффициенты и добавляем случайность
            value = base_value * day_coefficients[day] * hour_coefficients[hour]
            value *= random.uniform(0.8, 1.2)  # 20% случайности
            
            result.append({
                'day': day,
                'hour': hour,
                'value': round(value, 2)
            })
    
    return result

def get_conversion_stats(start_date, end_date):
    """
    Генерирует данные о конверсии и воронке продаж
    
    Args:
        start_date: Начальная дата
        end_date: Конечная дата
        
    Returns:
        Словарь с данными о воронке продаж и конверсии
    """
    # В реальном приложении эти данные были бы получены из базы данных
    # Здесь мы генерируем пример воронки продаж
    
    # Проверяем, есть ли данные о продажах за указанный период
    sales_count = db.session.query(func.count(Sale.id)).filter(
        Sale.date.between(start_date, end_date)
    ).scalar() or 0
    
    if sales_count == 0:
        # Если продаж нет, генерируем демонстрационные данные
        visitors = random.randint(5000, 10000)
        product_views = int(visitors * random.uniform(0.4, 0.6))
        add_to_cart = int(product_views * random.uniform(0.2, 0.3))
        checkout_started = int(add_to_cart * random.uniform(0.5, 0.7))
        purchases = int(checkout_started * random.uniform(0.7, 0.9))
    else:
        # Если есть данные о продажах, генерируем более реалистичную воронку
        purchases = sales_count
        checkout_started = int(purchases / random.uniform(0.7, 0.9))
        add_to_cart = int(checkout_started / random.uniform(0.5, 0.7))
        product_views = int(add_to_cart / random.uniform(0.2, 0.3))
        visitors = int(product_views / random.uniform(0.4, 0.6))
    
    # Рассчитываем конверсию между этапами
    conversion_rate = {
        'visit_to_view': round((product_views / visitors) * 100, 2) if visitors > 0 else 0,
        'view_to_cart': round((add_to_cart / product_views) * 100, 2) if product_views > 0 else 0,
        'cart_to_checkout': round((checkout_started / add_to_cart) * 100, 2) if add_to_cart > 0 else 0,
        'checkout_to_purchase': round((purchases / checkout_started) * 100, 2) if checkout_started > 0 else 0,
        'overall': round((purchases / visitors) * 100, 2) if visitors > 0 else 0
    }
    
    # Формируем данные для воронки
    funnel = [
        {'stage': 'Посетители', 'value': visitors},
        {'stage': 'Просмотры товаров', 'value': product_views},
        {'stage': 'Добавления в корзину', 'value': add_to_cart},
        {'stage': 'Начало оформления', 'value': checkout_started},
        {'stage': 'Покупки', 'value': purchases}
    ]
    
    return {
        'funnel': funnel,
        'conversion': conversion_rate
    }

def get_customer_segments():
    """
    Генерирует данные о сегментации клиентов
    
    Returns:
        Словарь с данными о сегментах клиентов
    """
    # В реальном приложении эти данные были бы получены из базы
    # Здесь мы генерируем примерные сегменты клиентов
    
    # RFM сегментация (Recency, Frequency, Monetary)
    # - Recency: как давно клиент совершал покупку
    # - Frequency: как часто клиент совершает покупки
    # - Monetary: сколько денег клиент тратит
    
    # Создаем сегменты
    segments = {
        'vip': {
            'name': 'VIP клиенты',
            'description': 'Клиенты с высокой частотой покупок и высоким средним чеком',
            'count': random.randint(50, 200),
            'avg_order': random.uniform(5000, 10000),
        },
        'regular': {
            'name': 'Постоянные клиенты',
            'description': 'Клиенты, регулярно совершающие покупки',
            'count': random.randint(500, 1000),
            'avg_order': random.uniform(2000, 4000),
        },
        'occasional': {
            'name': 'Периодические клиенты',
            'description': 'Клиенты, совершающие покупки время от времени',
            'count': random.randint(1000, 2000),
            'avg_order': random.uniform(1000, 2000),
        },
        'one_time': {
            'name': 'Разовые клиенты',
            'description': 'Клиенты, совершившие только одну покупку',
            'count': random.randint(2000, 5000),
            'avg_order': random.uniform(500, 1500),
        },
        'new': {
            'name': 'Новые клиенты',
            'description': 'Клиенты, совершившие первую покупку в течение последнего месяца',
            'count': random.randint(100, 500),
            'avg_order': random.uniform(1000, 3000),
        }
    }
    
    # Вычисляем общую выручку и процент для каждого сегмента
    total_revenue = 0
    for key, segment in segments.items():
        segment['revenue'] = segment['count'] * segment['avg_order']
        total_revenue += segment['revenue']
    
    for key, segment in segments.items():
        segment['percentage'] = (segment['revenue'] / total_revenue * 100) if total_revenue > 0 else 0
    
    return segments

def get_geographic_data():
    """
    Получает географические данные о продажах
    
    Returns:
        Список словарей с географическими данными
    """
    # В реальном приложении эти данные были бы получены из базы
    # Здесь мы генерируем примерные данные о продажах по городам
    
    # Получаем все города из базы
    cities = db.session.query(City.id, City.name).all()
    
    if not cities:
        # Если в базе нет городов, создаем примерные данные
        return [{
            'id': i,
            'name': city,
            'revenue': random.uniform(10000, 100000),
            'orders': random.randint(100, 1000),
            'customers': random.randint(50, 500)
        } for i, city in enumerate([
            'Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 
            'Казань', 'Нижний Новгород', 'Челябинск', 'Самара', 'Омск', 'Ростов-на-Дону'
        ])]
    
    result = []
    for city_id, city_name in cities:
        # Получаем данные о продажах по этому городу
        # Если нет реальных данных, генерируем случайные
        result.append({
            'id': city_id,
            'name': city_name,
            'revenue': random.uniform(10000, 100000),
            'orders': random.randint(100, 1000),
            'customers': random.randint(50, 500)
        })
    
    # Сортируем по выручке
    result.sort(key=lambda x: x['revenue'], reverse=True)
    
    return result
