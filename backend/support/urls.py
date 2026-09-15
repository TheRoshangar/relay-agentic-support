from django.urls import path
from . import views


urlpatterns = [
    path('chat/<int:order_id>/', views.chat, name="chat"),

    # JSON API — استفاده شده توسط ری‌اکت
    path('dashboard/', views.dashboard, name="dashboard"),
    path('dashboard/<int:conversation_id>/', views.conversation_detail, name="conversation_detail"),

    # صفحات HTML — پنل مدیریت (staff)
    path('dashboard-page/', views.dashboard_view, name="dashboard_page"),
    path('dashboard-page/<int:conversation_id>/', views.conversation_detail_view, name="conversation_detail_page"),

    path('events/', views.support_events, name='support_events'),
    path('conversation-events/<int:conversation_id>/', views.conversation_events, name='conversation_events'),


    path('feedback/', views.submit_feedback, name='submit_feedback'),
]