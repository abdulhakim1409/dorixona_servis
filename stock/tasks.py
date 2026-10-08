import requests
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone
from .api import batches, medicines
from .models import User, ReminderLog

def _send(chat, text):
    r = requests.post(f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage', timeout=10, json={'chat_id': chat, 'text': text,
        'reply_markup': {'inline_keyboard': [[{'text': 'Batafsil ro\'yxat', 'callback_data': 'exp:30'}, {'text': 'Hisobdan chiqarish', 'callback_data': 'chiqim'}]]}})
    r.raise_for_status()

@shared_task(bind=True, max_retries=3, default_retry_delay=300, autoretry_for=(requests.RequestException,), retry_backoff=True)
def muddat_eslatmasi(self):
    today = timezone.localdate()
    exp = list(batches().filter(yaroqlilik_sanasi__range=(today, today + timedelta(days=30)), qoldiq__gt=0).order_by('yaroqlilik_sanasi'))
    low = list(medicines().filter(is_active=True, qoldiq__lt=F('min_qoldiq')))
    for u in User.objects.filter(role='admin', telegram_id__isnull=False, notify_enabled=True, is_active=True):
        chat = u.telegram_id
        # jurnalda allaqachon bor yozuvlar o'tkazib yuboriladi (har bir partiya alohida)
        new_exp = [b for b in exp if not ReminderLog.objects.filter(partiya=b, turi='muddat', sana=today, chat_id=chat, holat='yuborildi').exists()]
        new_low = [m for m in low if not ReminderLog.objects.filter(partiya__dori=m, turi='min_qoldiq', sana=today, chat_id=chat, holat='yuborildi').exists()]
        if not new_exp and not new_low: continue  # bo'sh xabar yuborilmaydi
        text = f'Ertalabki hisobot — {today:%d.%m.%Y}\n'
        if new_exp:
            text += "\nMuddati tugayotgan partiyalar:\n" + '\n'.join(f'• {b.dori.name}, {b.partiya_raqami}: {b.qoldiq:g} {b.dori.unit}, {(b.yaroqlilik_sanasi - today).days} kun qoldi' for b in new_exp)
        if new_low:
            text += "\n\nMinimal qoldiqdan past dorilar:\n" + '\n'.join(f'• {m.name}: {m.qoldiq:g} / {m.min_qoldiq:g} {m.unit}' for m in new_low)
        try:
            _send(chat, text); holat, xato = 'yuborildi', ''
        except requests.RequestException as e:
            holat, xato = 'xato', str(e)
        items = [(b, 'muddat', (b.yaroqlilik_sanasi - today).days, b.qoldiq) for b in new_exp]
        for m in new_low:
            b = m.partiyalar.first()
            if b: items.append((b, 'min_qoldiq', 0, m.qoldiq))
        for b, turi, kun, q in items:
            try:
                obj, _ = ReminderLog.objects.get_or_create(partiya=b, turi=turi, sana=today, chat_id=chat,
                    defaults=dict(qolgan_kun=kun, qoldiq=q, holat=holat, xato_matni=xato))
                if obj.holat == 'xato' and holat == 'yuborildi': obj.holat, obj.xato_matni = holat, ''; obj.save()
            except IntegrityError:
                pass
        if holat == 'xato': raise requests.RequestException(xato)  # retry: 5, 10, 20 daqiqa
