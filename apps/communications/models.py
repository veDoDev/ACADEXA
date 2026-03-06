from django.db import models
from django.conf import settings


class Message(models.Model):
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=200, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.sender} → {self.receiver}: {self.subject[:30]}"
