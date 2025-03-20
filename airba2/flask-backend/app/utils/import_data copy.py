import os
import pandas as pd
import logging
import time
from datetime import datetime
from flask import current_app
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .. import db
from ..models.catalog import City, Store, CategoryGroup, Category, Product, Sale

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('data_import')

def clean_string(value):
    """Очищает строковые значения от лишних пробелов"""
    if isinstance(value, str):
        return value.strip()
    return value

def handle_null(value, default=""):
    """Обрабатывает пустые значения"""
    if pd.isna(value):
        return default
    return value

def parse_float(value, default=None):
    """Безопасно преобразует значение в float"""
    if pd.isna(value):
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        value = value.strip()
        # Если значение '-' или пустое, вернем None
        if value == '-' or value == '':
            return default
        
        # Попробуем преобразовать строку в число
        try:
            return float(value)
        except ValueError:
            logger.warning(f"Не удалось преобразовать '{value}' в число, использую {default}")
            return default
    
    return default

def import_store_info(file_path):
    """Импортирует информацию о магазинах из Excel файла"""
    start_time = time.time()
    logger.info(f"Начало импорта данных о магазинах из {file_path}")
    
    cities_counter = 0
    stores_counter = 0
    
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            logger.error(f"Файл не найден: {file_path}")
            return
        
        # Читаем Excel файл
        logger.info(f"Чтение файла {file_path}...")
        df = pd.read_excel(file_path)
        logger.info(f"Прочитано {len(df)} строк из файла")
        
        # Сначала создаем все города и коммитим их
        cities_dict = {}
        for idx, row in df.iterrows():
            city_name = clean_string(handle_null(row.get('Наименование города')))
            if not city_name:
                continue
                
            # Добавляем город только если его еще нет в словаре
            if city_name not in cities_dict:
                region = clean_string(handle_null(row.get('Направление ПВЗ (регион)')))
                
                # Проверяем существует ли уже город
                city = City.query.filter_by(name=city_name).first()
                if not city:
                    city = City(name=city_name, region=region)
                    db.session.add(city)
                    cities_counter += 1
                    logger.debug(f"Создан новый город: {city_name}, регион: {region}")
        
        # Коммитим все города перед добавлением магазинов
        if cities_counter > 0:
            logger.info(f"Сохранение {cities_counter} городов...")
            db.session.commit()
            logger.info(f"Сохранено {cities_counter} городов")
        
        # Обновляем словарь городов из базы данных
        cities = City.query.all()
        for city in cities:
            cities_dict[city.name] = city.id
        
        logger.info(f"Загружено {len(cities_dict)} городов из базы данных")
        
        # Теперь добавляем магазины
        for idx, row in df.iterrows():
            if idx > 0 and idx % 100 == 0:
                logger.info(f"Обработано {idx}/{len(df)} строк данных о магазинах")
                
            store_id = row.get('store_id')
            if pd.isna(store_id):
                continue
                
            store_name = clean_string(handle_null(row.get('Наименование магазина')))
            if not store_name:
                continue
                
            address = clean_string(handle_null(row.get('Адрес магазина')))
            
            # Получаем город для магазина
            city_name = clean_string(handle_null(row.get('Наименование города')))
            if not city_name or city_name not in cities_dict:
                logger.warning(f"Город '{city_name}' не найден для магазина '{store_name}', пропуск")
                continue
            
            # Безопасно преобразуем размер магазина
            size_value = row.get('Общая площадь')
            if pd.isna(size_value):
                size_value = row.get('Торговая площадь')
            
            size = parse_float(size_value)  # None, если не удалось преобразовать
            
            # Проверяем, существует ли магазин
            store = Store.query.filter_by(name=store_name).first()
            
            if not store:
                # Создаем новый магазин
                store = Store(
                    name=store_name,
                    address=address,
                    city_id=cities_dict[city_name],
                    size=size,
                    opening_date=datetime.now().date()  # Используем текущую дату, так как в файле нет даты открытия
                )
                db.session.add(store)
                stores_counter += 1
                logger.debug(f"Создан новый магазин: {store_name}, адрес: {address}, город: {city_name}")
            
            # Периодически делаем commit, чтобы не накапливать слишком много изменений
            if stores_counter > 0 and stores_counter % 100 == 0:
                db.session.commit()
                logger.info(f"Сохранено {stores_counter} магазинов")
        
        # Сохраняем изменения
        if stores_counter % 100 != 0:  # Если были несохраненные изменения
            db.session.commit()
            
        elapsed_time = time.time() - start_time
        logger.info(f"Успешно импортированы данные о магазинах. Создано {cities_counter} городов и {stores_counter} магазинов за {elapsed_time:.2f} секунд")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при импорте данных о магазинах: {str(e)}", exc_info=True)
        raise

def import_product_categories(file_path):
    """Импортирует категории и товары из CSV файла запасов"""
    start_time = time.time()
    logger.info(f"Начало импорта категорий и товаров из {file_path}")
    
    groups_counter = 0
    categories_counter = 0
    products_counter = 0
    
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            logger.error(f"Файл не найден: {file_path}")
            return
        
        # Используем чанки для обработки больших файлов
        logger.info(f"Чтение файла {file_path} по частям...")
        
        # Первый проход - обработка групп и категорий
        chunk_size = 100000  # Размер части для обработки
        group_dict = {}
        category_dict = {}
        
        # Попытаемся открыть с различными кодировками
        encodings = ['utf-8', 'latin1', 'cp1251']
        for encoding in encodings:
            try:
                # Используем chunks для обработки по частям
                chunks = pd.read_csv(file_path, encoding=encoding, chunksize=chunk_size)
                break
            except Exception as e:
                logger.warning(f"Не удалось открыть файл с кодировкой {encoding}: {str(e)}")
                if encoding == encodings[-1]:
                    logger.error(f"Не удалось открыть файл ни с одной из кодировок")
                    raise
        
        # Шаг 1: Собираем все уникальные группы
        logger.info("Шаг 1: Обработка групп категорий...")
        chunk_count = 0
        unique_groups = set()
        
        for chunk in chunks:
            chunk_count += 1
            logger.info(f"Обработка части {chunk_count} ({len(chunk)} строк)")
            
            # Собираем уникальные группы из текущего чанка
            for group_name in chunk['group'].dropna().unique():
                group_name = clean_string(handle_null(group_name))
                if group_name and group_name not in unique_groups:
                    unique_groups.add(group_name)
        
        # Проверяем существующие группы в БД и создаем недостающие
        logger.info(f"Найдено {len(unique_groups)} уникальных групп, проверка в БД...")
        existing_groups = {g.name: g.id for g in CategoryGroup.query.all()}
        
        for group_name in unique_groups:
            if group_name not in existing_groups:
                group = CategoryGroup(name=group_name, description=f"Группа категорий {group_name}")
                db.session.add(group)
                groups_counter += 1
        
        # Сохраняем группы в БД
        if groups_counter > 0:
            logger.info(f"Сохранение {groups_counter} новых групп категорий...")
            db.session.commit()
            logger.info(f"Сохранено {groups_counter} групп категорий")
        
        # Обновляем словарь групп
        group_dict = {g.name: g.id for g in CategoryGroup.query.all()}
        logger.info(f"Загружено {len(group_dict)} групп категорий из базы данных")
        
        # Шаг 2: Обработка категорий
        logger.info("Шаг 2: Обработка категорий...")
        # Переоткрываем файл
        chunks = pd.read_csv(file_path, encoding=encoding, chunksize=chunk_size)
        chunk_count = 0
        unique_categories = {}  # формат {(группа, категория): 1}
        
        for chunk in chunks:
            chunk_count += 1
            logger.info(f"Обработка части {chunk_count} ({len(chunk)} строк)")
            
            # Фильтруем только строки с валидными группами и категориями
            valid_data = chunk.dropna(subset=['group', 'categ'])
            
            for _, row in valid_data.iterrows():
                group_name = clean_string(handle_null(row['group']))
                category_name = clean_string(handle_null(row['categ']))
                
                if group_name and category_name and group_name in group_dict:
                    category_key = (group_name, category_name)
                    unique_categories[category_key] = 1
            
            # Чтобы не хранить все категории в памяти, периодически создаем их в БД
            if len(unique_categories) > 10000 or chunk_count % 10 == 0:
                # Получаем существующие категории
                existing_categories = {}
                for category in Category.query.all():
                    group = CategoryGroup.query.get(category.group_id)
                    if group:
                        existing_categories[(group.name, category.name)] = category.id
                
                # Создаем недостающие категории
                new_categories = []
                for (group_name, category_name) in unique_categories:
                    if (group_name, category_name) not in existing_categories:
                        category = Category(
                            name=category_name, 
                            description=f"Категория {category_name}", 
                            group_id=group_dict[group_name]
                        )
                        db.session.add(category)
                        new_categories.append((group_name, category_name))
                        categories_counter += 1
                
                # Сохраняем новые категории
                if new_categories:
                    logger.info(f"Сохранение {len(new_categories)} новых категорий...")
                    db.session.commit()
                    logger.info(f"Сохранено {len(new_categories)} категорий")
                
                # Обновляем словарь категорий
                for category in Category.query.all():
                    group = CategoryGroup.query.get(category.group_id)
                    if group:
                        category_key = f"{group.name}_{category.name}"
                        category_dict[category_key] = category.id
                
                # Очищаем словарь уникальных категорий
                unique_categories = {}
        
        # Обрабатываем оставшиеся категории
        if unique_categories:
            # Получаем существующие категории
            existing_categories = {}
            for category in Category.query.all():
                group = CategoryGroup.query.get(category.group_id)
                if group:
                    existing_categories[(group.name, category.name)] = category.id
            
            # Создаем недостающие категории
            new_categories = []
            for (group_name, category_name) in unique_categories:
                if (group_name, category_name) not in existing_categories:
                    category = Category(
                        name=category_name, 
                        description=f"Категория {category_name}", 
                        group_id=group_dict[group_name]
                    )
                    db.session.add(category)
                    new_categories.append((group_name, category_name))
                    categories_counter += 1
            
            # Сохраняем новые категории
            if new_categories:
                logger.info(f"Сохранение {len(new_categories)} новых категорий...")
                db.session.commit()
                logger.info(f"Сохранено {len(new_categories)} категорий")
        
        # Финальное обновление словаря категорий
        category_dict = {}
        for category in Category.query.all():
            group = CategoryGroup.query.get(category.group_id)
            if group:
                category_key = f"{group.name}_{category.name}"
                category_dict[category_key] = category.id
        
        logger.info(f"Загружено {len(category_dict)} категорий из базы данных")
        
        # Шаг 3: Обработка товаров 
        logger.info("Шаг 3: Обработка товаров...")
        # Переоткрываем файл
        chunks = pd.read_csv(file_path, encoding=encoding, chunksize=chunk_size)
        chunk_count = 0
        
        # Вместо загрузки всех товаров в БД сразу, обрабатываем по частям
        for chunk in chunks:
            chunk_count += 1
            logger.info(f"Обработка части {chunk_count} ({len(chunk)} строк)")
            
            # Фильтруем только строки с валидными группами, категориями и моделями
            valid_data = chunk.dropna(subset=['group', 'categ', 'Model'])
            
            # Получаем существующие товары для этого чанка
            models = [clean_string(handle_null(m)) for m in valid_data['Model'] if not pd.isna(m)]
            existing_products = {}
            
            # Оптимизация: загружаем только товары, которые есть в этом чанке
            if models:
                for product in Product.query.filter(Product.name.in_(models)).all():
                    existing_products[product.name] = product.id
            
            # Создаем новые товары
            batch_products = []
            batch_size = 1000
            
            for _, row in valid_data.iterrows():
                group_name = clean_string(handle_null(row['group']))
                category_name = clean_string(handle_null(row['categ']))
                model = clean_string(handle_null(row['Model']))
                
                if not group_name or not category_name or not model:
                    continue
                
                # Создаем ключ для категории
                category_key = f"{group_name}_{category_name}"
                
                # Пропускаем, если категория не найдена
                if category_key not in category_dict:
                    continue
                
                # Пропускаем, если товар уже существует
                if model in existing_products:
                    continue
                
                quant = parse_float(row['quant'], default=0)
                
                # Создаем новый товар
                product = Product(
                    name=model,
                    description=f"Товар {model}",
                    price=0,  # Временная цена, будет обновлена при импорте продаж
                    stock=quant,
                    category_id=category_dict[category_key]
                )
                db.session.add(product)
                products_counter += 1
                batch_products.append(model)
                
                # Сохраняем пакет товаров
                if len(batch_products) >= batch_size:
                    db.session.commit()
                    logger.info(f"Сохранено {products_counter} товаров (пакет {len(batch_products)})")
                    batch_products = []
            
            # Сохраняем оставшиеся товары в пакете
            if batch_products:
                db.session.commit()
                logger.info(f"Сохранено {products_counter} товаров (последний пакет {len(batch_products)})")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Успешно импортированы категории и товары. Создано {groups_counter} групп, {categories_counter} категорий и {products_counter} товаров за {elapsed_time:.2f} секунд")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при импорте категорий и товаров: {str(e)}", exc_info=True)
        raise

def import_sales(file_path):
    """Импортирует данные о продажах из Excel файла"""
    start_time = time.time()
    logger.info(f"Начало импорта данных о продажах из {file_path}")
    
    sales_counter = 0
    missing_stores = set()
    missing_products = set()
    price_updated = 0
    
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            logger.error(f"Файл не найден: {file_path}")
            return
        
        # Читаем Excel файл
        logger.info(f"Чтение файла {file_path}...")
        df = pd.read_excel(file_path)
        logger.info(f"Прочитано {len(df)} строк из файла")
        
        # Загружаем все магазины и товары в память для быстрого поиска
        store_dict = {}
        stores = Store.query.all()
        for store in stores:
            store_dict[store.name] = store.id
        
        product_dict = {}
        products = Product.query.all()
        for product in products:
            product_dict[product.name] = product.id
        
        logger.info(f"Загружено {len(store_dict)} магазинов и {len(product_dict)} товаров из базы данных")
        
        # Обрабатываем каждую строку файла
        for idx, row in df.iterrows():
            if idx > 0 and idx % 1000 == 0:
                logger.info(f"Обработано {idx}/{len(df)} строк данных о продажах. Создано {sales_counter} записей о продажах")
                
            store_name = clean_string(handle_null(row.get('Наименование магазина')))
            item_name = clean_string(handle_null(row.get('Товар')))
            
            if not store_name or not item_name:
                continue
            
            # Находим ID магазина
            store_id = None
            if store_name in store_dict:
                store_id = store_dict[store_name]
            else:
                if store_name not in missing_stores:
                    missing_stores.add(store_name)
                    logger.warning(f"Магазин не найден: {store_name}")
                continue
            
            # Находим ID товара
            product_id = None
            if item_name in product_dict:
                product_id = product_dict[item_name]
            else:
                # Попробуем найти по части наименования
                product_found = False
                for product_name, pid in product_dict.items():
                    if item_name in product_name or product_name in item_name:
                        product_id = pid
                        product_found = True
                        # Добавляем в словарь для быстрого поиска в будущем
                        product_dict[item_name] = pid
                        break
                
                if not product_found:
                    if item_name not in missing_products:
                        missing_products.add(item_name)
                        logger.warning(f"Товар не найден: {item_name}")
                    continue
            
            # Обновляем цену товара, если она равна 0
            product = Product.query.get(product_id)
            if product and product.price == 0:
                price = parse_float(row.get('Price'))
                if price and price > 0:
                    product.price = price
                    db.session.add(product)
                    price_updated += 1
                    logger.debug(f"Обновлена цена товара {product.name}: {price}")
            
            # Получаем данные о продаже
            date_str = row.get('Дата')
            if pd.isna(date_str):
                date = datetime.now()
            else:
                # Преобразуем дату из строки или из числа Excel
                if isinstance(date_str, str):
                    try:
                        date = datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        date = datetime.now()
                else:
                    try:
                        date = pd.to_datetime(date_str)
                    except:
                        date = datetime.now()
            
            quantity = parse_float(row.get('Quantity'), default=1)
            if quantity <= 0:
                quantity = 1
            
            price = parse_float(row.get('Price'))
            if not price or price <= 0:
                price = parse_float(row.get('NS, с НДС'))
                if not price or price <= 0:
                    price = parse_float(row.get('GS, с НДС'))
                    if not price or price <= 0:
                        logger.warning(f"Не удалось определить цену для {item_name}, пропуск")
                        continue
            
            # Создаем новую продажу
            sale = Sale(
                product_id=product_id,
                store_id=store_id,
                quantity=quantity,
                price=price,
                date=date
            )
            db.session.add(sale)
            sales_counter += 1
            
            # Регулярно делаем промежуточный коммит, чтобы не накапливать слишком много в сессии
            if sales_counter % 10000 == 0:
                db.session.commit()
                logger.info(f"Промежуточное сохранение: импортировано {sales_counter} продаж")
        
        # Сохраняем изменения
        if sales_counter % 10000 != 0:  # Если были несохраненные изменения
            db.session.commit()
            
        elapsed_time = time.time() - start_time
        logger.info(f"Успешно импортированы данные о продажах. Создано {sales_counter} записей о продажах, обновлены цены {price_updated} товаров за {elapsed_time:.2f} секунд")
        
        if missing_stores:
            logger.warning(f"Не найдено {len(missing_stores)} магазинов")
        
        if missing_products:
            logger.warning(f"Не найдено {len(missing_products)} товаров")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при импорте данных о продажах: {str(e)}", exc_info=True)
        raise

def import_all_data():
    """Импортирует все данные из файлов"""
    total_start_time = time.time()
    logger.info("=== НАЧАЛО ПОЛНОГО ИМПОРТА ДАННЫХ ===")
    
    # Пути к файлам
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    logger.info(f"Директория с данными: {base_dir}")
    
    store_info_path = os.path.join(base_dir, 'info', 'store_info.xlsx')
    stock_path = os.path.join(base_dir, 'stock', "Stock'22 (1).csv")
    sales_path = os.path.join(base_dir, 'sales', 'sales22-1.xlsx')
    
    # Проверяем существование файлов
    for path, name in [(store_info_path, "информация о магазинах"), 
                       (stock_path, "данные о запасах"), 
                       (sales_path, "данные о продажах")]:
        if os.path.exists(path):
            logger.info(f"Файл найден: {path}")
        else:
            logger.warning(f"Файл не найден: {path} - {name} не будут импортированы")
    
    try:
        # Импортируем данные в правильном порядке
        if os.path.exists(store_info_path):
            import_store_info(store_info_path)
        else:
            logger.error("Файл с информацией о магазинах отсутствует, импорт невозможен")
            return
        
        if os.path.exists(stock_path):
            import_product_categories(stock_path)
        else:
            logger.error("Файл с данными о запасах отсутствует, импорт товаров невозможен")
            return
        
        if os.path.exists(sales_path):
            import_sales(sales_path)
        else:
            logger.warning("Файл с данными о продажах отсутствует, продажи не будут импортированы")
    
        total_elapsed_time = time.time() - total_start_time
        logger.info(f"=== ИМПОРТ ДАННЫХ ЗАВЕРШЕН УСПЕШНО за {total_elapsed_time:.2f} секунд ===")
    
    except Exception as e:
        logger.error(f"=== ИМПОРТ ДАННЫХ ЗАВЕРШЕН С ОШИБКОЙ: {str(e)} ===", exc_info=True)
        raise
    
    
import_all_data()