from django.db import models
from django.conf import settings


class Assignment(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignments_created'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.CharField(max_length=100, blank=True)
    deadline = models.DateTimeField()
    max_marks = models.IntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def submission_count(self):
        return self.submissions.count()


class Submission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('flagged', 'Flagged'),
        ('approved', 'Approved'),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    file = models.FileField(upload_to='submissions/', blank=True, null=True)
    text_content = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)

    plagiarism_score = models.FloatField(null=True, blank=True)
    quality_score = models.FloatField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True)
    generated_solution = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    teacher_remarks = models.TextField(blank=True)
    marks_awarded = models.IntegerField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['assignment', 'student']

    def __str__(self):
        return f"{self.student.username} → {self.assignment.title}"

    def plagiarism_level(self):
        if self.plagiarism_score is None:
            return 'unknown'
        if self.plagiarism_score >= 70:
            return 'high'
        elif self.plagiarism_score >= 40:
            return 'medium'
        return 'low'
