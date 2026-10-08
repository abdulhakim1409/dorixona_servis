"""Test ma'lumotlarini kiritadi. Qayta ishga tushirsa ham takrorlanmaydi."""
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from stock.models import User, Supplier, Medicine, Batch, StockIn, StockOut

t = timezone.localdate()
d = lambda n: t + timedelta(days=n)
admin = User.objects.filter(role='admin').first() or User.objects.filter(is_superuser=True).first()

# 1. Yetkazib beruvchilar
SUP = {
    'Nobel Pharma Distribution': ('+998712000001', '301234567', 'Toshkent, Chilonzor tumani'),
    'Dori-Darmon Savdo': ('+998712000002', '302345678', 'Toshkent, Yunusobod tumani'),
    'Farm Trade Asia': ('+998712000003', '303456789', 'Toshkent, Sergeli tumani'),
}
sup = {n: Supplier.objects.get_or_create(name=n, defaults=dict(phone=p, stir=s, address=a))[0] for n, (p, s, a) in SUP.items()}
S = list(sup.values())

# 2. Dorilar: (nomi, ishlab chiqaruvchi, shtrix kod, birlik, min_qoldiq, retsept)
MED = [
    ('Paratsetamol 500mg', 'Nobel Pharma', '4780012345001', 'quti', 20, False),
    ('Ibuprofen 200mg', 'Nika Pharm', '4780012345002', 'quti', 15, False),
    ('Analgin 500mg', 'Dori-Darmon', '4780012345003', 'quti', 20, False),
    ('Sitramon', 'Nika Pharm', '4780012345004', 'quti', 10, False),
    ('Aspirin 500mg', 'Bayer', '4780012345005', 'quti', 10, False),
    ('No-shpa 40mg', 'Sanofi', '4780012345006', 'quti', 15, False),
    ("Aktivlashtirilgan ko'mir", 'Dori-Darmon', '4780012345007', 'quti', 30, False),
    ('Smekta', 'Ipsen', '4780012345008', 'quti', 10, False),
    ('Loperamid 2mg', 'Nobel Pharma', '4780012345009', 'quti', 10, False),
    ('Suprastin 25mg', 'Egis', '4780012345010', 'quti', 10, False),
    ('Loratadin 10mg', 'Nika Pharm', '4780012345011', 'quti', 10, False),
    ('Ambroksol sirop 15mg/5ml', 'Nobel Pharma', '4780012345012', 'ml', 500, False),
    ('Xlorheksidin 0.05%', 'Dori-Darmon', '4780012345013', 'ml', 1000, False),
    ('Vodorod peroksid 3%', 'Dori-Darmon', '4780012345014', 'ml', 1000, False),
    ('Validol 60mg', 'Dori-Darmon', '4780012345015', 'quti', 10, False),
    ('Amoksitsillin 500mg', 'Nobel Pharma', '4780012345016', 'quti', 10, True),
    ('Azitromitsin 500mg', 'Nika Pharm', '4780012345017', 'quti', 8, True),
    ('Metformin 850mg', 'Nobel Pharma', '4780012345018', 'quti', 10, True),
    ('Omeprazol 20mg', 'Nika Pharm', '4780012345019', 'quti', 10, True),
    ('Enalapril 10mg', 'Egis', '4780012345020', 'quti', 10, True),
]
med = {}
for n, m, b, u, mq, r in MED:
    med[b] = Medicine.objects.get_or_create(barcode=b, defaults=dict(name=n, manufacturer=m, unit=u, min_qoldiq=mq, retsept_kerak=r))[0]

# 3. Partiyalar. Maxsus muddatlar (bugundan necha kun): yaqin, o'tgan, o'rtacha
SPECIAL = {'001': 10, '002': 25, '003': -15, '005': 51, '016': 18}
new_batches = []
for i, (n, m, b, u, mq, r) in enumerate(MED, 1):
    key = b[-3:]
    kirim = Decimal(2000 + i * 700)
    qty = 2000 if u == 'ml' else 50
    if key == '016': qty = 12
    exp = SPECIAL.get(key, 200 + i * 25)
    new_batches.append((med[b], f'B-{i:03d}', exp, kirim, qty, S[i % 3], -60))
# ikkinchi (yangi) partiyalar
for key in ('001', '002', '003'):
    b = '4780012345' + key
    i = int(key)
    new_batches.append((med[b], f'B-{i:03d}N', 330, Decimal(2500 + i * 700), 80, S[(i + 1) % 3], -10))

batches = {}
for dori, raqam, exp, kirim, qty, s, qabul in new_batches:
    bt, created = Batch.objects.get_or_create(
        dori=dori, partiya_raqami=raqam,
        defaults=dict(yaroqlilik_sanasi=d(exp), kirim_narxi=kirim, sotuv_narxi=(kirim * Decimal('1.4')).quantize(Decimal('1')),
                      yetkazuvchi=s, qabul_sanasi=d(qabul)))
    batches[raqam] = bt
    # 4. Kirim faqat bo'sh partiyaga yoziladi (takrorlanmaslik uchun)
    if not bt.kirimlar.exists():
        StockIn.objects.create(partiya=bt, miqdor=qty, sana=bt.qabul_sanasi, hujjat_raqami=f'F-{1000 + len(batches)}', kim=admin)

# 5. Bir nechta chiqim (faqat chiqim umuman yo'q bo'lsa)
if not StockOut.objects.exists():
    for raqam, qty, sabab, izoh in [('B-001', 5, 'sotuv', ''), ('B-016', 6, 'sotuv', ''), ('B-003', 10, 'yaroqsiz', "Muddati o'tgan")]:
        bt = batches[raqam]
        StockOut.objects.create(partiya=bt, miqdor=qty, sabab=sabab, narx=bt.sotuv_narxi, sana=t, izoh=izoh, kim=admin, manba='api')

# Farmatsevt sinov akkaunti
if not User.objects.filter(username='farmatsevt').exists():
    User.objects.create_user('farmatsevt', password='farm12345', full_name='Sinov Farmatsevt', role='pharmacist')

print('Tayyor:', Supplier.objects.count(), 'yetkazuvchi,', Medicine.objects.count(), 'dori,', Batch.objects.count(), 'partiya,',
      StockIn.objects.count(), 'kirim,', StockOut.objects.count(), 'chiqim')
