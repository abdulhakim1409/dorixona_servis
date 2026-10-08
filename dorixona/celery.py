import os
from celery import Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dorixona.settings')
app = Celery('dorixona')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
