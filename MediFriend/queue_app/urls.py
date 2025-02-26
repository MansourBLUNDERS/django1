# urls.py
from django.urls import path
from . import views

app_name = 'queue'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/queue/', views.get_queue, name='get_queue'),
    path('api/add-patient/', views.add_patient, name='add_patient'),
    path('api/update-status/', views.update_status, name='update_status'),
]
