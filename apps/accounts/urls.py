from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('classes/', views.teacher_classes_view, name='teacher_classes'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('analytics/submissions.csv', views.export_submissions_csv, name='export_submissions_csv'),
]
