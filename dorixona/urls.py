from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from stock.api import router, urlpatterns as stock_urls
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', TokenObtainPairView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/', include(router.urls)),
    path('api/', include(stock_urls)),
    path('', TemplateView.as_view(template_name='index.html')),
]
