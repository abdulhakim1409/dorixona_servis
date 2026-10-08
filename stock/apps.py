from django.apps import AppConfig, apps

MODELLAR = {
    'stock.User': ('Xodim', 'Xodimlar'),
    'stock.Supplier': ('Yetkazib beruvchi', 'Yetkazib beruvchilar'),
    'stock.Medicine': ('Dori', 'Dorilar'),
    'stock.Batch': ('Partiya', 'Partiyalar'),
    'stock.StockIn': ('Kirim', 'Kirimlar'),
    'stock.StockOut': ('Chiqim', 'Chiqimlar'),
    'stock.ReminderLog': ('Eslatma jurnali', 'Eslatmalar jurnali'),
    'auth.Group': ('Guruh', 'Guruhlar'),
    'django_celery_beat.ClockedSchedule': ('Aniq vaqt', 'Aniq vaqtlar'),
    'django_celery_beat.CrontabSchedule': ('Crontab jadval', 'Crontab jadvallar'),
    'django_celery_beat.IntervalSchedule': ('Interval', 'Intervallar'),
    'django_celery_beat.PeriodicTask': ('Davriy vazifa', 'Davriy vazifalar'),
    'django_celery_beat.SolarSchedule': ('Quyosh hodisasi', 'Quyosh hodisalari'),
}

MAYDONLAR = {
    'username': 'Login', 'password': 'Parol', 'full_name': "To'liq ismi", 'role': 'Rol',
    'phone': 'Telefon', 'telegram_id': 'Telegram ID', 'notify_enabled': 'Eslatma yuborilsinmi',
    'link_code': "Bot bog'lash kodi", 'is_active': 'Faol', 'created_at': 'Yaratilgan vaqt',
    'name': 'Nomi', 'stir': 'STIR (INN)', 'address': 'Manzil',
    'barcode': 'Shtrix kod', 'manufacturer': 'Ishlab chiqaruvchi', 'unit': "O'lchov birligi",
    'min_qoldiq': 'Minimal qoldiq', 'retsept_kerak': 'Retsept kerak',
    'dori': 'Dori', 'partiya_raqami': 'Partiya raqami', 'yaroqlilik_sanasi': 'Yaroqlilik sanasi',
    'kirim_narxi': 'Kirim narxi', 'sotuv_narxi': 'Sotuv narxi', 'yetkazuvchi': 'Yetkazib beruvchi',
    'qabul_sanasi': 'Qabul sanasi', 'partiya': 'Partiya', 'miqdor': 'Miqdor', 'sana': 'Sana',
    'hujjat_raqami': 'Hujjat raqami', 'izoh': 'Izoh', 'kim': 'Kim yozgan', 'sabab': 'Sabab',
    'narx': 'Narx', 'manba': 'Manba', 'turi': 'Turi', 'qolgan_kun': 'Qolgan kun',
    'qoldiq': 'Qoldiq', 'chat_id': 'Chat ID', 'holat': 'Holat', 'xato_matni': 'Xato matni',
}


class StockConfig(AppConfig):
    name = 'stock'
    verbose_name = 'Ombor'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        for yol, (bir, kop) in MODELLAR.items():
            try:
                model = apps.get_model(yol)
            except LookupError:
                continue
            model._meta.verbose_name = bir
            model._meta.verbose_name_plural = kop
            if yol.startswith('stock.'):
                for f in model._meta.get_fields():
                    if f.name in MAYDONLAR and hasattr(f, 'verbose_name'):
                        f.verbose_name = MAYDONLAR[f.name]
        try:
            apps.get_app_config('django_celery_beat').verbose_name = 'Davriy vazifalar'
        except LookupError:
            pass