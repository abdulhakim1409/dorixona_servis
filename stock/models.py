from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, F

class User(AbstractUser):
    ROLES = [('admin', 'Administrator'), ('pharmacist', 'Farmatsevt')]
    full_name = models.CharField(max_length=120)
    role = models.CharField(max_length=16, choices=ROLES, default='pharmacist')
    phone = models.CharField(max_length=20, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    notify_enabled = models.BooleanField(default=True)
    link_code = models.CharField(max_length=12, blank=True)  # botni bog'lash kodi

class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=20)
    stir = models.CharField(max_length=9, blank=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Medicine(models.Model):
    UNITS = [('dona', 'dona'), ('quti', 'quti'), ('ml', 'ml'), ('gr', 'gr')]
    name = models.CharField(max_length=150, db_index=True)
    barcode = models.CharField(max_length=32, unique=True, db_index=True)
    manufacturer = models.CharField(max_length=120)
    unit = models.CharField(max_length=10, choices=UNITS)
    min_qoldiq = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    retsept_kerak = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Batch(models.Model):
    dori = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='partiyalar')
    partiya_raqami = models.CharField(max_length=40)
    yaroqlilik_sanasi = models.DateField(db_index=True)
    kirim_narxi = models.DecimalField(max_digits=12, decimal_places=2)
    sotuv_narxi = models.DecimalField(max_digits=12, decimal_places=2)
    yetkazuvchi = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True)
    qabul_sanasi = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('dori', 'partiya_raqami')
        constraints = [models.CheckConstraint(condition=Q(sotuv_narxi__gte=F('kirim_narxi')), name='sotuv_gte_kirim')]

class StockIn(models.Model):
    partiya = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='kirimlar')
    miqdor = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    sana = models.DateField()
    hujjat_raqami = models.CharField(max_length=40, blank=True)
    izoh = models.TextField(blank=True)
    kim = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(miqdor__gt=0), name='kirim_miqdor_pos')]

class StockOut(models.Model):
    SABAB = [('sotuv', 'Sotuv'), ('qaytarish', 'Qaytarish'), ('yaroqsiz', 'Yaroqsiz')]
    partiya = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name='chiqimlar')
    miqdor = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    sabab = models.CharField(max_length=12, choices=SABAB)
    narx = models.DecimalField(max_digits=12, decimal_places=2)
    sana = models.DateField()
    izoh = models.TextField(blank=True)
    kim = models.ForeignKey(User, on_delete=models.PROTECT)
    manba = models.CharField(max_length=10, choices=[('api', 'api'), ('bot', 'bot')], default='api')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=Q(miqdor__gt=0), name='chiqim_miqdor_pos')]

class ReminderLog(models.Model):
    partiya = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='eslatmalar')
    turi = models.CharField(max_length=16, choices=[('muddat', 'muddat'), ('min_qoldiq', 'min_qoldiq')])
    sana = models.DateField(db_index=True)
    qolgan_kun = models.IntegerField()
    qoldiq = models.DecimalField(max_digits=10, decimal_places=2)
    chat_id = models.BigIntegerField()
    holat = models.CharField(max_length=10, choices=[('yuborildi', 'yuborildi'), ('xato', 'xato')])
    xato_matni = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('partiya', 'turi', 'sana', 'chat_id')
