from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    department = models.CharField(max_length=100, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
