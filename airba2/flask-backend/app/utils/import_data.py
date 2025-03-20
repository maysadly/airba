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
        
        # Проверка на очевидно текстовое значение (игнорируем, если в строке больше 3 букв и нет цифр)
        alpha_count = sum(c.isalpha() for c in value)
        digit_count = sum(c.isdigit() for c in value)
        
        if alpha_count > 3 and digit_count == 0:
            return default
        
        # Попробуем преобразовать строку в число
        try:
            # Замена запятой на точку для поддержки разных форматов чисел
            value = value.replace(',', '.')
            return float(value)
        except ValueError:
            # Выводим предупреждение только если строка похожа на число
            if digit_count > 0:
                logger.warning(f"Не удалось преобразовать '{value}' в число, использую {default}")
            return default
    
    return default

def find_price_columns(df):
    """Находит колонки с ценами в DataFrame"""
    price_columns = []
    exclude_patterns = ['скидк', 'discount', 'trade', 'акци', 'каскад', 'подар', 'менеджер', 'директор', 'другое', 'основани']
    
    # Сначала проверяем наиболее вероятные колонки с ценами
    priority_patterns = ['price', 'цена', 'стоимость', 'сумма', 'руб', 'с ндс', 'без ндс', 'gs, с ндс', 'ns, с ндс']
    
    # Проверка первых нескольких строк, чтобы определить, содержит ли колонка числа
    sample_rows = min(5, len(df))
    
    for col in df.columns:
        col_lower = str(col).lower()
        
        # Пропускаем колонки, которые вероятно содержат текстовые описания скидок
        if any(pattern in col_lower for pattern in exclude_patterns):
            continue
            
        # Сначала проверяем приоритетные шаблоны
        if any(pattern in col_lower for pattern in priority_patterns):
            # Проверяем, содержит ли колонка числа в первых строках
            has_numbers = False
            for i in range(sample_rows):
                if i < len(df):
                    val = df.iloc[i][col]
                    if isinstance(val, (int, float)) or (isinstance(val, str) and any(c.isdigit() for c in val)):
                        has_numbers = True
                        break
            
            if has_numbers:
                price_columns.append(col)
                
    # Если не нашли приоритетные колонки, ищем любые колонки с числовыми данными
    if not price_columns:
        for col in df.columns:
            col_lower = str(col).lower()
            if any(pattern in col_lower for pattern in exclude_patterns):
                continue
                
            # Проверяем, содержит ли колонка числа в большинстве строк
            numeric_count = 0
            for i in range(sample_rows):
                if i < len(df):
                    val = df.iloc[i][col]
                    if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '', 1).replace(',', '', 1).isdigit()):
                        numeric_count += 1
                        
            if numeric_count >= sample_rows // 2:
                price_columns.append(col)
    
    logger.info(f"Найдены колонки с ценами: {price_columns}")
    return price_columns

def find_product_column(df):
    """Находит колонку с названиями товаров"""
    for col in df.columns:
        col_lower = str(col).lower()
        if ('това' in col_lower or 'product' in col_lower or 'model' in col_lower or 
            'наименование изд' in col_lower or 'наименование тов' in col_lower):
            logger.info(f"Найдена колонка с товарами: {col}")
            return col
    
    # Если не нашли, берем первую колонку
    logger.warning(f"Не найдена колонка с товарами, использую первую колонку: {df.columns[0]}")
    return df.columns[0]

def find_store_column(df):
    """Находит колонку с названиями магазинов"""
    for col in df.columns:
        col_lower = str(col).lower()
        if ('магаз' in col_lower or 'store' in col_lower or 'shop' in col_lower or 
            'точка продаж' in col_lower or 'офис' in col_lower):
            logger.info(f"Найдена колонка с магазинами: {col}")
            return col
    
    # Если не нашли, возвращаем None
    logger.warning("Не найдена колонка с магазинами")
    return None

def find_quantity_column(df):
    """Находит колонку с количеством"""
    for col in df.columns:
        col_lower = str(col).lower()
        if ('quant' in col_lower or 'кол' in col_lower or 'шт' in col_lower or 
            'колич' in col_lower or 'count' in col_lower):
            logger.info(f"Найдена колонка с количеством: {col}")
            return col
    
    # Если не нашли, возвращаем None
    logger.warning("Не найдена колонка с количеством")
    return None

def find_date_column(df):
    """Находит колонку с датой"""
    for col in df.columns:
        col_lower = str(col).lower()
        if ('дата' in col_lower or 'date' in col_lower or 'time' in col_lower or 
            'время' in col_lower or 'день' in col_lower):
            logger.info(f"Найдена колонка с датой: {col}")
            return col
    
    # Если не нашли, возвращаем None
    logger.warning("Не найдена колонка с датой")
    return None

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
        logger.info(f"Колонки в файле: {df.columns.tolist()}")
        
        # Находим нужные колонки
        city_column = None
        store_column = None
        address_column = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'город' in col_lower or 'city' in col_lower:
                city_column = col
            elif 'магазин' in col_lower or 'store' in col_lower:
                store_column = col
            elif 'адрес' in col_lower or 'address' in col_lower:
                address_column = col
        
        # Если нужные колонки не найдены, используем значения по умолчанию
        if not city_column:
            city_column = 'Наименование города'
            logger.warning(f"Колонка с городами не найдена, использую '{city_column}'")
        
        if not store_column:
            store_column = 'Наименование магазина'
            logger.warning(f"Колонка с магазинами не найдена, использую '{store_column}'")
        
        if not address_column:
            address_column = 'Адрес магазина'
            logger.warning(f"Колонка с адресами не найдена, использую '{address_column}'")
        
        # Сначала создаем все города и коммитим их
        cities_dict = {}
        for idx, row in df.iterrows():
            city_name = clean_string(handle_null(row.get(city_column)))
            if not city_name:
                continue
                
            # Добавляем город только если его еще нет в словаре
            if city_name not in cities_dict:
                region = clean_string(handle_null(row.get('Направление ПВЗ (регион)', '')))
                
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
                
            store_name = clean_string(handle_null(row.get(store_column)))
            if not store_name:
                continue
                
            address = clean_string(handle_null(row.get(address_column)))
            
            # Получаем город для магазина
            city_name = clean_string(handle_null(row.get(city_column)))
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
                logger.info(f"Обработано {idx}/{len(df)} строк данных о магазинах")
        
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
                # Сначала проверим первые 5 строк файла чтобы узнать имена колонок
                sample_df = pd.read_csv(file_path, encoding=encoding, nrows=5)
                logger.info(f"Колонки в файле: {sample_df.columns.tolist()}")
                
                # Проверим, есть ли нужные колонки
                group_column = None
                category_column = None
                model_column = None
                quantity_column = None
                
                for col in sample_df.columns:
                    col_lower = str(col).lower()
                    if 'group' in col_lower or 'групп' in col_lower:
                        group_column = col
                    elif 'categ' in col_lower or 'категор' in col_lower:
                        category_column = col
                    elif 'model' in col_lower or 'модель' in col_lower:
                        model_column = col
                    elif 'quant' in col_lower or 'кол' in col_lower:
                        quantity_column = col
                
                if not group_column:
                    group_column = 'group'
                    logger.warning(f"Колонка с группами не найдена, использую '{group_column}'")
                
                if not category_column:
                    category_column = 'categ'
                    logger.warning(f"Колонка с категориями не найдена, использую '{category_column}'")
                
                if not model_column:
                    model_column = 'Model'
                    logger.warning(f"Колонка с моделями не найдена, использую '{model_column}'")
                
                if not quantity_column:
                    quantity_column = 'quant'
                    logger.warning(f"Колонка с количеством не найдена, использую '{quantity_column}'")
                
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
            for group_name in chunk[group_column].dropna().unique():
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
            valid_data = chunk.dropna(subset=[group_column, category_column])
            
            for _, row in valid_data.iterrows():
                group_name = clean_string(handle_null(row[group_column]))
                category_name = clean_string(handle_null(row[category_column]))
                
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
            valid_data = chunk.dropna(subset=[group_column, category_column, model_column])
            
            # Получаем существующие товары для этого чанка
            models = [clean_string(handle_null(m)) for m in valid_data[model_column] if not pd.isna(m)]
            existing_products = {}
            
            # Оптимизация: загружаем только товары, которые есть в этом чанке
            if models:
                for product in Product.query.filter(Product.name.in_(models)).all():
                    existing_products[product.name] = product.id
            
            # Создаем новые товары
            batch_products = []
            batch_size = 1000
            
            for _, row in valid_data.iterrows():
                group_name = clean_string(handle_null(row[group_column]))
                category_name = clean_string(handle_null(row[category_column]))
                model = clean_string(handle_null(row[model_column]))
                
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
                
                quant = parse_float(row.get(quantity_column, 0), default=0)
                
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
        
        # Читаем Excel файл и анализируем колонки
        logger.info(f"Чтение файла {file_path}...")
        
        # Попробуем несколько вариантов для надежности
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            logger.warning(f"Ошибка при чтении Excel файла: {str(e)}")
            try:
                # Попробуем с явным указанием engine
                df = pd.read_excel(file_path, engine='openpyxl')
            except Exception as e2:
                logger.error(f"Не удалось прочитать файл при второй попытке: {str(e2)}")
                raise
        
        logger.info(f"Прочитано {len(df)} строк из файла")
        logger.info(f"Первые несколько строк файла:")
        try:
            logger.info(df.head(3).to_string())
        except:
            pass
        
        logger.info(f"Колонки в файле: {df.columns.tolist()}")
        
        # Определяем колонки для работы
        price_columns = find_price_columns(df)
        product_column = find_product_column(df)
        store_column = find_store_column(df)
        quantity_column = find_quantity_column(df)
        date_column = find_date_column(df)
        
        logger.info(f"Найдены колонки для импорта:")
        logger.info(f"- Товары: {product_column}")
        logger.info(f"- Магазины: {store_column}")
        logger.info(f"- Количество: {quantity_column}")
        logger.info(f"- Дата: {date_column}")
        logger.info(f"- Цены: {price_columns}")
        
        # Если мы не нашли какие-то колонки, используем фиксированные имена
        if not product_column:
            product_column = 'Товар'
            logger.info(f"Используем фиксированную колонку для товаров: {product_column}")
        
        if not store_column:
            store_column = 'Наименование магазина'
            logger.info(f"Используем фиксированную колонку для магазинов: {store_column}")
        
        if not quantity_column:
            quantity_column = 'Quantity'
            logger.info(f"Используем фиксированную колонку для количества: {quantity_column}")
        
        if not date_column:
            date_column = 'Дата'
            logger.info(f"Используем фиксированную колонку для даты: {date_column}")
        
        if not price_columns:
            price_columns = ['Price', 'NS, с НДС', 'GS, с НДС']
            logger.info(f"Используем фиксированные колонки для цен: {price_columns}")
        
        # Загружаем все магазины и товары в память для быстрого поиска
        logger.info("Загрузка магазинов из базы данных...")
        store_dict = {}
        stores = Store.query.all()
        for store in stores:
            store_dict[store.name] = store.id
            # Добавим более короткие версии имени для лучшего матчинга
            short_name = store.name.split()[0] if ' ' in store.name else store.name
            if short_name and len(short_name) > 3 and short_name not in store_dict:
                store_dict[short_name] = store.id
        
        logger.info("Загрузка товаров из базы данных...")
        product_dict = {}
        products = Product.query.all()
        for product in products:
            product_dict[product.name] = (product.id, product.price)
        
        logger.info(f"Загружено {len(store_dict)} магазинов и {len(product_dict)} товаров из базы данных")
        
        # Создаем записи о продажах (один проход для простоты)
        batch_size = 5000
        sales_batch = []
        
        for idx, row in df.iterrows():
            if idx > 0 and idx % 1000 == 0:
                logger.info(f"Обработано {idx}/{len(df)} строк данных о продажах. Создано {sales_counter} записей о продажах")
            
            # Получаем название магазина и товара
            store_name = clean_string(handle_null(row.get(store_column)))
            item_name = clean_string(handle_null(row.get(product_column)))
            
            if not store_name or not item_name:
                continue
            
            # Находим ID магазина с более гибким поиском
            store_id = None
            if store_name in store_dict:
                store_id = store_dict[store_name]
            else:
                # Попробуем поиск с нечеткими совпадениями
                for stored_name, id in store_dict.items():
                    if store_name in stored_name or stored_name in store_name:
                        store_id = id
                        # Добавляем в словарь для будущих запросов
                        store_dict[store_name] = id
                        break
            
            if not store_id:
                if store_name not in missing_stores:
                    missing_stores.add(store_name)
                    logger.warning(f"Магазин не найден: {store_name}")
                continue
            
            # Находим ID товара с более гибким поиском
            product_id = None
            if item_name in product_dict:
                product_id, _ = product_dict[item_name]
            else:
                # Попробуем более гибкий поиск
                for product_name, (pid, _) in product_dict.items():
                    if item_name in product_name or product_name in item_name:
                        product_id = pid
                        # Добавляем в словарь для будущих запросов
                        product_dict[item_name] = (pid, 0)
                        break
            
            if not product_id:
                if item_name not in missing_products:
                    missing_products.add(item_name)
                    logger.warning(f"Товар не найден: {item_name}")
                continue
            
            # Получаем дату
            date_str = row.get(date_column)
            if pd.isna(date_str):
                date = datetime.now()
            else:
                try:
                    if isinstance(date_str, str):
                        date = datetime.strptime(date_str, '%Y-%m-%d')
                    else:
                        date = pd.to_datetime(date_str)
                except Exception as e:
                    logger.debug(f"Ошибка при преобразовании даты '{date_str}': {str(e)}")
                    date = datetime.now()
            
            # Получаем количество с дефолтным значением 1
            quantity = parse_float(row.get(quantity_column), default=1)
            if quantity <= 0:
                quantity = 1
            
            # Получаем цену, сначала из файла, затем из базы
            price = None
            for price_col in price_columns:
                if price_col in df.columns:
                    price_val = parse_float(row.get(price_col))
                    if price_val and price_val > 0:
                        price = price_val
                        break
            
            # Если не нашли цену в файле, берем из базы данных
            if not price or price <= 0:
                product = Product.query.get(product_id)
                if product and product.price > 0:
                    price = product.price
                else:
                    # Используем среднюю цену или фиксированное значение
                    avg_price = db.session.query(db.func.avg(Product.price)).filter(Product.price > 0).scalar()
                    price = avg_price if avg_price and avg_price > 0 else 1000
                    logger.debug(f"Для товара {item_name} используется средняя цена {price}")
            
            # Создаем новую продажу
            sale = Sale(
                product_id=product_id,
                store_id=store_id,
                quantity=quantity,
                price=price,
                date=date
            )
            sales_batch.append(sale)
            sales_counter += 1
            
            # Периодически сохраняем пакеты продаж
            if len(sales_batch) >= batch_size:
                db.session.bulk_save_objects(sales_batch)
                db.session.commit()
                logger.info(f"Сохранено {sales_counter} продаж")
                sales_batch = []
        
        # Сохраняем оставшиеся продажи
        if sales_batch:
            db.session.bulk_save_objects(sales_batch)
            db.session.commit()
            logger.info(f"Сохранено итоговых {sales_counter} продаж")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Успешно импортированы данные о продажах. Создано {sales_counter} записей о продажах за {elapsed_time:.2f} секунд")
        
        if missing_stores:
            logger.warning(f"Не найдено {len(missing_stores)} магазинов: {', '.join(list(missing_stores)[:5])}...")
        
        if missing_products:
            logger.warning(f"Не найдено {len(missing_products)} товаров: {', '.join(list(missing_products)[:5])}...")
        
        # Обновляем цены товаров на основе импортированных продаж
        if sales_counter > 0:
            logger.info("Обновление цен товаров на основе импортированных продаж...")
            products_with_zero_price = Product.query.filter(Product.price == 0).count()
            
            if products_with_zero_price > 0:
                # Найдем средние цены из продаж
                price_subquery = db.session.query(
                    Sale.product_id,
                    db.func.avg(Sale.price).label('avg_price')
                ).group_by(Sale.product_id).subquery()
                
                # Обновим товары с нулевыми ценами
                update_count = db.session.query(Product).filter(
                    Product.price == 0,
                    Product.id == price_subquery.c.product_id
                ).update({
                    Product.price: price_subquery.c.avg_price
                }, synchronize_session=False)
                
                db.session.commit()
                logger.info(f"Обновлены цены для {update_count} товаров")
        
        return sales_counter
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при импорте данных о продажах: {str(e)}", exc_info=True)
        raise

def update_zero_prices(sales_path):
    """Обновляет только цены товаров с нулевой ценой"""
    start_time = time.time()
    logger.info(f"Начало обновления цен товаров из {sales_path}")
    
    price_updated = 0
    
    try:
        # Проверяем существование файла
        if not os.path.exists(sales_path):
            logger.error(f"Файл не найден: {sales_path}")
            return
        
        # Читаем Excel файл и находим нужные колонки
        logger.info(f"Чтение файла {sales_path}...")
        df = pd.read_excel(sales_path)
        logger.info(f"Прочитано {len(df)} строк из файла")
        logger.info(f"Колонки в файле: {df.columns.tolist()}")
        
        # Определяем колонки для работы
        price_columns = find_price_columns(df)
        product_column = find_product_column(df)
        
        # Получаем товары с нулевой ценой
        zero_price_products = {p.name: p.id for p in Product.query.filter(Product.price == 0).all()}
        logger.info(f"Найдено {len(zero_price_products)} товаров с нулевой ценой")
        
        if not zero_price_products:
            logger.info("Нет товаров с нулевой ценой для обновления")
            return
        
        # Словарь для накопления цен товаров
        product_prices = {}  # {product_id: [цена1, цена2, ...]}
        
        # Собираем цены из файла
        for idx, row in df.iterrows():
            if idx > 0 and idx % 10000 == 0:
                logger.info(f"Обработано {idx}/{len(df)} строк")
            
            item_name = clean_string(handle_null(row.get(product_column)))
            
            if not item_name or item_name not in zero_price_products:
                continue
            
            product_id = zero_price_products[item_name]
            
            # Ищем цену в различных колонках
            price = None
            for price_col in price_columns:
                price_val = parse_float(row.get(price_col))
                if price_val and price_val > 0:
                    price = price_val
                    break
            
            # Если нашли цену, добавляем в словарь
            if price and price > 0:
                if product_id not in product_prices:
                    product_prices[product_id] = []
                product_prices[product_id].append(price)
        
        # Обновляем цены товаров
        logger.info(f"Обновление цен для {len(product_prices)} товаров...")
        for product_id, prices in product_prices.items():
            # Используем среднюю цену
            avg_price = sum(prices) / len(prices)
            
            product = Product.query.get(product_id)
            if product and product.price == 0:
                product.price = avg_price
                db.session.add(product)
                price_updated += 1
                
                if price_updated % 1000 == 0:
                    db.session.commit()
                    logger.info(f"Обновлено {price_updated} цен товаров")
        
        # Сохраняем оставшиеся изменения
        if price_updated % 1000 != 0:
            db.session.commit()
            logger.info(f"Обновлено {price_updated} цен товаров")
        
        # Проверяем, сколько товаров осталось с нулевыми ценами
        remaining_zero = db.session.query(db.func.count(Product.id)).filter(Product.price == 0).scalar()
        
        # Если остались товары с нулевыми ценами, устанавливаем им среднюю цену
        if remaining_zero > 0:
            logger.info(f"Осталось товаров с нулевой ценой: {remaining_zero}")
            
            # Найдем среднюю цену из базы
            avg_price = db.session.query(db.func.avg(Product.price)).filter(Product.price > 0).scalar() or 1000
            
            # Применим эту цену к оставшимся товарам
            db.session.query(Product).filter(Product.price == 0).update({Product.price: avg_price})
            db.session.commit()
            
            logger.info(f"Для оставшихся {remaining_zero} товаров установлена средняя цена: {avg_price:.2f}")
            price_updated += remaining_zero
        
        elapsed_time = time.time() - start_time
        logger.info(f"Успешно обновлены цены {price_updated} товаров за {elapsed_time:.2f} секунд")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при обновлении цен товаров: {str(e)}", exc_info=True)
        raise

def import_only_prices_and_sales():
    """Импортирует только цены товаров и данные о продажах"""
    total_start_time = time.time()
    logger.info("=== НАЧАЛО ИМПОРТА ЦЕН И ПРОДАЖ ===")
    
    # Пути к файлам
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    logger.info(f"Директория с данными: {base_dir}")
    
    sales_path = os.path.join(base_dir, 'sales', 'sales22-1.xlsx')
    
    # Проверяем существование файла с продажами
    if os.path.exists(sales_path):
        logger.info(f"Файл найден: {sales_path}")
    else:
        logger.error(f"Файл не найден: {sales_path} - данные о продажах не будут импортированы")
        return
    
    try:
        # Получаем количество товаров и продаж до импорта
        products_count = db.session.query(db.func.count(Product.id)).scalar()
        sales_count = db.session.query(db.func.count(Sale.id)).scalar()
        zero_price_count = db.session.query(db.func.count(Product.id)).filter(Product.price == 0).scalar()
        
        logger.info(f"Текущее состояние БД: {products_count} товаров, {sales_count} продаж, {zero_price_count} товаров с нулевой ценой")
        
        if zero_price_count > 0:
            # Обновляем цены товаров
            logger.info(f"Обновление цен для {zero_price_count} товаров...")
            update_zero_prices(sales_path)
        else:
            logger.info("Все товары имеют ненулевые цены")
        
        # ИЗМЕНЕНИЕ: Всегда импортируем продажи независимо от наличия в базе
        logger.info("Форсированный импорт данных о продажах...")
        
        # Если есть продажи, удаляем их перед новым импортом
        if sales_count > 0:
            logger.info(f"Удаление существующих {sales_count} записей о продажах...")
            db.session.query(Sale).delete()
            db.session.commit()
        
        # Импортируем продажи
        import_sales(sales_path)
        
        total_elapsed_time = time.time() - total_start_time
        logger.info(f"=== ИМПОРТ ЦЕН И ПРОДАЖ ЗАВЕРШЕН УСПЕШНО за {total_elapsed_time:.2f} секунд ===")
    
    except Exception as e:
        logger.error(f"=== ИМПОРТ ЦЕН И ПРОДАЖ ЗАВЕРШЕН С ОШИБКОЙ: {str(e)} ===", exc_info=True)
        raise

def import_all_data(limit_rows=None):
    """Импортирует все данные из файлов"""
    total_start_time = time.time()
    if limit_rows:
        logger.info(f"=== НАЧАЛО ЧАСТИЧНОГО ИМПОРТА ДАННЫХ (ограничение: {limit_rows} строк) ===")
    else:
        logger.info("=== НАЧАЛО ПОЛНОГО ИМПОРТА ДАННЫХ ===")
    
    # Проверяем директорию с данными
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
    logger.info(f"Директория с данными: {base_dir}")
    
    # Проверяем наличие всех необходимых файлов
    store_info_path = os.path.join(base_dir, 'info', 'store_info.xlsx')
    products_path = os.path.join(base_dir, 'stock', "Stock'22 (1).csv")
    sales_path = os.path.join(base_dir, 'sales', 'sales22-1.xlsx')
    
    files_exist = True
    for path in [store_info_path, products_path, sales_path]:
        if os.path.exists(path):
            logger.info(f"Файл найден: {path}")
        else:
            logger.warning(f"Файл не найден: {path}")
            if path != sales_path:  # Продажи не обязательны
                files_exist = False
    
    if not files_exist:
        logger.error("Не все необходимые файлы найдены. Импорт прерван.")
        return
    
    try:
        # Шаг 1: Импорт магазинов
        logger.info(f"Начало импорта данных о магазинах из {store_info_path}")
        import_store_info(store_info_path)
        
        # Шаг 2: Импорт категорий и товаров
        logger.info(f"Начало импорта категорий и товаров из {products_path}")
        import_product_categories(products_path)
        
        # Шаг 3: Импорт продаж
        logger.info(f"Начало импорта данных о продажах из {sales_path}")
        import_sales(sales_path)
        
        total_elapsed_time = time.time() - total_start_time
        logger.info(f"=== ИМПОРТ ДАННЫХ ЗАВЕРШЕН УСПЕШНО за {total_elapsed_time:.2f} секунд ===")
        
    except Exception as e:
        logger.error(f"=== ИМПОРТ ДАННЫХ ЗАВЕРШЕН С ОШИБКОЙ: {str(e)} ===", exc_info=True)
        raise