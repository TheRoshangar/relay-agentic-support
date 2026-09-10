
from django.urls import path
from . import views


urlpatterns = [
    path('api/', views.orders_api, name='orders_api'),
    path(
        'api/<int:order_id>/',
        views.order_detail_api,
        name='order_detail_api',
    ),
]

