# views.py
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .models import Patient
from django.utils import timezone
from datetime import timedelta

def home(request):
    """Render the main page with the patient form and queue"""
    return render(request, 'queue/index.html')

def get_queue(request):
    """API endpoint to get the current queue sorted by priority"""
    patients = Patient.objects.filter(status='pending').order_by('-priority', 'created_at')
    queue_data = []
    
    for index, patient in enumerate(patients, start=1):
        time_slot = patient.calculate_time_slot(index)
        queue_data.append({
            'id': patient.id,
            'index': index,
            'name': patient.name,
            'email': patient.email,
            'age': patient.age,
            'cancer_stage': patient.cancer_stage,
            'temperature': patient.temperature,
            'heart_rate': patient.heart_rate,
            'blood_pressure': patient.blood_pressure,
            'description': patient.description,
            'priority': patient.priority,
            'created_at': patient.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'status': patient.status,
            'time_slot': time_slot.strftime("%Y-%m-%d %H:%M"),
            'is_today': time_slot.date() == timezone.now().date()
        })
    
    return JsonResponse({'queue': queue_data})
    



@csrf_exempt
def add_patient(request):
    """API endpoint to add a new patient and get AI priority"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get AI priority
            priority = get_ai_priority(data)
            
            # Create new patient
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
            
            return JsonResponse({
                'success': True, 
                'priority': priority,
                'id': patient.id
            })
            
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
    
    # Try different methods to extract priority
    priority = None
    
    # Method 1: Try to parse entire response as JSON
    try:
        parsed_json = json.loads(response_text)
        priority = parsed_json.get('priority')
    except json.JSONDecodeError:
        pass
    
    # Method 2: Try to extract JSON using regex
    if priority is None:
        import re
        json_match = re.search(r'\{.*?\}', response_text)
        if json_match:
            try:
                extracted_json = json.loads(json_match.group(0))
                priority = extracted_json.get('priority')
            except json.JSONDecodeError:
                pass
    
    # Method 3: Just extract a number between 1-5
    if priority is None:
        import re
        number_match = re.search(r'\b[1-5]\b', response_text)
        if number_match:
            priority = int(number_match.group(0))
    
    # Default to 1 if all methods fail
    if priority is None or priority < 1 or priority > 5:
        priority = 1
    
    return priority




@csrf_exempt
def update_status(request):
    """API endpoint to update patient status"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            patient = Patient.objects.get(id=data['patient_id'])
            old_status = patient.status
            patient.status = data['status']
            patient.save()
            
            if data['status'] == 'completed':
                # For completions, no need to adjust time slots
                pass
            elif data['status'] == 'canceled':
                # For cancellations, shift subsequent patients forward
                subsequent_patients = Patient.objects.filter(
                    status='pending',
                    priority=patient.priority,
                    created_at__gt=patient.created_at
                ).order_by('created_at')
                
                # Update time slots for subsequent patients
                for subsequent_patient in subsequent_patients:
                    subsequent_patient.created_at = subsequent_patient.created_at - timedelta(hours=1)
                    subsequent_patient.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)