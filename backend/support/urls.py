from django.urls import path
from . import views


urlpatterns = [
    path('chat/<int:order_id>/', views.chat, name="chat"),
    path('dashboard/' , views.dashboard , name="dashboard"),
    path('dashboard-page/', views.dashboard_view, name="dashboard_page"),
    path('dashboard/<int:conversation_id>/' , views.conversation_detail , name="conversation_detail"),
    path('conversation/<int:conversation_id>/', views.conversation_detail_view, name="conversation_detail_view"),
    path('dashboard-page/<int:conversation_id>/', views.conversation_detail_view, name="conversation_detail"),
    path('events/',views.support_events,name='support_events'),
]