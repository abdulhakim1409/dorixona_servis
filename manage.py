#!/usr/bin/env python
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dorixona.settings')
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
from stock.models import Medicine
data = [
 ("Paratsetamol 500mg","quti",False),("Ibuprofen 400mg","quti",False),("Analgin 500mg","quti",False),
 ("Aspirin 500mg","quti",False),("Sitramon","quti",False),("No-shpa 40mg","quti",False),
 ("Aktivlangan ko'mir 250mg","quti",False),("Loratadin 10mg","quti",False),("Suprastin 25mg","quti",False),
 ("Vitamin C 500mg","quti",False),("Amoksitsillin 500mg","quti",True),("Azitromitsin 500mg","quti",True),
 ("Ciprofloksatsin 500mg","quti",True),("Omeprazol 20mg","quti",False),("Smekta","quti",False),
 ("Validol","dona",False),("Nafazolin tomchi 0.1%","ml",False),("Xlorgeksidin 0.05%","ml",False),
 ("Yod eritmasi 5%","ml",False),("Bint steril","dona",False)]
for i,(n,u,r) in enumerate(data,1):
    Medicine.objects.get_or_create(barcode=f"47800000{i:05d}", defaults=dict(name=n, unit=u, retsept_kerak=r, manufacturer="Test zavod", min_qoldiq=10))
exit()