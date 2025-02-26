# models.py
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta

class Patient(models.Model):
    """Model to store patient information"""
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
    
    def __str__(self):
        return f"{self.name} (Priority: {self.priority})"
    
    class Meta:
        ordering = ['-priority', 'created_at']


class Appointment(models.Model):
    """Model to manage appointments with time slots"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='appointments')
    appointment_time = models.DateTimeField()
    duration = models.IntegerField(default=60)  # Duration in minutes
    completed = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['appointment_time']
    
    def __str__(self):
        status = "Completed" if self.completed else "Cancelled" if self.cancelled else "Scheduled"
        return f"{self.patient.name}: {self.appointment_time.strftime('%Y-%m-%d %H:%M')} ({status})"
    
    def mark_completed(self):
        """Mark appointment as completed"""
        self.completed = True
        self.save()
    
    def cancel(self):
        """Cancel appointment and reschedule other appointments"""
        self.cancelled = True
        self.save()
        
        # Find all appointments after this one on the same day that aren't completed or cancelled
        same_day = self.appointment_time.date()
        later_appointments = Appointment.objects.filter(
            appointment_time__date=same_day,
            appointment_time__gt=self.appointment_time,
            completed=False,
            cancelled=False
        ).order_by('appointment_time')
        
        # Move each appointment earlier
        current_time = self.appointment_time
        for appointment in later_appointments:
            # Move this appointment to the current_time
            old_time = appointment.appointment_time
            appointment.appointment_time = current_time
            appointment.save()
            
            # Update current_time for the next appointment
            current_time = current_time + timedelta(minutes=appointment.duration)
    
    @classmethod
    def get_next_available_slot(cls, requested_date=None, default_duration=60):
        """Find the next available appointment slot based on existing appointments"""
        if requested_date is None:
            requested_date = timezone.now().date()
        else:
            # If a datetime was passed, extract just the date
            if isinstance(requested_date, datetime):
                requested_date = requested_date.date()
        
        # Start time is 9 AM on the requested date
        start_time = timezone.make_aware(datetime.combine(requested_date, datetime.min.time())) + timedelta(hours=9)
        
        # End time is 5 PM on the requested date
        end_time = start_time + timedelta(hours=8)
        
        # Get all non-cancelled appointments for this day
        day_appointments = cls.objects.filter(
            appointment_time__date=requested_date,
            cancelled=False
        ).order_by('appointment_time')
        
        # If no appointments exist yet, return the start time
        if not day_appointments.exists():
            return start_time
        
        # Check if there's space before the first appointment
        first_appt = day_appointments.first()
        if first_appt and (first_appt.appointment_time - start_time).total_seconds() / 60 >= default_duration:
            return start_time
        
        # Find gaps between appointments
        for i in range(len(day_appointments) - 1):
            current_end = day_appointments[i].appointment_time + timedelta(minutes=day_appointments[i].duration)
            next_start = day_appointments[i + 1].appointment_time
            
            # If there's enough time between appointments
            if (next_start - current_end).total_seconds() / 60 >= default_duration:
                return current_end
        
        # Check after the last appointment
        if day_appointments:
            last_appt = day_appointments.last()
            last_end = last_appt.appointment_time + timedelta(minutes=last_appt.duration)
            
            if last_end < end_time:
                return last_end
        
        # No slots available today, try tomorrow
        return cls.get_next_available_slot(requested_date + timedelta(days=1), default_duration)