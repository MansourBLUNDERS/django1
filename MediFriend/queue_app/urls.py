# urls.py
from django.urls import path
from . import views

app_name = 'queue'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/queue/', views.get_queue, name='get_queue'),
    path('api/add-patient/', views.add_patient, name='add_patient'),
    path('api/appointments/<int:appointment_id>/update/', views.update_appointment, name='update_appointment'),
]