
from django.urls import path
from . import views


urlpatterns = [
    path('api/', views.orders_api, name='orders_api'),
]

