from django.urls import path
from . import views

urlpatterns = [
    path('inbox/', views.dm_home, name='inbox'),
    path('dm/', views.dm_home, name='dm_home'),
    path('dm/<int:user_id>/', views.dm_chat, name='dm_chat'),
    path('dm/<int:user_id>/messages.json', views.dm_messages_json, name='dm_messages_json'),
    path('send/', views.send_message, name='send_message'),
    path('send/<int:receiver_id>/', views.send_message, name='send_message_to'),
    path('<int:pk>/', views.message_detail, name='message_detail'),
    
    path('channels/', views.channel_list, name='channel_list'),
    path('channels/create/', views.channel_create, name='channel_create'),
    path('channels/<int:pk>/', views.channel_detail, name='channel_detail'),
    path('channels/<int:pk>/messages.json', views.channel_messages_json, name='channel_messages_json'),
]
