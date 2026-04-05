from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        ('Profile Attributes', {'fields': ('role', 'department', 'bio', 'profile_pic')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile Attributes', {'fields': ('role', 'department', 'bio', 'profile_pic')}),
    )
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'department']

admin.site.register(User, CustomUserAdmin)
