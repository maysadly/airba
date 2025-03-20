"""
Модуль с упрощенными алгоритмами для аналитики и прогнозирования.
Не требует scikit-learn или statsmodels.
"""
import numpy as np
import math
import random
from datetime import datetime, timedelta

def simple_moving_average(data, window=3):
    """
    Простое скользящее среднее.
    
    Args:
        data: список числовых значений
        window: размер окна
        
    Returns:
        Список сглаженных значений
    """
    result = []
    for i in range(len(data)):
        start_idx = max(0, i - window + 1)
        window_values = data[start_idx:i+1]
        result.append(sum(window_values) / len(window_values))
    return result

def simple_linear_regression(x, y):
    """
    Простая линейная регрессия без использования scikit-learn.
    
    Args:
        x: список значений независимой переменной
        y: список значений зависимой переменной
        
    Returns:
        (slope, intercept) - коэффициенты линейной регрессии
    """
    n = len(x)
    if n != len(y) or n < 2:
        return 0, 0
        
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
    
    if denominator == 0:
        return 0, mean_y
    
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    
    return slope, intercept

def naive_seasonal_forecast(data, periods=6, seasonal_period=7, alpha=0.3):
    """
    Наивный сезонный прогноз, комбинирующий тренд и сезонность.
    
    Args:
        data: список исторических значений
        periods: количество периодов для прогноза
        seasonal_period: период сезонности (например, 7 для недельной)
        alpha: вес для экспоненциального сглаживания (0-1)
        
    Returns:
        Список прогнозных значений
    """
    if len(data) < max(seasonal_period * 2, 10):
        # Недостаточно данных для хорошего сезонного прогноза
        return [data[-1]] * periods
    
    # Вычисляем сезонные индексы
    seasons = {}
    for i in range(len(data)):
        season_idx = i % seasonal_period
        if season_idx not in seasons:
            seasons[season_idx] = []
        seasons[season_idx].append(data[i])
    
    # Усредняем сезонные индексы
    seasonal_indices = {}
    for season, values in seasons.items():
        seasonal_indices[season] = sum(values) / len(values)
    
    # Нормализуем индексы
    avg_value = sum(data) / len(data)
    for season in seasonal_indices:
        seasonal_indices[season] = seasonal_indices[season] / avg_value if avg_value > 0 else 1.0
    
    # Прогнозируем будущие значения
    result = []
    for i in range(periods):
        # Индекс сезона для прогноза
        season_idx = (len(data) + i) % seasonal_period
        
        # Базовый прогноз (используем экспоненциальное сглаживание)
        base_value = data[-1]
        for j in range(min(5, len(data)-1)):
            weight = alpha * (1-alpha)**j
            base_value += weight * data[-(j+2)]
        
        # Применяем сезонный коэффициент
        seasonal_factor = seasonal_indices.get(season_idx, 1.0)
        forecast = base_value * seasonal_factor
        
        # Добавляем немного случайности
        forecast *= random.uniform(0.95, 1.05)
        
        result.append(max(0, forecast))
    
    return result

def generate_simple_prediction(data, periods=6, method='average'):
    """
    Генерирует прогноз на основе исторических данных, используя простые методы.
    
    Args:
        data: список исторических значений
        periods: количество периодов для прогноза
        method: метод прогнозирования ('average', 'linear', 'seasonal')
        
    Returns:
        Список прогнозных значений и их достоверность (значение, достоверность)
    """
    if not data or len(data) < 2:
        return [(0, 0.5) for _ in range(periods)]
    
    # Методы прогнозирования
    if method == 'average':
        # Простое среднее значение
        avg = sum(data) / len(data)
        predictions = [avg] * periods
        
        # Уверенность на основе стандартного отклонения
        variance = sum((x - avg) ** 2 for x in data) / len(data)
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        # Более высокая вариация означает меньшую уверенность
        if avg > 0:
            confidence_base = max(0.5, min(0.9, 1 - (std_dev / avg) * 0.5))
        else:
            confidence_base = 0.5
            
    elif method == 'linear':
        # Линейная регрессия
        x = list(range(len(data)))
        slope, intercept = simple_linear_regression(x, data)
        
        predictions = []
        for i in range(periods):
            next_x = len(data) + i
            predictions.append(intercept + slope * next_x)
        
        # Оценка уверенности на основе остатков регрессии
        predicted_past = [intercept + slope * i for i in range(len(data))]
        errors = [abs(data[i] - predicted_past[i]) for i in range(len(data))]
        avg_error = sum(errors) / len(errors) if errors else 0
        
        if sum(data) / len(data) > 0:
            confidence_base = max(0.5, min(0.9, 1 - (avg_error / (sum(data) / len(data))) * 0.5))
        else:
            confidence_base = 0.5
    
    else:  # 'seasonal'
        # Наивный сезонный прогноз
        predictions = naive_seasonal_forecast(data, periods)
        
        # Базовая уверенность немного выше, так как учитываем сезонность
        confidence_base = 0.7
    
    # Уменьшаем уверенность по мере удаления в будущее
    result = []
    for i, pred in enumerate(predictions):
        # С каждым шагом в будущее снижаем уверенность на 5%
        confidence = max(0.5, confidence_base * (1 - 0.05 * i))
        result.append((max(0, pred), confidence))
    
    return result

def generate_date_series(start_date, periods, freq='day'):
    """
    Генерирует серию дат для прогнозов.
    
    Args:
        start_date: начальная дата (строка формата YYYY-MM-DD или объект datetime)
        periods: количество периодов
        freq: частота ('day', 'week', 'month', 'year')
        
    Returns:
        Список строк с датами
    """
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    
    result = []
    current_date = start_date
    
    for _ in range(periods):
        if freq == 'day':
            current_date += timedelta(days=1)
            result.append(current_date.strftime('%Y-%m-%d'))
        elif freq == 'week':
            current_date += timedelta(days=7)
            result.append(f"{current_date.strftime('%Y')}-W{current_date.isocalendar()[1]:02d}")
        elif freq == 'month':
            year = current_date.year + (current_date.month // 12)
            month = (current_date.month % 12) + 1
            current_date = current_date.replace(year=year, month=month)
            result.append(f"{current_date.strftime('%Y-%m')}")
        elif freq == 'year':
            current_date = current_date.replace(year=current_date.year + 1)
            result.append(str(current_date.year))
    
    return result

def format_predictions_for_api(historical_data, predictions, freq='day', start_date=None):
    """
    Форматирует прогнозы для API.
    
    Args:
        historical_data: список исторических значений
        predictions: список кортежей (прогноз, уверенность)
        freq: частота ('day', 'week', 'month', 'year')
        start_date: начальная дата для прогноза (если None, используется текущая дата)
        
    Returns:
        Список словарей с прогнозами
    """
    if not start_date:
        start_date = datetime.now()
    
    # Генерируем даты
    dates = generate_date_series(start_date, len(predictions), freq)
    
    # Форматируем результат
    result = []
    for i, ((value, confidence), date_str) in enumerate(zip(predictions, dates)):
        # Вычисляем процент роста относительно предыдущего значения
        if i == 0:
            prev_value = historical_data[-1] if historical_data else 0
        else:
            prev_value = predictions[i-1][0]
        
        growth = ((value - prev_value) / prev_value * 100) if prev_value > 0 else 0
        
        result.append({
            'period': date_str,
            'value': round(value, 2),
            'growth': round(growth, 2),
            'confidence': round(confidence, 2)
        })
    
    return result
