from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views

from .auth_api import login_api


urlpatterns = [
    path('admin/', admin.site.urls),

    path(
        'login/',
        auth_views.LoginView.as_view(template_name="login.html"),
        name="login",
    ),

    path(
        'api/login/',
        login_api,
        name='login_api',
    ),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('orders/', include('orders.urls')),
    path('support/', include('support.urls')),
]