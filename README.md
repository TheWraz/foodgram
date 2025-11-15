# Foodgram

## Описание проекта

Foodgram - это веб-приложение для публикации рецептов. Пользователи могут создавать свои рецепты, добавлять их в избранное, подписываться на других авторов и формировать список покупок для выбранных рецептов.

### Основные возможности:

- Создание и редактирование рецептов
- Добавление рецептов в избранное
- Подписка на авторов
- Формирование списка покупок
- Скачивание списка покупок в формате TXT
- Генерация коротких ссылок на рецепты

### Стек технологий

#python #JSON #YAML #Django #React #API #Docker #Nginx #PostgreSQL #Gunicorn #JWT #Postman

## Как запустить проект:

### Предварительные требования:
- Docker
- Docker Compose

### 1. Клонирование репозитория:
```
git clone https://github.com/TheWraz/foodgram
cd foodgram
```

### 2. Настройка переменных окружения:
Создайте файл `.env` в корневой папке:
```env
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_HOST=db
DB_PORT=5433

SECRET_KEY=your-django-secret-key
DEBUG=False  # True для разработки, False для продакшена
ALLOWED_HOSTS=localhost,127.0.0.1
USE_SQLITE=False  # False для использования PostgreSQL
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
```

Замените your-django-secret-key-here на свой безопасный ключ:
```
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 3. Запуск приложения:
В корневой папке выполнить:
```
docker-compose up -d --build
```
Ингредиенты автоматически загружаются из `data/ingredients.csv` при первом запуске.

### Доступ к приложению
После успешного запуска приложение будет доступно по адресам:

- Основное приложение: http://localhost:8001/
- API: http://localhost:8001/api/
- Админка: http://localhost:8001/admin/

### Остановка приложения:
```
docker-compose down
```

## Автор 

- Автор: Wraz - Backend разработка
- Адрес сервера: foodgramwraz.duckdns.org