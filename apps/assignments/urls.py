from django.urls import path
from . import views

urlpatterns = [
    path('', views.assignment_list, name='assignment_list'),
    path('calendar/', views.assignment_calendar, name='assignment_calendar'),
    path('create/', views.assignment_create, name='assignment_create'),
    path('<int:pk>/', views.assignment_detail, name='assignment_detail'),
    path('<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('submissions/', views.all_submissions, name='all_submissions'),
    path('submissions/<int:pk>/', views.submission_detail, name='submission_detail'),
    path('<int:pk>/edit/', views.assignment_edit, name='assignment_edit'),
    path('<int:pk>/delete/', views.assignment_delete, name='assignment_delete'),
    path('submissions/<int:pk>/recalculate/', views.recalculate_analysis, name='recalculate_analysis'),
]
