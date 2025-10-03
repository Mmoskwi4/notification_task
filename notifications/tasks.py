from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.contrib.auth.models import User
from .service import NotificationService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_notification_task(self, user_id, subject, message):
    """
    Celery задача для отправки уведомлений с механизмом повторных попыток
    """
    try:
        user = User.objects.get(id=user_id)
        logger.info(f"Starting notification task for user: {user.username}")
        
        service = NotificationService(user, subject, message)
        success = service.send()
        
        if success:
            logger.info(f"Notification successfully sent to user {user_id} via {service.last_successful_channel}")
            return {
                'status': 'success',
                'user_id': user_id,
                'username': user.username,
                'channel': service.last_successful_channel,
                'subject': subject
            }
        else:
            # Если все каналы не сработали, повторяем задачу
            logger.warning(f"All channels failed for user {user_id}, retrying...")
            raise self.retry(countdown=60)  # Повтор через 60 секунд
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found in database")
        return {
            'status': 'error', 
            'reason': 'user_not_found',
            'user_id': user_id
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in notification task: {e}")
        try:
            # Повторяем при неожиданных ошибках
            raise self.retry(exc=e, countdown=30)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for user {user_id}")
            return {
                'status': 'error', 
                'reason': 'max_retries_exceeded',
                'user_id': user_id
            }