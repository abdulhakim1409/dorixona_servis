from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Subquery, OuterRef, F, DecimalField, Value, Min
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import serializers, viewsets, mixins, filters
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.pagination import PageNumberPagination
from django.urls import path
from .models import *

class Bad(APIException):
    status_code = 400
class Pages(PageNumberPagination):
    page_size = 20

# ---- auth / ruxsatlar ----
class BotAuth(BaseAuthentication):
    """Bot xizmat tokeni + X-Telegram-Id orqali xodim sifatida kiradi."""
    def authenticate(self, request):
        tok = request.headers.get('X-Bot-Token')
        if not tok or tok != settings.BOT_SERVICE_TOKEN:
            return None
        tg = request.headers.get('X-Telegram-Id')
        u = User.objects.filter(telegram_id=tg, is_active=True).first() if tg else None
        return (u, None) if u else None
class IsAdmin(BasePermission):
    def has_permission(self, r, v): return bool(r.user and r.user.is_authenticated and r.user.role == 'admin')
class AdminWriteOnly(BasePermission):
    def has_permission(self, r, v):
        if not (r.user and r.user.is_authenticated): return False
        return r.method in ('GET', 'HEAD', 'OPTIONS') or r.user.role == 'admin'

# ---- qoldiq (ustunda saqlanmaydi, Subquery bilan hisoblanadi) ----
def _sum(model, **flt):
    return Coalesce(Subquery(model.objects.filter(**flt).values(flt_key(flt)).annotate(s=Sum('miqdor')).values('s')),
                    Value(Decimal('0')), output_field=DecimalField())
def flt_key(f): return 'partiya' if 'partiya' in f else 'partiya__dori'
def batches():
    q = Batch.objects.select_related('dori', 'yetkazuvchi')
    return q.annotate(kirim=_sum(StockIn, partiya=OuterRef('pk')), chiqim=_sum(StockOut, partiya=OuterRef('pk'))
                      ).annotate(qoldiq=F('kirim') - F('chiqim'))
def medicines():
    return Medicine.objects.annotate(kirim=_sum(StockIn, partiya__dori=OuterRef('pk')),
        chiqim=_sum(StockOut, partiya__dori=OuterRef('pk'))).annotate(qoldiq=F('kirim') - F('chiqim'))

# ---- serializerlar ----
class SupplierS(serializers.ModelSerializer):
    class Meta: model = Supplier; fields = '__all__'
class BatchS(serializers.ModelSerializer):
    qoldiq = serializers.DecimalField(10, 2, read_only=True)
    dori_nomi = serializers.CharField(source='dori.name', read_only=True)
    class Meta: model = Batch; fields = '__all__'
    def validate(self, d):
        qs = d.get('qabul_sanasi', getattr(self.instance, 'qabul_sanasi', None))
        ys = d.get('yaroqlilik_sanasi', getattr(self.instance, 'yaroqlilik_sanasi', None))
        if qs and ys and ys <= qs: raise serializers.ValidationError({'detail': "Yaroqlilik sanasi qabul sanasidan keyin bo'lishi shart"})
        kn = d.get('kirim_narxi', getattr(self.instance, 'kirim_narxi', 0)); sn = d.get('sotuv_narxi', getattr(self.instance, 'sotuv_narxi', 0))
        if sn < kn: raise serializers.ValidationError({'detail': "Sotuv narxi kirim narxidan past bo'lmasin"})
        return d
class MedicineS(serializers.ModelSerializer):
    qoldiq = serializers.DecimalField(10, 2, read_only=True, default=None)
    class Meta: model = Medicine; fields = '__all__'
class MedicineDetailS(MedicineS):
    partiyalar = serializers.SerializerMethodField()
    def get_partiyalar(self, o):
        return BatchS(batches().filter(dori=o).order_by('yaroqlilik_sanasi'), many=True).data
class StockInS(serializers.ModelSerializer):
    class Meta: model = StockIn; fields = '__all__'; read_only_fields = ('kim',)
class StockOutS(serializers.ModelSerializer):
    class Meta: model = StockOut; fields = '__all__'; read_only_fields = ('kim', 'narx')

# ---- viewsetlar ----
class SupplierV(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('name'); serializer_class = SupplierS
    permission_classes = [AdminWriteOnly]; pagination_class = Pages; http_method_names = ['get', 'post', 'head', 'options']
class MedicineV(viewsets.ModelViewSet):
    permission_classes = [AdminWriteOnly]; pagination_class = Pages
    filter_backends = [filters.SearchFilter]; search_fields = ['name', 'barcode']
    def get_serializer_class(self): return MedicineDetailS if self.action == 'retrieve' else MedicineS
    def get_queryset(self):
        q = medicines().order_by('name'); p = self.request.query_params
        if p.get('manufacturer'): q = q.filter(manufacturer__icontains=p['manufacturer'])
        if p.get('is_active') in ('true', 'false'): q = q.filter(is_active=p['is_active'] == 'true')
        return q
    def destroy(self, request, *a, **k):
        if Batch.objects.filter(dori_id=k['pk']).exists(): raise Bad("Bu dorining partiyalari bor, o'chirib bo'lmaydi")
        return super().destroy(request, *a, **k)
class BatchV(viewsets.ModelViewSet):
    serializer_class = BatchS; permission_classes = [AdminWriteOnly]; pagination_class = Pages
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    def get_queryset(self):
        q = batches().order_by('yaroqlilik_sanasi'); p = self.request.query_params
        if p.get('medicine'): q = q.filter(dori_id=p['medicine'])
        if p.get('supplier'): q = q.filter(yetkazuvchi_id=p['supplier'])
        if p.get('expiring_in'): q = q.filter(yaroqlilik_sanasi__range=(timezone.localdate(), timezone.localdate() + timedelta(days=int(p['expiring_in']))))
        return q
class StockInV(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = StockIn.objects.select_related('partiya__dori').order_by('-id'); serializer_class = StockInS
    permission_classes = [IsAdmin]; pagination_class = Pages
    def get_queryset(self):
        q = super().get_queryset(); p = self.request.query_params
        if p.get('date_from'): q = q.filter(sana__gte=p['date_from'])
        if p.get('date_to'): q = q.filter(sana__lte=p['date_to'])
        if p.get('medicine'): q = q.filter(partiya__dori_id=p['medicine'])
        return q
    def perform_create(self, s): s.save(kim=self.request.user)
class StockOutV(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = StockOut.objects.select_related('partiya__dori', 'kim').order_by('-id'); serializer_class = StockOutS
    permission_classes = [IsAuthenticated]; pagination_class = Pages
    def get_queryset(self):
        q = super().get_queryset(); p = self.request.query_params
        for k, f in [('reason', 'sabab'), ('date_from', 'sana__gte'), ('date_to', 'sana__lte'), ('user', 'kim_id')]:
            if p.get(k): q = q.filter(**{f: p[k]})
        return q
    def create(self, request, *a, **k):
        s = self.get_serializer(data=request.data); s.is_valid(raise_exception=True)
        d = s.validated_data; today = timezone.localdate()
        with transaction.atomic():
            b = Batch.objects.select_for_update().get(pk=d['partiya'].pk)  # poyga holatiga qarshi qulf
            qoldiq = batches().get(pk=b.pk).qoldiq
            if d['miqdor'] > qoldiq: raise Bad(f"Partiyada atigi {qoldiq:g} {b.dori.unit} qoldi")
            if b.yaroqlilik_sanasi < today and d['sabab'] == 'sotuv': raise Bad("Muddati o'tgan partiyadan sotuv qilib bo'lmaydi, faqat 'yaroqsiz' sababi mumkin")
            if d['sabab'] == 'yaroqsiz' and not d.get('izoh'): raise Bad("Yaroqsiz sababi uchun izoh majburiy")
            obj = s.save(kim=request.user, narx=b.sotuv_narxi, manba=request.headers.get('X-Bot-Token') and 'bot' or 'api')
        data = dict(s.data); data['yangi_qoldiq'] = qoldiq - obj.miqdor
        return Response(data, status=201)

router = DefaultRouter()
router.register('suppliers', SupplierV, basename='suppliers')
router.register('medicines', MedicineV, basename='medicines')
router.register('batches', BatchV, basename='batches')
router.register('stock-in', StockInV, basename='stock-in')
router.register('stock-out', StockOutV, basename='stock-out')

# ---- qoldiq / hisobot endpointlari ----
def paged(view, qs, ser):
    pg = Pages(); page = pg.paginate_queryset(qs, view.request, view=None)
    return pg.get_paginated_response(ser(page, many=True).data)
@api_view(['GET'])
def me(r): return Response({'id': r.user.id, 'username': r.user.username, 'full_name': r.user.full_name, 'role': r.user.role})
@api_view(['GET'])
def barcode(r, code):
    m = medicines().filter(barcode=code).first()
    if not m: return Response({'detail': 'Bunday shtrix kod bazada yoq'}, status=404)
    d = MedicineDetailS(m).data
    d['eng_yaqin_muddat'] = min((b['yaroqlilik_sanasi'] for b in d['partiyalar'] if Decimal(b['qoldiq']) > 0), default=None)
    return Response(d)
@api_view(['GET'])
def stock(r): return paged(r, medicines().order_by('name'), MedicineS)
@api_view(['GET'])
def stock_batches(r):
    q = batches().order_by('yaroqlilik_sanasi')
    if r.query_params.get('only_positive') == 'true': q = q.filter(qoldiq__gt=0)
    return paged(r, q, BatchS)
@api_view(['GET'])
def expiring(r):
    t = timezone.localdate(); days = int(r.query_params.get('days', 30))
    return paged(r, batches().filter(yaroqlilik_sanasi__gte=t, yaroqlilik_sanasi__lte=t + timedelta(days=days), qoldiq__gt=0).order_by('yaroqlilik_sanasi'), BatchS)
@api_view(['GET'])
def expired(r): return paged(r, batches().filter(yaroqlilik_sanasi__lt=timezone.localdate(), qoldiq__gt=0).order_by('yaroqlilik_sanasi'), BatchS)
@api_view(['GET'])
def low(r): return paged(r, medicines().filter(is_active=True, qoldiq__lt=F('min_qoldiq')).order_by('name'), MedicineS)
@api_view(['GET'])
def movements(r):
    a = [dict(tur='kirim', id=i.id, dori=i.partiya.dori.name, partiya=i.partiya.partiya_raqami, miqdor=i.miqdor, sana=i.sana) for i in StockIn.objects.select_related('partiya__dori')[:200]]
    b = [dict(tur='chiqim', id=i.id, dori=i.partiya.dori.name, partiya=i.partiya.partiya_raqami, miqdor=i.miqdor, sana=i.sana, sabab=i.sabab) for i in StockOut.objects.select_related('partiya__dori')[:200]]
    rows = sorted(a + b, key=lambda x: (x['sana'], x['id']), reverse=True)
    pg = Pages(); return pg.get_paginated_response(pg.paginate_queryset(rows, r))
@api_view(['GET'])
@permission_classes([IsAdmin])
def summary(r):
    t = timezone.localdate(); bq = batches()
    qiymat = sum((b.qoldiq * b.kirim_narxi for b in bq.filter(qoldiq__gt=0)), Decimal('0'))
    return Response({'dorilar_soni': Medicine.objects.count(), 'ombor_qiymati': qiymat,
        'muddati_yaqinlar': bq.filter(yaroqlilik_sanasi__range=(t, t + timedelta(days=30)), qoldiq__gt=0).count()})
@api_view(['POST'])
@permission_classes([AllowAny])
def bot_link(r):
    if r.headers.get('X-Bot-Token') != settings.BOT_SERVICE_TOKEN: return Response({'detail': 'Ruxsat yoq'}, status=403)
    u = User.objects.filter(link_code=r.data.get('code', ''), is_active=True).exclude(link_code='').first()
    if not u: return Response({'detail': "Kod noto'g'ri"}, status=400)
    u.telegram_id = r.data['telegram_id']; u.link_code = ''; u.save()
    return Response({'role': u.role, 'full_name': u.full_name})

urlpatterns = [path('auth/me/', me), path('medicines/barcode/<str:code>/', barcode), path('stock/', stock),
    path('stock/batches/', stock_batches), path('stock/expiring/', expiring), path('stock/expired/', expired),
    path('stock/low/', low), path('stock/movements/', movements), path('reports/summary/', summary), path('bot/link/', bot_link)]
