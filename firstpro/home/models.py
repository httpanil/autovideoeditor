from django.db import models
import uuid

class VideoJob(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]
    status_message = models.TextField(default="Starting...")
    progress = models.IntegerField(default=0)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')

    video = models.FileField(upload_to='videos/', null=True, blank=True)

    error = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.status}"