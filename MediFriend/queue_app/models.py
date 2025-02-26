# models.py
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    age = models.IntegerField()
    cancer_stage = models.IntegerField()
    temperature = models.FloatField()
    heart_rate = models.IntegerField()
    blood_pressure = models.CharField(max_length=10)
    description = models.TextField()
    priority = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    index = models.PositiveIntegerField(default=0)
    def calculate_time_slot(self, index):
        """Calculate time slot based on queue position"""
        days = (index - 1) // 8
        hour = 9 + (index - 1) % 8  # Start at 9 AM, 8 slots/day
        return timezone.now().replace(
            hour=hour,
            minute=0,
            second=0,
            microsecond=0
        ) + timezone.timedelta(days=days)
    
    class Meta:
        #ordering = ['-priority', 'created_at']  # Order by priority (descending) then by creation time
        ordering = ['-priority', 'created_at']
    def __str__(self):
        return f"{self.name} (Priority: {self.priority})"
    