import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from statistics import mean, median
import math
import warnings
warnings.filterwarnings('ignore')

# Пытаемся импортировать более продвинутые библиотеки для предсказаний
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    sklearn_available = True
except ImportError:
    sklearn_available = False
    print("WARNING: scikit-learn не установлен. Будет использоваться базовая версия алгоритмов.")

try:
    import statsmodels.api as sm
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    statsmodels_available = True
except ImportError:
    statsmodels_available = False
    print("WARNING: statsmodels не установлен. Будет использоваться базовая версия алгоритмов.")

def predict_values_linear(historical_data, periods=6, confidence_base=0.9):
    """
    Прогнозирует будущие значения, используя линейную регрессию.
    
    Args:
        historical_data: Список исторических значений
        periods: Количество периодов для прогноза
        confidence_base: Базовый уровень доверия
        
    Returns:
        Список кортежей (предсказание, уровень доверия)
    """
    if not historical_data or len(historical_data) < 2:
        return [(0, 0.5) for _ in range(periods)]
    
    # Если sklearn доступен, используем его
    if sklearn_available:
        # Преобразуем в numpy arrays
        X = np.array(range(len(historical_data))).reshape(-1, 1)
        y = np.array(historical_data)
        
        # Обучаем модель линейной регрессии
        model = LinearRegression()
        model.fit(X, y)
        
        # Коэффициент детерминации для определения уверенности в прогнозе
        r_squared = model.score(X, y)
        
        # Прогнозируем будущие значения
        future_X = np.array(range(len(historical_data), len(historical_data) + periods)).reshape(-1, 1)
        predictions = model.predict(future_X)
        
        # Нормализуем предсказания (не допускаем отрицательных значений)
        normalized_predictions = [max(0, float(p)) for p in predictions]
        
        # Вычисляем доверительные интервалы на основе R^2
        confidence_scores = [max(0.5, min(0.95, confidence_base * r_squared)) for _ in range(periods)]
        
        # Уменьшаем уверенность по мере удаления в будущее
        for i in range(1, periods):
            confidence_scores[i] *= (1 - 0.03 * i)  # Уменьшаем на 3% с каждым периодом
    else:
        # Используем простую линейную регрессию
        n = len(historical_data)
        x_mean = sum(range(n)) / n
        y_mean = sum(historical_data) / n
        
        # Вычисляем наклон (коэффициент регрессии)
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(historical_data))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        # Избегаем деления на ноль
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Вычисляем точку пересечения
        intercept = y_mean - slope * x_mean
        
        # Прогнозируем будущие значения
        normalized_predictions = []
        for i in range(periods):
            x = n + i
            prediction = intercept + slope * x
            normalized_predictions.append(max(0, prediction))
            
        # Простая оценка уверенности
        # Чем больше наклон отличается от 0, тем меньше уверенность
        abs_slope = abs(slope)
        confidence_base = max(0.5, min(0.9, 0.9 - abs_slope / 10))
        
        confidence_scores = [confidence_base * (1 - 0.05 * i) for i in range(periods)]
    
    return list(zip(normalized_predictions, confidence_scores))

def predict_values_polynomial(historical_data, periods=6, degree=2, confidence_base=0.85):
    """
    Прогнозирует будущие значения, используя полиномиальную регрессию.
    
    Args:
        historical_data: Список исторических значений
        periods: Количество периодов для прогноза
        degree: Степень полинома
        confidence_base: Базовый уровень доверия
        
    Returns:
        Список кортежей (предсказание, уровень доверия)
    """
    if not historical_data or len(historical_data) < 3:
        return [(0, 0.5) for _ in range(periods)]
    
    # Используем sklearn если доступен
    if sklearn_available:
        # Ограничиваем степень полинома в зависимости от количества данных
        max_degree = min(degree, len(historical_data) // 2)
        if max_degree < 1:
            max_degree = 1
        
        # Преобразуем в numpy arrays
        X = np.array(range(len(historical_data))).reshape(-1, 1)
        y = np.array(historical_data)
        
        # Создаем полиномиальные признаки
        poly = PolynomialFeatures(degree=max_degree)
        X_poly = poly.fit_transform(X)
        
        # Обучаем модель линейной регрессии на полиномиальных признаках
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # Коэффициент детерминации для определения уверенности в прогнозе
        r_squared = model.score(X_poly, y)
        
        # Прогнозируем будущие значения
        future_X = np.array(range(len(historical_data), len(historical_data) + periods)).reshape(-1, 1)
        future_X_poly = poly.transform(future_X)
        predictions = model.predict(future_X_poly)
        
        # Нормализуем предсказания (не допускаем отрицательных значений)
        normalized_predictions = [max(0, float(p)) for p in predictions]
        
        # Вычисляем доверительные интервалы на основе R^2
        confidence_scores = [max(0.5, min(0.95, confidence_base * r_squared)) for _ in range(periods)]
    else:
        # Простая альтернатива полиномиальной регрессии - скользящее среднее с трендом
        if len(historical_data) <= 5:
            # Слишком мало данных, используем линейное предсказание
            return predict_values_linear(historical_data, periods, confidence_base)
        
        # Вычисляем простое скользящее среднее
        window_size = min(5, len(historical_data) // 2)
        last_values = historical_data[-window_size:]
        avg = sum(last_values) / len(last_values)
        
        # Оцениваем тренд по последним данным
        slope = (historical_data[-1] - historical_data[-window_size]) / (window_size - 1) if window_size > 1 else 0
        
        # Прогнозируем будущие значения
        normalized_predictions = []
        for i in range(periods):
            # Добавляем нелинейность с убывающим эффектом
            nonlinear_factor = 1 / (1 + 0.1 * i)
            prediction = avg + slope * (i + 1) * nonlinear_factor
            normalized_predictions.append(max(0, prediction))
        
        # Простая оценка уверенности
        confidence_scores = [max(0.5, confidence_base - 0.05 * i) for i in range(periods)]
    
    # Уменьшаем уверенность по мере удаления в будущее
    for i in range(1, periods):
        confidence_scores[i] *= (1 - 0.04 * i)  # Уменьшаем на 4% с каждым периодом
    
    return list(zip(normalized_predictions, confidence_scores))

def predict_seasonal_arima(data, periods=6, confidence_base=0.8):
    """
    Прогнозирует будущие значения, используя SARIMA (сезонная ARIMA).
    Возвращает простой прогноз, если statsmodels не установлен.
    
    Args:
        data: Список словарей с исторической информацией
        periods: Количество периодов для прогноза
        confidence_base: Базовый уровень доверия
        
    Returns:
        Список кортежей (предсказание, уровень доверия)
    """
    if not data or len(data) < 4:
        return [(0, 0.5) for _ in range(periods)]
    
    try:
        # Проверяем, доступен ли statsmodels
        if not statsmodels_available:
            raise ImportError("Statsmodels not available")
        
        # Создаем pandas Series с историческими данными
        df = pd.DataFrame(data)
        
        # Пробуем определить сезонность
        seasonal_period = 7  # По умолчанию недельная
        
        if 'date' in df.columns:
            # Устанавливаем дату в качестве индекса
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            if len(df) >= 365:  # Если больше года данных
                seasonal_period = 365  # Годовая сезонность
            elif len(df) >= 90:  # Если больше квартала
                seasonal_period = 90  # Квартальная сезонность
            elif len(df) >= 30:  # Если больше месяца
                seasonal_period = 30  # Месячная сезонность
        
        # Применяем сезонную ARIMA
        model = sm.tsa.statespace.SARIMAX(
            df['total'],
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, seasonal_period),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        results = model.fit(disp=False)
        
        # Прогнозируем
        forecast = results.forecast(steps=periods)
        
        # Нормализуем предсказания
        normalized_predictions = [max(0, float(p)) for p in forecast]
        
        # Доверительные интервалы на основе точности модели
        # Используем AIC (Akaike Information Criterion) для оценки
        aic = results.aic
        aic_confidence = 1 / (1 + math.exp(aic / 1000))  # Нормализуем AIC
        confidence_scores = [max(0.5, min(0.95, confidence_base * aic_confidence)) for _ in range(periods)]
        
        # Уменьшаем уверенность по мере удаления в будущее
        for i in range(1, periods):
            confidence_scores[i] *= (1 - 0.05 * i)  # Уменьшаем на 5% с каждым периодом
        
        return list(zip(normalized_predictions, confidence_scores))
        
    except Exception as e:
        # Если что-то пошло не так, возвращаем более простой прогноз
        # Просто берем среднее значение и делаем небольшие отклонения
        historical_values = [item['total'] for item in data]
        avg_value = sum(historical_values) / len(historical_values)
        
        predictions = []
        for i in range(periods):
            # Добавляем тренд и случайность
            trend_factor = 1 + (i * 0.01)  # Небольшой рост с каждым периодом
            random_factor = random.uniform(0.95, 1.05)  # 5% случайности
            prediction = avg_value * trend_factor * random_factor
            confidence = max(0.5, confidence_base - (0.05 * i))  # Уменьшаем уверенность
            
            predictions.append((max(0, prediction), confidence))
        
        return predictions

def generate_ensemble_prediction(data, periods=6, confidence_base=0.85):
    """
    Создает ансамбль прогнозов, используя несколько методов.
    
    Args:
        data: Список словарей с исторической информацией
        periods: Количество периодов для прогноза
        confidence_base: Базовый уровень доверия
        
    Returns:
        Список кортежей (предсказание, уровень доверия)
    """
    if not data or len(data) < 2:
        return [(0, 0.5) for _ in range(periods)]
    
    # Экстракт значений total
    historical_values = [item['total'] for item in data]
    
    # Получаем прогнозы от разных моделей
    linear_predictions = predict_values_linear(historical_values, periods, confidence_base)
    poly_predictions = predict_values_polynomial(historical_values, periods, 2, confidence_base)
    if len(data) >= 4:
        seasonal_predictions = predict_seasonal_arima(data, periods, confidence_base)
    else:
        seasonal_predictions = [(0, 0) for _ in range(periods)]
    
    # Взвешивание прогнозов на основе уверенности
    ensemble_predictions = []
    
    for i in range(periods):
        lin_val, lin_conf = linear_predictions[i]
        poly_val, poly_conf = poly_predictions[i]
        seasonal_val, seasonal_conf = seasonal_predictions[i]
        
        # Нормализуем веса, чтобы сумма была 1
        total_conf = lin_conf + poly_conf + seasonal_conf
        if total_conf == 0:
            # Если все модели имеют нулевую уверенность, используем равные веса
            lin_weight = poly_weight = seasonal_weight = 1/3
        else:
            lin_weight = lin_conf / total_conf
            poly_weight = poly_conf / total_conf
            seasonal_weight = seasonal_conf / total_conf
        
        # Взвешенное среднее предсказаний
        ensemble_value = (lin_val * lin_weight + 
                          poly_val * poly_weight + 
                          seasonal_val * seasonal_weight)
        
        # Взвешенное среднее уверенности (с небольшим бонусом для ансамбля)
        ensemble_conf = (lin_conf * lin_weight + 
                         poly_conf * poly_weight + 
                         seasonal_conf * seasonal_weight) * 1.05
        
        # Ограничиваем в диапазоне [0.5, 0.95]
        ensemble_conf = max(0.5, min(0.95, ensemble_conf))
        
        ensemble_predictions.append((ensemble_value, ensemble_conf))
    
    return ensemble_predictions
