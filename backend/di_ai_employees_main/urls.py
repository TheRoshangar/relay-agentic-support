from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView # type: ignore

from .auth_api import login_api, csrf_token_api


urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/login/', login_api, name='login_api'),

    path('orders/', include('orders.urls')),
    path('support/', include('support.urls')),

    path('api/csrf/', csrf_token_api, name='csrf_token_api'),

    # OpenAPI docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger_ui'),
]