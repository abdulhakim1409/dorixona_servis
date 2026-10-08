import os
from datetime import timedelta
from pathlib import Path
from celery.schedules import crontab
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.environ['SECRET_KEY']; DEBUG = os.getenv('DEBUG') == '1'; ALLOWED_HOSTS = ['*']
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.messages', 'django.contrib.staticfiles', 'rest_framework', 'django_celery_beat', 'stock']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware']
ROOT_URLCONF = 'dorixona.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages']}}]
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.getenv('DB_NAME', 'dorixona'), 'USER': os.getenv('DB_USER', 'dorixona_user'),
    'PASSWORD': os.getenv('DB_PASSWORD', ''), 'HOST': os.getenv('DB_HOST', 'localhost'), 'PORT': os.getenv('DB_PORT', '5432')}}
AUTH_USER_MODEL = 'stock.User'
LANGUAGE_CODE = 'uz'
TIME_ZONE = 'Asia/Tashkent'; USE_I18N = True; USE_TZ = True; STATIC_URL = 'static/'; DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
REST_FRAMEWORK = {'DEFAULT_AUTHENTICATION_CLASSES': ['stock.auth.BotAuth', 'rest_framework_simplejwt.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination', 'PAGE_SIZE': 20}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(hours=8)}
BOT_SERVICE_TOKEN = os.getenv('BOT_SERVICE_TOKEN'); TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0'); CELERY_TIMEZONE = 'Asia/Tashkent'
CELERY_BEAT_SCHEDULE = {'muddat-eslatma': {'task': 'stock.tasks.muddat_eslatmasi', 'schedule': crontab(hour=8, minute=0)}}