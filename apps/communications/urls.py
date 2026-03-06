from django.urls import path
from . import views

urlpatterns = [
    path('inbox/', views.inbox, name='inbox'),
    path('send/', views.send_message, name='send_message'),
    path('send/<int:receiver_id>/', views.send_message, name='send_message_to'),
    path('<int:pk>/', views.message_detail, name='message_detail'),
]
