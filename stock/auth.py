from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from .models import User


class BotAuth(BaseAuthentication):
    """Bot xizmat tokeni + X-Telegram-Id orqali xodim sifatida kiradi."""
    def authenticate(self, request):
        tok = request.headers.get('X-Bot-Token')
        if not tok or tok != settings.BOT_SERVICE_TOKEN:
            return None
        tg = request.headers.get('X-Telegram-Id')
        u = User.objects.filter(telegram_id=tg, is_active=True).first() if tg else None
        return (u, None) if u else None