# API маршруты системы аналитики

В этом документе представлены все доступные маршруты API с примерами запросов и ответов.

## Оглавление

- [Аутентификация](#аутентификация)
  - [Регистрация](#регистрация)
  - [Авторизация](#авторизация)
  - [Обновление токена](#обновление-токена)
- [Панель управления](#панель-управления)
  - [Получение общей аналитики](#получение-общей-аналитики)
- [Прогнозы](#прогнозы)
  - [Прогнозы продаж](#прогнозы-продаж)
  - [Специализированные прогнозы](#специализированные-прогнозы)
- [Отчеты](#отчеты)
  - [Генерация отчета](#генерация-отчета)
  - [Шаблоны отчетов](#шаблоны-отчетов)
- [Категории](#категории)
  - [Топ категорий](#топ-категорий)
  - [Аналитика по категории](#аналитика-по-категории)
- [Товары](#товары)
  - [Топ товаров](#топ-товаров)
  - [Аналитика по товару](#аналитика-по-товару)
- [Магазины](#магазины)
  - [Топ магазинов](#топ-магазинов)
  - [Аналитика по магазину](#аналитика-по-магазину)
  - [Географическая аналитика](#географическая-аналитика)

## Аутентификация

### Регистрация

**URL**: `/api/auth/register`  
**Метод**: `POST`  
**Описание**: Регистрация нового пользователя

**Тело запроса**:
```json
{
  "username": "user123",
  "password": "securepassword"
}
```

**Ответ (201 Created)**:
```json
{
  "message": "Пользователь успешно зарегистрирован"
}
```

**Возможные ошибки**:
- `409 Conflict` - Пользователь с таким именем уже существует
- `500 Internal Server Error` - Ошибка сервера при регистрации

### Авторизация

**URL**: `/api/auth/login`  
**Метод**: `POST`  
**Описание**: Авторизация пользователя и получение JWT токенов

**Тело запроса**:
```json
{
  "username": "user123",
  "password": "securepassword"
}
```

**Ответ (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Возможные ошибки**:
- `401 Unauthorized` - Неверное имя пользователя или пароль

### Обновление токена

**URL**: `/api/auth/refresh`  
**Метод**: `POST`  
**Описание**: Обновление токена доступа с помощью токена обновления

**Заголовки**:
```
Authorization: Bearer <refresh_token>
```

**Ответ (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Возможные ошибки**:
- `401 Unauthorized` - Неверный или просроченный токен обновления

## Панель управления

### Получение общей аналитики

**URL**: `/api/analytics/dashboard`  
**Метод**: `GET`  
**Описание**: Получение комплексной аналитики для панели управления

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)
- `category_id` - ID категории для фильтрации (опционально)
- `store_id` - ID магазина для фильтрации (опционально)
- `product_id` - ID товара для фильтрации (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/dashboard?period=month&category_id=5
```

**Ответ (200 OK)**:
```json
{
  "data": {
    "summary": {
      "total_revenue": 1250000,
      "total_quantity": 2500,
      "avg_order_value": 5000,
      "avg_price": 500,
      "sales_trend": 10.5,
      "growth_rate": 15.3,
      "total_products": 1200,
      "total_categories": 25,
      "total_stores": 15
    },
    "monthly": [
      {
        "year": 2023,
        "month": 1,
        "month_name": "Январь",
        "total": 300000,
        "quantity": 600,
        "orders": 120,
        "avg_order": 2500
      },
      // ... другие месяцы
    ],
    "daily": [
      {
        "date": "2023-01-01",
        "weekday": 6,
        "weekday_name": "Воскресенье",
        "total": 12000,
        "quantity": 24,
        "orders": 5
      },
      // ... другие дни
    ],
    "weekly": [
      {
        "year": 2023,
        "week": 1,
        "start_date": "2023-01-01",
        "end_date": "2023-01-07",
        "total": 75000,
        "quantity": 150,
        "orders": 30,
        "avg_order": 2500
      },
      // ... другие недели
    ],
    "yearly": [
      {
        "year": 2022,
        "total": 1000000,
        "quantity": 2000,
        "orders": 400,
        "avg_order": 2500,
        "growth": 0
      },
      {
        "year": 2023,
        "total": 1250000,
        "quantity": 2500,
        "orders": 500,
        "avg_order": 2500,
        "growth": 25
      }
    ],
    "top_products": [
      {
        "id": 42,
        "name": "Смартфон Samsung Galaxy S21",
        "quantity": 150,
        "revenue": 150000,
        "percentage": 12,
        "growth": 8.5,
        "avg_price": 1000
      },
      // ... другие товары
    ],
    "top_categories": [
      {
        "id": 5,
        "name": "Смартфоны",
        "group_name": "Электроника",
        "revenue": 400000,
        "percentage": 32,
        "growth": 15.2,
        "products_count": 45
      },
      // ... другие категории
    ],
    "top_stores": [
      {
        "id": 3,
        "name": "ТЦ Мега",
        "city": "Москва",
        "revenue": 300000,
        "percentage": 24,
        "growth": 18.7,
        "avg_order": 6000,
        "orders": 50
      },
      // ... другие магазины
    ]
  },
  "charts": {
    "time_series": [
      {"x": "2023-01", "y": 300000},
      {"x": "2023-02", "y": 320000},
      // ... другие точки
    ],
    "category_distribution": [
      {"label": "Смартфоны", "value": 400000},
      {"label": "Ноутбуки", "value": 350000},
      // ... другие категории
    ],
    "heatmap_data": [
      {"day": "Monday", "hour": 9, "value": 50.5},
      {"day": "Monday", "hour": 10, "value": 75.8},
      // ... другие точки
    ],
    "funnel_data": {
      "funnel": [
        {"stage": "Посетители", "value": 10000},
        {"stage": "Просмотры товаров", "value": 5000},
        {"stage": "Добавления в корзину", "value": 1000},
        {"stage": "Начало оформления", "value": 700},
        {"stage": "Покупки", "value": 500}
      ],
      "conversion": {
        "visit_to_view": 50,
        "view_to_cart": 20,
        "cart_to_checkout": 70,
        "checkout_to_purchase": 71.43,
        "overall": 5
      }
    },
    "customer_segments": {
      "vip": {
        "name": "VIP клиенты",
        "description": "Клиенты с высокой частотой покупок и высоким средним чеком",
        "count": 100,
        "avg_order": 8000,
        "revenue": 800000,
        "percentage": 64
      },
      // ... другие сегменты
    },
    "geo_data": [
      {
        "id": 1,
        "name": "Москва",
        "revenue": 600000,
        "orders": 120,
        "customers": 80
      },
      // ... другие города
    ]
  },
  "statistics": {
    "mean": 312500,
    "median": 310000,
    "min": 300000,
    "max": 340000,
    "std_dev": 15811.39,
    "variance": 250000000,
    "range": 40000,
    "quartiles": [300000, 310000, 320000],
    "skewness": 0.94,
    "kurtosis": -0.72
  }
}
```

## Прогнозы

### Прогнозы продаж

**URL**: `/api/analytics/predictions`  
**Метод**: `GET`  
**Описание**: Получение прогнозов продаж на будущие периоды

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)
- `prediction_periods` - Количество периодов для прогноза, по умолчанию 6
- `prediction_method` - Метод прогнозирования (`linear`, `polynomial`, `seasonal`, `ensemble`), по умолчанию `ensemble`
- `category_id` - ID категории для фильтрации (опционально)
- `store_id` - ID магазина для фильтрации (опционально)
- `product_id` - ID товара для фильтрации (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/predictions?period=month&prediction_periods=3&prediction_method=linear
```

**Ответ (200 OK)**:
```json
{
  "method": "linear",
  "description": "Прогноз на основе данных за период с 2023-01-01 по 2023-12-31 с использованием метода linear",
  "daily": [
    {
      "period": "2024-01-01",
      "value": 13000,
      "growth": 5.3,
      "confidence": 0.85
    },
    // ... другие дни
  ],
  "weekly": [
    {
      "period": "2024-W01",
      "value": 78000,
      "growth": 4.0,
      "confidence": 0.82
    },
    // ... другие недели
  ],
  "monthly": [
    {
      "period": "2024-01",
      "value": 330000,
      "growth": 5.8,
      "confidence": 0.9
    },
    // ... другие месяцы
  ],
  "yearly": [
    {
      "period": "2024",
      "value": 4000000,
      "growth": 8.1,
      "confidence": 0.75
    }
  ]
}
```

### Специализированные прогнозы

**URL**: `/api/analytics/forecast/{forecast_type}`  
**Метод**: `GET`  
**Описание**: Получение специализированного прогноза определенного типа

**Параметры пути**:
- `forecast_type` - Тип прогноза (`sales`, `revenue`, `growth`)

**Параметры запроса**: Аналогично `/api/analytics/predictions`

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/forecast/revenue?period=month&prediction_periods=3
```

**Ответ (200 OK)**:
```json
{
  "method": "specialized",
  "description": "Специализированный прогноз типа revenue",
  "daily": [...],
  "weekly": [...],
  "monthly": [...],
  "yearly": [...]
}
```

## Отчеты

### Генерация отчета

**URL**: `/api/analytics/reports`  
**Метод**: `POST`  
**Описание**: Генерация аналитического отчета в выбранном формате

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)

**Тело запроса**:
```json
{
  "format": "json", // csv, excel, json, pdf
  "report_type": "sales", // sales, categories, products, stores
  "include_charts": false,
  "group_by": "day", // day, week, month, year
  "columns": ["date", "total_revenue", "total_quantity", "avg_price"]
}
```

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Ответ (если формат json, 200 OK)**:
```json
{
  "report_type": "sales",
  "start_date": "2023-01-01",
  "end_date": "2023-01-31",
  "group_by": "day",
  "data": [
    {
      "date": "2023-01-01",
      "total_revenue": 12000,
      "total_quantity": 24,
      "avg_price": 500
    },
    // ... другие дни
  ]
}
```

**Если формат CSV, Excel или PDF**: файл для скачивания

### Шаблоны отчетов

**URL**: `/api/analytics/reports/templates`  
**Метод**: `GET`  
**Описание**: Получение списка доступных шаблонов отчетов

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Ответ (200 OK)**:
```json
{
  "templates": [
    {
      "id": "sales_summary",
      "name": "Сводка по продажам",
      "description": "Общая сводка продаж по дням, неделям или месяцам",
      "report_type": "sales",
      "default_format": "excel",
      "group_by": "day",
      "columns": ["date", "total_revenue", "total_quantity", "avg_price"]
    },
    // ... другие шаблоны
  ]
}
```

## Категории

### Топ категорий

**URL**: `/api/analytics/categories/top`  
**Метод**: `GET`  
**Описание**: Получение топ категорий по продажам

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)
- `limit` - Количество категорий в результате, по умолчанию 10
- `store_id` - ID магазина для фильтрации (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/categories/top?period=month&limit=5
```

**Ответ (200 OK)**:
```json
{
  "top_categories": [
    {
      "id": 5,
      "name": "Смартфоны",
      "group_name": "Электроника",
      "revenue": 400000,
      "percentage": 32,
      "growth": 15.2,
      "products_count": 45
    },
    // ... другие категории (всего 5)
  ]
}
```

### Аналитика по категории

**URL**: `/api/analytics/categories/{category_id}/analytics`  
**Метод**: `GET`  
**Описание**: Получение подробной аналитики по конкретной категории

**Параметры пути**:
- `category_id` - ID категории

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/categories/5/analytics?period=month
```

**Ответ (200 OK)**:
```json
{
  "category": {
    "id": 5,
    "name": "Смартфоны",
    "description": "Мобильные телефоны с сенсорным экраном",
    "group_name": "Электроника"
  },
  "sales_stats": {
    "total_quantity": 500,
    "total_revenue": 400000,
    "avg_price": 800,
    "transactions_count": 450,
    "stores_count": 12,
    "products_count": 45,
    "growth": 15.2
  },
  "monthly_data": [
    {
      "year": 2023,
      "month": 1,
      "month_name": "Январь",
      "quantity": 150,
      "revenue": 120000
    },
    // ... другие месяцы
  ],
  "top_products": [
    {
      "id": 42,
      "name": "Смартфон Samsung Galaxy S21",
      "quantity": 60,
      "revenue": 60000,
      "percentage": 15,
      "avg_price": 1000
    },
    // ... другие товары
  ],
  "charts": {
    "time_series": [
      {"x": "2023-01", "y": 120000},
      {"x": "2023-02", "y": 130000},
      // ... другие точки
    ]
  }
}
```

## Товары

### Топ товаров

**URL**: `/api/analytics/products/top`  
**Метод**: `GET`  
**Описание**: Получение топ продаваемых товаров

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)
- `limit` - Количество товаров в результате, по умолчанию 10
- `category_id` - ID категории для фильтрации (опционально)
- `store_id` - ID магазина для фильтрации (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/products/top?period=month&limit=5&category_id=5
```

**Ответ (200 OK)**:
```json
{
  "top_products": [
    {
      "id": 42,
      "name": "Смартфон Samsung Galaxy S21",
      "quantity": 60,
      "revenue": 60000,
      "percentage": 15,
      "growth": 8.5,
      "avg_price": 1000
    },
    // ... другие товары (всего 5)
  ]
}
```

### Аналитика по товару

**URL**: `/api/analytics/products/{product_id}/analytics`  
**Метод**: `GET`  
**Описание**: Получение подробной аналитики по конкретному товару

**Параметры пути**:
- `product_id` - ID товара

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/products/42/analytics?period=month
```

**Ответ (200 OK)**:
```json
{
  "product": {
    "id": 42,
    "name": "Смартфон Samsung Galaxy S21",
    "description": "Флагманский смартфон Samsung 2021 года",
    "category": "Смартфоны"
  },
  "sales_stats": {
    "total_quantity": 60,
    "total_revenue": 60000,
    "avg_price": 1000,
    "transactions_count": 58,
    "stores_count": 10,
    "growth": 8.5
  },
  "monthly_data": [
    {
      "year": 2023,
      "month": 1,
      "month_name": "Январь",
      "quantity": 18,
      "revenue": 18000
    },
    // ... другие месяцы
  ],
  "top_stores": [
    {
      "id": 3,
      "name": "ТЦ Мега",
      "city": "Москва",
      "quantity": 15,
      "revenue": 15000,
      "percentage": 25
    },
    // ... другие магазины
  ],
  "charts": {
    "time_series": [
      {"x": "2023-01", "y": 18000},
      {"x": "2023-02", "y": 20000},
      // ... другие точки
    ]
  }
}
```

## Магазины

### Топ магазинов

**URL**: `/api/analytics/stores/top`  
**Метод**: `GET`  
**Описание**: Получение топ магазинов по продажам

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)
- `limit` - Количество магазинов в результате, по умолчанию 10
- `category_id` - ID категории для фильтрации (опционально)
- `product_id` - ID товара для фильтрации (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/stores/top?period=month&limit=5
```

**Ответ (200 OK)**:
```json
{
  "top_stores": [
    {
      "id": 3,
      "name": "ТЦ Мега",
      "city": "Москва",
      "revenue": 300000,
      "percentage": 24,
      "growth": 18.7,
      "avg_order": 6000,
      "orders": 50
    },
    // ... другие магазины (всего 5)
  ]
}
```

### Аналитика по магазину

**URL**: `/api/analytics/stores/{store_id}/analytics`  
**Метод**: `GET`  
**Описание**: Получение подробной аналитики по конкретному магазину

**Параметры пути**:
- `store_id` - ID магазина

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `year`, `all`), по умолчанию `month`
- `start_date` - Начальная дата в формате YYYY-MM-DD (опционально)
- `end_date` - Конечная дата в формате YYYY-MM-DD (опционально)

**Заголовки**:
```
Authorization: Bearer <access_token>
```

**Пример запроса**:
```
GET /api/analytics/stores/3/analytics?period=month
```

**Ответ (200 OK)**:
```json
{
  "store": {
    "id": 3,
    "name": "ТЦ Мега",
    "address": "ул. Московская, 10",
    "city": "Москва"
  },
  "sales_stats": {
    "total_quantity": 350,
    "total_revenue": 300000,
    "avg_price": 857.14,
    "transactions_count": 50,
    "products_count": 120,
    "growth": 18.7
  },
  "monthly_data": [
    {
      "year": 2023,
      "month": 1,
      "month_name": "Январь",
      "quantity": 100,
      "revenue": 90000,
      "orders": 15,
      "avg_order": 6000
    },
    // ... другие месяцы
  ],
  "top_categories": [
    {
      "id": 5,
      "name": "Смартфоны",
      "quantity": 60,
      "revenue": 60000,
      "percentage": 20
    },
    // ... другие категории
  ],
  "top_products": [
    {
      "id": 42,
      "name": "Смартфон Samsung Galaxy S21",
      "category": "Смартфоны",
      "quantity": 15,
      "revenue": 15000,
      "percentage": 5,
      "avg_price": 1000
    },
    // ... другие товары
  ],
  "charts": {
    "time_series": [
      {"x": "2023-01", "y": 90000},
      {"x": "2023-02", "y": 100000},
      // ... другие точки
    ],
    "category_distribution": [
      {"label": "Смартфоны", "value": 60000},
      {"label": "Ноутбуки", "value": 55000},
      // ... другие категории
    ]
  }
}
```

### Географическая аналитика

**URL**: `/api/analytics/stores/geo`  
**Метод**: `GET`  
**Описание**: Получение географических данных о магазинах и продажах

**Параметры запроса**:
- `period` - Период анализа (`day`, `week`, `month`, `quarter`, `