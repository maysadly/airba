import random
from datetime import datetime, timedelta
from .. import db
from ..models.catalog import CategoryGroup, Category, Product, Sale, City, Store

def generate_mock_data():
    """Генерирует реалистичные тестовые данные для электронного магазина"""
    # Очищаем существующие данные
    db.session.query(Sale).delete()
    db.session.query(Product).delete()
    db.session.query(Category).delete()
    db.session.query(CategoryGroup).delete()
    db.session.query(Store).delete()
    db.session.query(City).delete()
    
    # Создаем города
    cities = [
        City(name="Москва", region="Центральный", population=12600000),
        City(name="Санкт-Петербург", region="Северо-Западный", population=5300000),
        City(name="Новосибирск", region="Сибирский", population=1600000),
        City(name="Екатеринбург", region="Уральский", population=1400000),
        City(name="Казань", region="Приволжский", population=1200000),
        City(name="Нижний Новгород", region="Приволжский", population=1250000),
        City(name="Челябинск", region="Уральский", population=1130000),
        City(name="Самара", region="Приволжский", population=1150000)
    ]
    db.session.add_all(cities)
    db.session.commit()
    
    # Создаем магазины
    stores = [
        # Москва
        Store(name="Электроника City ТЦ Метрополис", address="Ленинградское шоссе, 16А", city_id=1, size=450, 
              opening_date=datetime(2015, 6, 15)),
        Store(name="Электроника City ТРЦ Авиапарк", address="Ходынский бульвар, 4", city_id=1, size=570, 
              opening_date=datetime(2016, 3, 22)),
        Store(name="Электроника City ТЦ Кунцево Плаза", address="Ярцевская улица, 19", city_id=1, size=380, 
              opening_date=datetime(2019, 4, 8)),
        
        # Санкт-Петербург
        Store(name="Электроника City ТРК Галерея", address="Лиговский проспект, 30А", city_id=2, size=410, 
              opening_date=datetime(2017, 8, 10)),
        Store(name="Электроника City Невский", address="Невский проспект, 114", city_id=2, size=320, 
              opening_date=datetime(2018, 12, 5)),
        
        # Новосибирск
        Store(name="Электроника City ТРЦ Аура", address="Военная улица, 5", city_id=3, size=285, 
              opening_date=datetime(2019, 9, 18)),
        
        # Екатеринбург
        Store(name="Электроника City ТРЦ Гринвич", address="ул. 8 Марта, 46", city_id=4, size=340, 
              opening_date=datetime(2020, 2, 27)),
        
        # Казань
        Store(name="Электроника City ТЦ Мега", address="проспект Победы, 141", city_id=5, size=370, 
              opening_date=datetime(2021, 5, 15)),
        
        # Нижний Новгород
        Store(name="Электроника City ТРЦ Седьмое Небо", address="ул. Бетанкура, 1", city_id=6, size=310, 
              opening_date=datetime(2021, 8, 22)),
        
        # Челябинск
        Store(name="Электроника City ТРК Родник", address="ул. Труда, 203", city_id=7, size=295, 
              opening_date=datetime(2022, 3, 12)),
        
        # Самара
        Store(name="Электроника City ТРК Космопорт", address="Дыбенко, 30", city_id=8, size=325, 
              opening_date=datetime(2022, 7, 8))
    ]
    db.session.add_all(stores)
    db.session.commit()
    
    # Создаем группы категорий
    groups = [
        CategoryGroup(name="Компьютерная техника", description="Компьютеры, ноутбуки, комплектующие и аксессуары"),
        CategoryGroup(name="Смартфоны и гаджеты", description="Мобильные телефоны, планшеты и аксессуары"),
        CategoryGroup(name="Аудио и видео", description="Телевизоры, аудиосистемы, проекторы и аксессуары"),
        CategoryGroup(name="Бытовая техника", description="Крупная и мелкая бытовая техника для дома"),
        CategoryGroup(name="Фото и видео", description="Фотоаппараты, видеокамеры и аксессуары"),
        CategoryGroup(name="Игры и развлечения", description="Консоли, игры, виртуальная реальность")
    ]
    db.session.add_all(groups)
    db.session.commit()
    
    # Создаем категории (объединяем бывшие категории и подкатегории)
    categories = [
        # Компьютерная техника
        Category(name="Игровые ноутбуки", description="Мощные ноутбуки для запуска современных игр", group_id=1),
        Category(name="Ультрабуки", description="Тонкие и лёгкие ноутбуки с долгим временем работы", group_id=1),
        Category(name="Трансформеры", description="Ноутбуки с поворотным экраном или отстёгиваемой клавиатурой", group_id=1),
        Category(name="Игровые ПК", description="Мощные компьютеры для запуска современных игр", group_id=1),
        Category(name="Офисные ПК", description="Компьютеры для работы с документами и интернетом", group_id=1),
        Category(name="Моноблоки", description="Компьютеры, совмещённые с монитором", group_id=1),
        Category(name="Процессоры", description="Центральные процессоры для компьютеров", group_id=1),
        Category(name="Видеокарты", description="Графические процессоры для компьютеров", group_id=1),
        Category(name="Оперативная память", description="Модули оперативной памяти для компьютеров", group_id=1),
        Category(name="Накопители", description="HDD и SSD для хранения данных", group_id=1),
        Category(name="Мониторы", description="Устройства для вывода изображения", group_id=1),
        Category(name="Клавиатуры", description="Устройства для ввода текста", group_id=1),
        Category(name="Мыши", description="Устройства для управления курсором", group_id=1),
        
        # Смартфоны и гаджеты
        Category(name="Android-смартфоны", description="Смартфоны на базе операционной системы Android", group_id=2),
        Category(name="iPhone", description="Смартфоны Apple на базе операционной системы iOS", group_id=2),
        Category(name="Android-планшеты", description="Планшеты на базе операционной системы Android", group_id=2),
        Category(name="iPad", description="Планшеты Apple на базе операционной системы iPadOS", group_id=2),
        Category(name="Windows-планшеты", description="Планшеты на базе операционной системы Windows", group_id=2),
        Category(name="Apple Watch", description="Умные часы Apple", group_id=2),
        Category(name="WearOS-часы", description="Умные часы на базе операционной системы WearOS", group_id=2),
        Category(name="Фитнес-браслеты", description="Устройства для отслеживания физической активности", group_id=2),
        Category(name="Чехлы", description="Защитные чехлы для смартфонов", group_id=2),
        Category(name="Защитные стёкла", description="Защитные стёкла для экранов смартфонов", group_id=2),
        Category(name="Зарядные устройства", description="Устройства для зарядки смартфонов", group_id=2),
        
        # Аудио и видео
        Category(name="OLED-телевизоры", description="Телевизоры с OLED-экранами", group_id=3),
        Category(name="QLED-телевизоры", description="Телевизоры с QLED-экранами", group_id=3),
        Category(name="LED-телевизоры", description="Телевизоры с LED-экранами", group_id=3),
        Category(name="Музыкальные центры", description="Стационарные аудиосистемы", group_id=3),
        Category(name="Беспроводные колонки", description="Портативные аудиосистемы", group_id=3),
        Category(name="Саундбары", description="Звуковые панели для телевизоров", group_id=3),
        Category(name="Домашние проекторы", description="Проекторы для домашнего использования", group_id=3),
        Category(name="Офисные проекторы", description="Проекторы для бизнес-презентаций", group_id=3),
        Category(name="Портативные проекторы", description="Компактные проекторы", group_id=3),
        Category(name="Беспроводные наушники", description="Наушники без проводов", group_id=3),
        Category(name="Проводные наушники", description="Классические наушники с проводом", group_id=3),
        Category(name="Игровые наушники", description="Наушники для геймеров с микрофоном", group_id=3),
        
        # Добавьте больше категорий для Бытовой техники, Фото и видео, Игр и развлечений
        # ...
    ]
    db.session.add_all(categories)
    db.session.commit()
    
    # Создаем продукты
    products = [
        # Игровые ноутбуки
        Product(name="MSI Katana GF76", description="Игровой ноутбук с процессором Intel Core i7 и видеокартой NVIDIA GeForce RTX 3060", price=89990, stock=15, category_id=1),
        Product(name="ASUS ROG Strix G15", description="Игровой ноутбук с процессором AMD Ryzen 7 и видеокартой NVIDIA GeForce RTX 3070", price=119990, stock=10, category_id=1),
        Product(name="Acer Predator Helios 300", description="Игровой ноутбук с процессором Intel Core i7 и видеокартой NVIDIA GeForce RTX 3070 Ti", price=129990, stock=8, category_id=1),
        Product(name="Lenovo Legion 5 Pro", description="Игровой ноутбук с процессором AMD Ryzen 7 и видеокартой NVIDIA GeForce RTX 3070", price=124990, stock=12, category_id=1),
        
        # Ультрабуки
        Product(name="Apple MacBook Air M2", description="Ультрабук с процессором Apple M2 и 8 ГБ оперативной памяти", price=99990, stock=20, category_id=2),
        Product(name="Dell XPS 13", description="Ультрабук с процессором Intel Core i7 и 16 ГБ оперативной памяти", price=109990, stock=15, category_id=2),
        Product(name="Huawei MateBook X Pro", description="Ультрабук с процессором Intel Core i7 и 16 ГБ оперативной памяти", price=89990, stock=10, category_id=2),
        Product(name="ASUS ZenBook 14", description="Ультрабук с процессором Intel Core i5 и 8 ГБ оперативной памяти", price=69990, stock=18, category_id=2),
        
        # Android-смартфоны
        Product(name="Samsung Galaxy S23 Ultra", description="Флагманский смартфон с 6.8-дюймовым экраном и камерой 200 МП", price=99990, stock=25, category_id=14),
        Product(name="Google Pixel 7 Pro", description="Смартфон с 6.7-дюймовым экраном и одной из лучших камер", price=79990, stock=15, category_id=14),
        Product(name="Xiaomi 13 Pro", description="Флагманский смартфон с 6.73-дюймовым экраном и процессором Snapdragon 8 Gen 2", price=69990, stock=20, category_id=14),
        Product(name="OnePlus 11", description="Производительный смартфон с 6.7-дюймовым экраном и быстрой зарядкой 100 Вт", price=59990, stock=18, category_id=14),
        
        # iPhone
        Product(name="Apple iPhone 14 Pro Max", description="Флагманский смартфон с 6.7-дюймовым экраном и системой Dynamic Island", price=109990, stock=30, category_id=15),
        Product(name="Apple iPhone 14 Pro", description="Флагманский смартфон с 6.1-дюймовым экраном и системой Dynamic Island", price=94990, stock=25, category_id=15),
        Product(name="Apple iPhone 14", description="Смартфон с 6.1-дюймовым экраном и процессором A15 Bionic", price=74990, stock=35, category_id=15),
        Product(name="Apple iPhone 13", description="Смартфон с 6.1-дюймовым экраном и процессором A15 Bionic", price=64990, stock=40, category_id=15),
        
        # OLED-телевизоры
        Product(name="LG OLED65C2", description="65-дюймовый OLED-телевизор с разрешением 4K и поддержкой Dolby Vision", price=169990, stock=8, category_id=27),
        Product(name="Sony XR-65A80K", description="65-дюймовый OLED-телевизор с разрешением 4K и процессором XR", price=179990, stock=6, category_id=27),
        Product(name="Philips 55OLED807", description="55-дюймовый OLED-телевизор с разрешением 4K и системой Ambilight", price=119990, stock=10, category_id=27),
        
        # Беспроводные наушники
        Product(name="Apple AirPods Pro 2", description="Беспроводные наушники с активным шумоподавлением и адаптивным эквалайзером", price=19990, stock=50, category_id=37),
        Product(name="Sony WF-1000XM4", description="Беспроводные наушники с активным шумоподавлением и поддержкой Hi-Res Audio", price=18990, stock=40, category_id=37),
        Product(name="Samsung Galaxy Buds 2 Pro", description="Беспроводные наушники с активным шумоподавлением и поддержкой 24-битного звука", price=14990, stock=45, category_id=37),
        Product(name="Jabra Elite 7 Pro", description="Беспроводные наушники с системой MultiSensor Voice и активным шумоподавлением", price=12990, stock=35, category_id=37)
    ]
    db.session.add_all(products)
    db.session.commit()
    
    # Создаем продажи за последние 12 месяцев
    sales = []
    now = datetime.utcnow()
    
    # Сезонные тренды для продаж
    # Январь: низкие продажи после праздников
    # Март-апрель: рост продаж весной
    # Август-сентябрь: школьный сезон, рост продаж техники
    # Ноябрь-декабрь: предновогодние продажи, пик
    
    seasons = {
        1: 0.6,   # Январь - низкий сезон
        2: 0.7,   # Февраль
        3: 0.8,   # Март
        4: 0.9,   # Апрель
        5: 0.8,   # Май
        6: 0.7,   # Июнь
        7: 0.8,   # Июль
        8: 1.0,   # Август - школьный сезон
        9: 1.1,   # Сентябрь - школьный сезон
        10: 0.9,  # Октябрь
        11: 1.2,  # Ноябрь - предновогодний сезон
        12: 1.5   # Декабрь - пик продаж
    }
    
    # Популярность категорий по месяцам
    category_seasonality = {
        # Смартфоны
        14: {  # Android-смартфоны
            9: 1.3,  # Рост в сентябре
            10: 1.3  # Рост в октябре
        },
        15: {  # iPhone
            9: 1.5,  # Рост в сентябре (новые iPhone)
            10: 1.5  # Рост в октябре (новые iPhone)
        },
        # Телевизоры 
        27: {  # OLED-телевизоры
            12: 1.8,  # Пик в декабре (праздники)
            11: 1.4   # Пик в ноябре (Черная пятница)
        }
    }
    
    for product in products:
        # Определяем базовую популярность продукта
        if product.price > 100000:
            popularity = random.uniform(0.5, 0.8)  # Дорогие товары менее популярны
        elif product.price > 50000:
            popularity = random.uniform(0.7, 1.0)  # Средние по цене
        elif product.price > 10000:
            popularity = random.uniform(0.9, 1.2)  # Доступные
        else:
            popularity = random.uniform(1.1, 1.5)  # Наиболее доступные
        
        # Генерируем продажи за каждый месяц
        for month_offset in range(12):
            sale_date = now - timedelta(days=30 * month_offset)
            month = sale_date.month
            
            # Базовое количество продаж в этом месяце
            monthly_sales_count = int(popularity * 10 * seasons[month])
            
            # Корректировка для сезонных категорий
            category_id = product.category_id
            if category_id in category_seasonality and month in category_seasonality[category_id]:
                monthly_sales_count = int(monthly_sales_count * category_seasonality[category_id][month])
            
            # Генерируем указанное количество продаж для этого месяца
            for _ in range(monthly_sales_count):
                # Генерируем случайную дату в пределах текущего месяца
                day = random.randint(1, 28)
                sale_date = datetime(sale_date.year, sale_date.month, day)
                
                # Выбираем случайный магазин
                store = random.choice(stores)
                
                # Скидки увеличиваются в сезонные периоды
                if month in [11, 12]:  # Ноябрь, декабрь - период скидок
                    discount = random.uniform(0.1, 0.3)
                else:
                    discount = random.uniform(0, 0.15)
                
                # Создаем продажу
                sales.append(
                    Sale(
                        product_id=product.id,
                        store_id=store.id,
                        quantity=random.randint(1, 3),  # Обычно покупают 1-3 единицы
                        price=product.price * (1 - discount),
                        date=sale_date
                    )
                )
    
    # Добавляем продажи партиями, чтобы не перегружать БД
    batch_size = 1000
    for i in range(0, len(sales), batch_size):
        db.session.add_all(sales[i:i+batch_size])
        db.session.commit()
    
    print(f"Создано {len(cities)} городов, {len(stores)} магазинов, {len(groups)} групп, {len(categories)} категорий, {len(products)} товаров и {len(sales)} продаж.")