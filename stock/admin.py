from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *
admin.site.register(User, UserAdmin)
for m, ld, sf in [(Supplier,('name','phone','is_active'),('name',)),
                  (Medicine,('name','barcode','unit','min_qoldiq','is_active'),('name','barcode')),
                  (Batch,('dori','partiya_raqami','yaroqlilik_sanasi','sotuv_narxi'),('partiya_raqami','dori__name')),
                  (StockIn,('partiya','miqdor','sana','kim'),('hujjat_raqami',)),
                  (StockOut,('partiya','miqdor','sabab','sana','kim','manba'),('partiya__partiya_raqami',)),
                  (ReminderLog,('partiya','turi','sana','chat_id','holat'),('partiya__partiya_raqami',))]:
    admin.site.register(m, type(m.__name__+'Admin', (admin.ModelAdmin,), {'list_display': ld, 'search_fields': sf, 'list_filter': (ld[-1],)}))
