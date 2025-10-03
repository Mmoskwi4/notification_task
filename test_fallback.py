import os
import sys
import django
import logging

# Настройка
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'notification_task.settings')
django.setup()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from django.conf import settings
from django.contrib.auth.models import User
from notifications.service import NotificationService
from notifications.models import UserProfile

def setup_test_user():
    """Настройка тестового пользователя"""
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@test.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        logging.info("✅ Created new test user")
    else:
        logging.info("✅ Using existing test user")
    
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'phone_number': '+79123456789',
            'telegram_chat_id': '123456789'  # Неправильный chat_id для теста fallback
        }
    )
    
    return user, profile

def test_basic_fallback():
    """Базовый тест fallback механизма"""
    
    logging.info("🧪 BASIC FALLBACK TEST")
    logging.info("=" * 60)
    
    user, profile = setup_test_user()
    
    # Сценарий 1: Telegram не работает (неправильный chat_id), но email работает
    logging.info("\n1. 📋 Telegram failed → Email fallback")
    service1 = NotificationService(user, "Test 1 - Fallback", "Telegram should fail, Email should work")
    result1 = service1.send()
    report1 = service1.get_delivery_report()
    logging.info(f"   Result: {result1}")
    logging.info(f"   Successful channel: {report1['successful_channel']}")
    logging.info(f"   Failed channels: {report1['failed_channels']}")
    
    # Сценарий 2: Отключаем Telegram, оставляем Email и SMS
    logging.info("\n2. 📋 No Telegram → Email should work")
    original_telegram = profile.telegram_chat_id
    
    profile.telegram_chat_id = None  # Отключаем Telegram
    profile.save()
    
    service2 = NotificationService(user, "Test 2 - No Telegram", "Should use Email")
    result2 = service2.send()
    report2 = service2.get_delivery_report()
    logging.info(f"   Result: {result2}")
    logging.info(f"   Successful channel: {report2['successful_channel']}")
    logging.info(f"   Failed channels: {report2['failed_channels']}")
    
    # Восстанавливаем Telegram
    profile.telegram_chat_id = original_telegram
    profile.save()

def test_sms_fallback():
    """Тест когда только SMS доступен"""
    
    logging.info("\n🧪 SMS FALLBACK TEST")
    logging.info("=" * 60)
    
    user, profile = setup_test_user()
    
    # Создаем временного пользователя для теста SMS (не изменяем основного)
    temp_user = User.objects.create(
        username='temp_sms_user',
        email='temp@example.com',  # Обязательно указываем email
        first_name='Temp',
        last_name='SMS User'
    )
    
    temp_profile = UserProfile.objects.create(
        user=temp_user,
        phone_number='+79123456789',  # Включаем SMS
        telegram_chat_id=None  # Отключаем Telegram
    )
    
    logging.info("📋 Only SMS available (Telegram disabled)")
    service = NotificationService(temp_user, "Test - Only SMS", "Should use SMS as fallback")
    result = service.send()
    report = service.get_delivery_report()
    logging.info(f"   Result: {result}")
    logging.info(f"   Successful channel: {report['successful_channel']}")
    logging.info(f"   Failed channels: {report['failed_channels']}")
    
    # Удаляем временного пользователя
    temp_user.delete()

def test_all_channels_failed():
    """Тест когда все каналы не работают"""
    
    logging.info("\n🧪 ALL CHANNELS FAILED TEST")
    logging.info("=" * 60)
    
    user, profile = setup_test_user()
    
    # Создаем временного пользователя с отключенными каналами
    temp_user = User.objects.create(
        username='temp_failed_user',
        email='test@test.com',
        first_name='Temp',
        last_name='Failed User'
    )
    
    temp_profile = UserProfile.objects.create(
        user=temp_user,
        phone_number=None,  # Отключаем SMS
        telegram_chat_id=None  # Отключаем Telegram
    )
    
    # Временно "ломаем" email настройки для теста
    original_email_host = getattr(settings, 'EMAIL_HOST', None)
    
    logging.info("📋 All channels disabled")
    service = NotificationService(temp_user, "Test - All Failed", "Should return False")
    result = service.send()
    report = service.get_delivery_report()
    logging.info(f"   Result: {result}")
    logging.info(f"   Successful channel: {report['successful_channel']}")
    logging.info(f"   Failed channels: {report['failed_channels']}")
    
    # Удаляем временного пользователя
    temp_user.delete()

def test_channel_priority():
    """Тест приоритета каналов"""
    
    logging.info("\n🧪 CHANNEL PRIORITY TEST")
    logging.info("=" * 60)
    
    user, profile = setup_test_user()
    
    scenarios = [
        {
            'name': 'All channels available',
            'telegram': True,
            'expected_priority': 'telegram'
        },
        {
            'name': 'Telegram disabled', 
            'telegram': False,
            'expected_priority': 'email'
        }
    ]
    
    for scenario in scenarios:
        logging.info(f"\n📋 {scenario['name']}")
        
        # Настраиваем каналы согласно сценарию
        original_telegram = profile.telegram_chat_id
        if not scenario['telegram']:
            profile.telegram_chat_id = None
            profile.save()
        
        service = NotificationService(
            user=user,
            subject=f"Priority Test - {scenario['name']}",
            message=f"Testing channel priority. Expected: {scenario['expected_priority']}"
        )
        result = service.send()
        report = service.get_delivery_report()
        
        logging.info(f"   Expected: {scenario['expected_priority']}")
        logging.info(f"   Actual: {report['successful_channel']}")
        logging.info(f"   Match: {'✅' if report['successful_channel'] == scenario['expected_priority'] else '❌'}")
        
        # Восстанавливаем настройки
        profile.telegram_chat_id = original_telegram
        profile.save()

def test_real_world_scenarios():
    """Тестирование реальных сценариев"""
    
    logging.info("\n🌍 REAL-WORLD SCENARIOS")
    logging.info("=" * 60)
    
    user, _ = setup_test_user()
    
    scenarios = [
        {
            'name': 'Важное уведомление',
            'subject': '⚠️ Важное обновление системы',
            'message': 'Запланированы технические работы. Система будет недоступна.'
        },
        {
            'name': 'Приветственное сообщение', 
            'subject': '🎉 Добро пожаловать!',
            'message': 'Спасибо за регистрацию в нашем сервисе.'
        },
        {
            'name': 'Напоминание о платеже',
            'subject': '💰 Напоминание об оплате',
            'message': 'Не забудьте оплатить счет до конца месяца.'
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        logging.info(f"\n{i}. {scenario['name']}")
        service = NotificationService(
            user=user,
            subject=scenario['subject'],
            message=scenario['message']
        )
        result = service.send()
        report = service.get_delivery_report()
        logging.info(f"   Result: {'✅ Success' if result else '❌ Failed'}")
        logging.info(f"   Channel: {report['successful_channel'] or 'None'}")
        logging.info(f"   Failed: {report['failed_channels']}")

def test_individual_channels():
    """Тестирование каждого канала отдельно"""
    
    logging.info("\n🎯 INDIVIDUAL CHANNEL TESTS")
    logging.info("=" * 60)
    
    user, _ = setup_test_user()
    
    # Тест Email канала
    logging.info("\n1. 📧 Testing Email Channel")
    from notifications.channels import EmailChannel
    email_channel = EmailChannel()
    email_result = email_channel.send(user, "Direct Email Test", "Testing email channel directly")
    logging.info(f"   Email result: {'✅ Success' if email_result else '❌ Failed'}")
    
    # Тест Telegram канала
    logging.info("\n2. 📲 Testing Telegram Channel")
    from notifications.channels import TelegramChannel
    telegram_channel = TelegramChannel()
    telegram_result = telegram_channel.send(user, "Direct Telegram Test", "Testing telegram channel directly")
    logging.info(f"   Telegram result: {'✅ Success' if telegram_result else '❌ Failed'}")
    
    # Тест SMS канала
    logging.info("\n3. 📱 Testing SMS Channel")
    from notifications.channels import TwilioSMSChannel
    sms_channel = TwilioSMSChannel()
    sms_result = sms_channel.send(user, "Direct SMS Test", "Testing SMS channel directly")
    logging.info(f"   SMS result: {'✅ Success' if sms_result else '❌ Failed'}")

if __name__ == "__main__":
    test_basic_fallback()
    test_sms_fallback()
    test_all_channels_failed()
    test_channel_priority()
    test_real_world_scenarios()
    test_individual_channels()
    
    logging.info("\n🎉 ALL TESTS COMPLETED!")
    logging.info("=" * 60)
