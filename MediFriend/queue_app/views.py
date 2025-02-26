import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Patient, Appointment

def home(request):
    """Render the main page with the patient form and appointment queue"""
    return render(request, 'queue/index.html')

def get_queue(request):
    """API endpoint to get the current appointment queue"""
    today = timezone.now().date()
    
    appointments = Appointment.objects.filter(
        appointment_time__date__gte=today,
        cancelled=False
    ).select_related('patient').order_by('appointment_time')
    
    queue_data = []
    
    for appointment in appointments:
        if appointment.completed and appointment.appointment_time.date() != today:
            continue
            
        queue_data.append({
            'id': appointment.id,
            'patient_id': appointment.patient.id,
            'name': appointment.patient.name,
            'email': appointment.patient.email,
            'age': appointment.patient.age,
            'cancer_stage': appointment.patient.cancer_stage,
            'temperature': appointment.patient.temperature,
            'heart_rate': appointment.patient.heart_rate,
            'blood_pressure': appointment.patient.blood_pressure,
            'description': appointment.patient.description,
            'priority': appointment.patient.priority,
            'appointment_time': appointment.appointment_time.strftime("%Y-%m-%d %H:%M"),
            'completed': appointment.completed,
            'cancelled': appointment.cancelled
        })
    
    return JsonResponse({'queue': queue_data})

@csrf_exempt
def add_patient(request):
    """API endpoint to add a new patient and schedule appointment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            priority = get_ai_priority(data)
            
            patient = Patient(
                name=data['name'],
                email=data['email'],
                age=data['age'],
                cancer_stage=data['cancerStage'],
                temperature=data['temp'],
                heart_rate=data['heart'],
                blood_pressure=data['blood'],
                description=data['description'],
                priority=priority
            )
            patient.save()
            
            appointment_time = schedule_appointment(patient, priority)
            
            return JsonResponse({
                'success': True, 
                'priority': priority,
                'patient_id': patient.id,
                'appointment_time': appointment_time.strftime("%Y-%m-%d %H:%M")
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@csrf_exempt
def update_appointment(request, appointment_id):
    """API endpoint to mark appointment as completed or cancelled"""
    if request.method == 'POST':
        try:
            appointment = get_object_or_404(Appointment, id=appointment_id)
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'complete':
                appointment.mark_completed()
                return JsonResponse({'success': True, 'message': 'Appointment marked as completed'})
            elif action == 'cancel':
                appointment.cancel()
                return JsonResponse({'success': True, 'message': 'Appointment cancelled and queue rescheduled'})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

def get_ai_priority(data):
    """Helper function to get priority from Gemini AI"""
    api_key = "AIzaSyBsjF22MDVkvIuHSxwwVlmxo3iXjspMZo4"  # In production, use environment variables
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    prompt = f"""
    Patient data:
    - Age: {data['age']}
    - Cancer Stage: {data['cancerStage']}
    - Temperature: {data['temp']}°C
    - Heart Rate: {data['heart']} bpm
    - Blood Pressure: {data['blood']}
    - Description: {data['description']}

    Based on this data for a cancer patient, analyze the urgency and return only a JSON object with a 'priority' field containing a number from 1 to 5, where 1 is lowest priority and 5 is highest priority. Example response: {{"priority": 3}}
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"API request failed with status: {response.status_code}")
    
    response_data = response.json()
    response_text = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
    
    priority = None
    
    try:
        parsed_json = json.loads(response_text)
        priority = parsed_json.get('priority')
    except json.JSONDecodeError:
        pass
    
    if priority is None:
        import re
        json_match = re.search(r'\{.*?\}', response_text)
        if json_match:
            try:
                extracted_json = json.loads(json_match.group(0))
                priority = extracted_json.get('priority')
            except json.JSONDecodeError:
                pass
    
    if priority is None:
        import re
        number_match = re.search(r'\b[1-5]\b', response_text)
        if number_match:
            priority = int(number_match.group(0))
    
    if priority is None or priority < 1 or priority > 5:
        priority = 1
    
    return priority

def schedule_appointment(patient, priority):
    """Schedule an appointment based on priority"""
    today = timezone.now().date()
    
    if priority >= 4:
        appointment_time = Appointment.get_next_available_slot(today)
    elif priority == 3:
        appointment_time = Appointment.get_next_available_slot(today)
        if appointment_time.date() > today + timedelta(days=1):
            pass
    
    else:
        appointment_time = Appointment.get_next_available_slot(today)
        
    appointment = Appointment(
        patient=patient,
        appointment_time=appointment_time,
        duration=60  
    )
    appointment.save()
    
    return appointment_time