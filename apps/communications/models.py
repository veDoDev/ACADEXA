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

    sentiment_label = models.CharField(max_length=16, blank=True)  # positive|neutral|negative
    sentiment_score = models.IntegerField(null=True, blank=True)  # -100..100 (heuristic)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.sender} → {self.receiver}: {self.subject[:30]}"


class Channel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_channels'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='channels'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ChannelMessage(models.Model):
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='channel_messages'
    )
    body = models.TextField()

    is_flagged = models.BooleanField(default=False)
    flag_reason = models.CharField(max_length=200, blank=True)

    sentiment_label = models.CharField(max_length=16, blank=True)  # positive|neutral|negative
    sentiment_score = models.IntegerField(null=True, blank=True)  # -100..100 (heuristic)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sent_at']

    def __str__(self):
        return f"{self.sender.username} in {self.channel.name} at {self.sent_at}"
