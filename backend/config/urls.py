from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from core.health import health
from core.auth_api import RegisterView, LoginView, MeView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from django.urls import include
from core.data_api import PaisViewSet
from core.risk_api import RiesgoViewSet, AlertaViewSet
from core.portfolio_api import PortafolioViewSet
from core.dashboard_api import DashboardViewSet
from core.audit_api import AuditListView

router = DefaultRouter()
router.register('paises', PaisViewSet)
router.register('riesgo', RiesgoViewSet, basename='riesgo')
router.register('alertas', AlertaViewSet, basename='alerta')
router.register('portafolios', PortafolioViewSet, basename='portafolio')
router.register('dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = [
    path('api/auditoria/', AuditListView.as_view()),
    path('api/', include(router.urls)),
    path('api/auth/register/', RegisterView.as_view()),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/auth/me/', MeView.as_view()),
    path('api/health/', health),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema')),
]

