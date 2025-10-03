import logging
from abc import ABC, abstractmethod
from django.conf import settings
from django.core.mail import send_mail
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import requests

logger = logging.getLogger(__name__)

class NotificationChannel(ABC):
    """Абстрактный базовый класс для всех каналов уведомлений."""

    @abstractmethod
    def send(self, user, subject, message) -> bool:
        """
        Attempts to send a notification to the user.
        Returns True if successful, False otherwise.
        """
        pass

    @property
    @abstractmethod
    def channel_name(self):
        """Returns the name of the channel."""
        pass

    def _log_success(self, user, details=""):
        """Логирование успешной отправки"""
        logger.info(f"✅ {self.channel_name.upper()} SUCCESS for {user.username} {details}")

    def _log_failure(self, user, reason=""):
        """Логирование неудачной отправки"""
        logger.warning(f"❌ {self.channel_name.upper()} FAILED for {user.username}: {reason}")

    def _log_error(self, user, error):
        """Логирование ошибки"""
        logger.error(f"💥 {self.channel_name.upper()} ERROR for {user.username}: {error}")

class EmailChannel(NotificationChannel):
    def send(self, user, subject, message) -> bool:
        if not user.email:
            self._log_failure(user, "no email address")
            return False
        
        try:
            # Проверяем настройки email
            if not all([
                settings.EMAIL_HOST_USER,
                settings.EMAIL_HOST_PASSWORD,
                settings.EMAIL_HOST
            ]):
                self._log_failure(user, "email settings not configured")
                return False
            
            logger.debug(f"📧 Preparing to send email to {user.email}")
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            self._log_success(user, f"to {user.email}")
            return True
            
        except Exception as e:
            self._log_error(user, str(e))
            return False

    @property
    def channel_name(self):
        return "email"

class TwilioSMSChannel(NotificationChannel):
    def __init__(self):
        self.client = None
        if (hasattr(settings, 'TWILIO_ACCOUNT_SID') and 
            hasattr(settings, 'TWILIO_AUTH_TOKEN') and
            settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN):
            
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID, 
                settings.TWILIO_AUTH_TOKEN
            )
            logger.debug("Twilio client initialized")
        else:
            logger.warning("Twilio credentials not found")

    def send(self, user, subject, message) -> bool:
        if not self.client:
            self._log_failure(user, "Twilio client not configured")
            return False

        from .models import UserProfile
        profile = getattr(user, 'userprofile', None)
        if not profile or not profile.phone_number:
            self._log_failure(user, "no phone number")
            return False
        
        try:
            full_message = f"{subject}\n{message}" if subject else message
            
            logger.debug(f"📱 Preparing to send SMS to {profile.phone_number}")
            
            twilio_message = self.client.messages.create(
                body=full_message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=profile.phone_number
            )
            
            self._log_success(user, f"to {profile.phone_number} (SID: {twilio_message.sid})")
            return True
            
        except TwilioRestException as e:
            self._log_error(user, f"Twilio error {e.code}: {e.msg}")
            return False
        except Exception as e:
            self._log_error(user, str(e))
            return False

    @property
    def channel_name(self):
        return "sms"

class TelegramChannel(NotificationChannel):
    def send(self, user, subject, message) -> bool:
        from .models import UserProfile
        profile = getattr(user, 'userprofile', None)
        if not profile or not profile.telegram_chat_id:
            self._log_failure(user, "no Telegram chat ID")
            return False
        
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not bot_token:
            self._log_failure(user, "Telegram bot token not configured")
            return False
        
        try:
            full_message = f"*{subject}*\n{message}" if subject else message
            
            logger.debug(f"📲 Preparing to send Telegram message to chat {profile.telegram_chat_id}")
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': profile.telegram_chat_id,
                'text': full_message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('ok'):
                self._log_success(user, f"to chat {profile.telegram_chat_id}")
                return True
            else:
                error_msg = response_data.get('description', 'Unknown error')
                self._log_error(user, f"Telegram API: {error_msg}")
                return False
                
        except requests.exceptions.RequestException as e:
            self._log_error(user, f"Network error: {e}")
            return False
        except Exception as e:
            self._log_error(user, str(e))
            return False

    @property
    def channel_name(self):
        return "telegram"