import logging
from .channels import EmailChannel, TwilioSMSChannel, TelegramChannel
from .models import Notification

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Сервис для отправки уведомлений с резервными каналами.
    Реализует цепочку ответственности: если один канал не сработал, пробуем следующий.
    """

    def __init__(self, user, subject, message):
        self.user = user
        self.subject = subject
        self.message = message
        # ПОРЯДОК ВАЖЕН: определяет приоритет каналов
        self.channels = [
            TelegramChannel(),    # Первый приоритет - быстрый и бесплатный
            EmailChannel(),       # Второй приоритет - надежный
            TwilioSMSChannel(),   # Третий приоритет - гарантированная доставка
        ]
        self.last_successful_channel = None
        self.failed_channels = []  # Инициализируем список для неудачных попыток

    def send(self) -> bool:
        """
        Пытается отправить уведомление через доступные каналы по цепочке.
        Возвращает True, если отправка прошла хотя бы через один канал.
        """
        # Создаем запись в БД о попытке отправки
        notification = Notification.objects.create(
            user=self.user,
            subject=self.subject,
            message=self.message,
            status='pending'
        )

        logger.info(f"🚀 Starting notification delivery for user {self.user.username}")
        logger.info(f"Available channels: {[ch.channel_name for ch in self.channels]}")
        logger.info(f"Message: '{self.subject}' - '{self.message[:50]}...'")

        # Проходим по всем каналам по порядку
        for channel in self.channels:
            channel_name = channel.channel_name
            logger.info(f"🔄 Attempting to send via {channel_name}...")
            
            try:
                success = channel.send(self.user, self.subject, self.message)
                
                if success:
                    # Успех! Сохраняем результат и завершаем цепочку
                    notification.status = 'sent'
                    notification.sent_via = channel_name
                    notification.save()
                    
                    self.last_successful_channel = channel_name
                    logger.info(f"✅ Notification successfully sent via {channel_name}")
                    
                    # Логируем информацию о пропущенных каналах
                    if self.failed_channels:
                        logger.info(f"📊 Skipped channels due to failures: {self.failed_channels}")
                    
                    return True
                else:
                    # Канал не сработал, пробуем следующий
                    self.failed_channels.append(channel_name)
                    logger.warning(f"❌ Channel {channel_name} failed, trying next...")
                    
            except Exception as e:
                # Ошибка в канале, пробуем следующий
                self.failed_channels.append(channel_name)
                logger.error(f"💥 Channel {channel_name} error: {e}, trying next...")
                continue

        # Если дошли сюда - все каналы не сработали
        notification.status = 'failed'
        notification.save()
        
        logger.error(f"💔 All delivery channels failed for user {self.user.username}")
        logger.error(f"Failed channels: {self.failed_channels}")
        
        return False

    def get_delivery_report(self):
        """Возвращает отчет о доставке"""
        return {
            'success': self.last_successful_channel is not None,
            'successful_channel': self.last_successful_channel,
            'failed_channels': self.failed_channels,
            'total_channels_attempted': len(self.failed_channels) + (1 if self.last_successful_channel else 0)
        }

def notify_user(user, subject, message):
    """
    Упрощенная функция для отправки уведомления.
    Возвращает сервис для получения детального отчета.
    """
    service = NotificationService(user, subject, message)
    service.send()
    return service