# 🔔 Система Уведомлений (Notification System)
Простая и надежная система для отправки уведомлений пользователям через multiple каналов с автоматическим fallback механизмом.

# 🚀 Возможности
📧 Email - отправка через SMTP

📱 SMS - интеграция с Twilio

📲 Telegram - отправка через бота

🔄 Автоматический Fallback - если один канал не сработал, система пробует следующий

⚡ Асинхронная обработка - через Celery и Redis

📊 Мониторинг - отслеживание статуса отправки

# 🛠 Технологии
Python 3.9+

Django 4.2+

Celery - асинхронные задачи

Redis - брокер сообщений

Twilio - SMS рассылки

Telegram Bot API - мессенджер уведомления

# 📦 Установка
1. Клонирование и настройка

``` git clone <repository-url>
cd notification_task
poetry install
```

2. Настройка окружения

    Создайте файл .env в корне проекта:
    - Пример .env лежит к корне проекта (env)


3. Инициализация базы данных

```
python manage.py migrate
python manage.py createsuperuser
```

4. Запуск сервисов
    - Терминал 1 - Redis:
    ```
    redis-server
    ```
    - Терминал 2 - Celery Worker:
    ```
    celery -A notification_task worker --loglevel=info --pool=solo

    ```
    - Терминал 3 - Django Server:
    ```
    python manage.py runserver
    ```


# 🎯 Использование
## Быстрая отправка уведомления
```
    from notifications.tasks import send_notification_task

    # Асинхронная отправка
    send_notification_task.delay(
    user_id=1,
    subject="Важное уведомление", 
    message="Текст вашего сообщения"
    )
```
## Через сервис напрямую
```
from django.contrib.auth.models import User
from notifications.service import NotificationService

user = User.objects.get(id=1)
service = NotificationService(
    user=user,
    subject="Тема сообщения",
    message="Текст сообщения"
)

# Синхронная отправка с fallback
success = service.send()

# Получение отчета
report = service.get_delivery_report()
print(f"Успешно: {report['success']}")
print(f"Канал: {report['successful_channel']}")
print(f"Неудачные каналы: {report['failed_channels']}")
```

# 🔧 Настройка каналов

## Email
Система использует стандартные настройки Django SMTP. Убедитесь, что в .env правильно указаны:

- EMAIL_HOST, EMAIL_PORT

- EMAIL_HOST_USER, EMAIL_HOST_PASSWORD

- Для Gmail используйте App Password

## Telegram
1. Создайте бота через @BotFather

2. Получите токен бота

3. Узнайте ваш Chat ID через @userinfobot

4. Добавьте Chat ID в профиль пользователя:

``` 
from notifications.models import UserProfile

profile = UserProfile.objects.get(user=user)
profile.telegram_chat_id = "ваш_chat_id"
profile.save()
```

## SMS (Twilio)
1. Зарегистрируйтесь на Twilio

2. Получите Account SID и Auth Token

3. Купите номер телефона в Twilio

4. Добавьте номер телефона в профиль пользователя:

```
profile.phone_number = "+79123456789"  # в формате E.164
profile.save()
```

# 📋 Приоритет каналов

Система пытается отправить уведомления в следующем порядке:

1. Telegram 🥇 (быстрый, бесплатный)

2. Email 🥈 (надежный)

3. SMS 🥉 (гарантированная доставка)

Если первый канал не сработал, автоматически пробуется следующий.

# 🧪 Тестирование
```
# Полный тест fallback механизма
python test_fallback.py
```

## Пример тестового сценария

```
from notifications.service import NotificationService

# Создание тестового пользователя
user = User.objects.create_user(
    username='test_user',
    email='test@example.com',
    password='testpass123'
)

# Настройка профиля
profile = UserProfile.objects.create(
    user=user,
    phone_number='+79123456789',
    telegram_chat_id='123456789'
)

# Отправка тестового уведомления
service = NotificationService(
    user=user,
    subject="Тестовое уведомление",
    message="Проверка работы системы"
)
service.send()
```

# 📊 Мониторинг

## Просмотр статуса уведомлений
```
from notifications.models import Notification

# Все уведомления
notifications = Notification.objects.all()

# Статистика
sent_count = Notification.objects.filter(status='sent').count()
failed_count = Notification.objects.filter(status='failed').count()
```

## Логирование
Система детально логирует весь процесс отправки. Логи можно найти в:

Консоли Celery worker

Файле test_results.log (при запуске тестов)



# 🐛 Решение проблем

## Email не отправляется
- Проверьте настройки SMTP в .env

- Для Gmail используйте App Password, не обычный пароль

- Убедитесь, что пользователь имеет email

## Telegram ошибки
- Проверьте правильность Chat ID

- Убедитесь, что бот запущен

- Проверьте токен бота

## SMS не работает
- Проверьте баланс Twilio аккаунта

- Убедитесь в правильности формата номера (+79123456789)

- Проверьте SID и токен Twilio

## Celery задачи не выполняются
- Убедитесь, что Redis запущен

- Проверьте, что Celery worker запущен

- Посмотрите логи Celery для деталей
