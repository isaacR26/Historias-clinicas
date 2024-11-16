from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime

app = Flask(__name__)


def calcular_edad(birth_date):
    try:
        birth_date = datetime.strptime(birth_date, "%Y-%m-%d")
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except (ValueError, TypeError):
        return "Fecha inválida"  # Manejo de error si el formato de la fecha es incorrecto o nulo

@app.route('/', methods=['GET', 'POST'])
def index():
    data = None
    total_patients = 0

    if request.method == 'POST':
        # Obtener el ID del recurso del formulario
        resource_id = request.form.get('resource_id')

        # Construir la URL de la solicitud FHIR usando el ID proporcionado
        fhir_url = f'http://localhost:8080/fhir/Patient/{resource_id}'

        # Realizar la solicitud HTTP al servidor FHIR
        response = requests.get(fhir_url)
        
        if response.status_code == 200:
            data = response.json()  # Convertir la respuesta JSON en un diccionario Python
            # Calcular la edad si la fecha de nacimiento está disponible
            if 'birthDate' in data:
                data['age'] = calcular_edad(data['birthDate'])
            else:
                data['age'] = "Fecha de nacimiento no disponible"
        else:
            data = {'error': 'Paciente no encontrado'}

    # Obtener el total de pacientes
    count_response = requests.get('http://localhost:8080/fhir/Patient')
    if count_response.status_code == 200:
        count_data = count_response.json()
        total_patients = count_data.get('total', 0)

    # Renderizar la plantilla con los datos y el conteo de pacientes
    return render_template('index.html', data=data, total_patients=total_patients)

# Función para convertir segundos a horas
def seconds_to_hours(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} horas {minutes} minutos"

# Función para formatear fecha y hora
def format_datetime(date_str):
    # Convertir la fecha en formato ISO 8601 a un objeto datetime
    date_obj = datetime.fromisoformat(date_str)
    # Formatear la fecha y hora como "día, fecha y hora"
    return date_obj.strftime("%A, %d de %B de %Y, %I:%M %p")

@app.route('/history/<string:patient_id>', methods=['GET'])
def history(patient_id):
    history_data = {}

    # Obtener condiciones del paciente
    condition_url = f'http://localhost:8080/fhir/Condition'
    response = requests.get(condition_url)
    
    if response.status_code == 200:
        conditions = response.json().get('entry', [])
        patient_conditions = [
            condition['resource'] for condition in conditions
            if condition['resource']['subject']['reference'] == f'Patient/{patient_id}'
        ]
        history_data['conditions'] = patient_conditions
    else:
        history_data['conditions'] = []

    # Obtener observaciones del paciente
    observation_url = f'http://localhost:8080/fhir/Observation'
    response = requests.get(observation_url)
    
    if response.status_code == 200:
        observations = response.json().get('entry', [])
        patient_observations = [
            observation['resource'] for observation in observations
            if observation['resource']['subject']['reference'] == f'Patient/{patient_id}'
        ]
        # Convertir las duraciones a horas y formatear las fechas
        for observation in patient_observations:
            # Convertir fecha de inicio y fin
            observation['effectivePeriod']['start'] = format_datetime(observation['effectivePeriod']['start'])
            observation['effectivePeriod']['end'] = format_datetime(observation['effectivePeriod']['end'])
            
            # Convertir la duración total de segundos a horas
            total_duration_seconds = observation['component'][1]['valueQuantity']['value']
            observation['total_duration'] = seconds_to_hours(total_duration_seconds)
            
            # Convertir el promedio de 30 días de segundos a horas
            avg_duration_seconds = observation['component'][2]['valueQuantity']['value']
            observation['avg_duration'] = seconds_to_hours(avg_duration_seconds)
        
        history_data['observations'] = patient_observations
    else:
        history_data['observations'] = []

    # Obtener Medicamentos del paciente
    medication_url = f'http://localhost:8080/fhir/MedicationRequest'
    response = requests.get(medication_url)

    if response.status_code == 200:
        medications = response.json().get('entry', [])
        patient_medications = [
            medication['resource'] for medication in medications
            if medication['resource']['subject']['reference'] == f'Patient/{patient_id}'
        ]
        history_data['medications'] = patient_medications
    else:
        history_data['medications'] = []

    #Obtener Citas del Paciente 
    encounter_url = f'http://localhost:8080/fhir/Encounter'
    response = requests.get(encounter_url)

    if response.status_code == 200:
        encounters = response.json().get('entry', [])
        patient_encounters = [
            encounter['resource'] for encounter in encounters
            if encounter['resource']['subject']['reference'] == f'Patient/{patient_id}'
        ]
        history_data['encounters'] = patient_encounters
    else:
        history_data['encounters'] = []

        

    return render_template('history.html', history_data=history_data, patient_id=patient_id)



@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        # Obtener datos del formulario
        patient_id = request.form.get('patient_id')
        name = request.form.get('name')
        family = request.form.get('family')
        gender = request.form.get('gender')
        birthDate = request.form.get('birthDate')
        deceased = request.form.get('deceased') == 'true'
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        postalCode = request.form.get('postalCode')
        country = request.form.get('country')
        contactName = request.form.get('contactName')
        contactPhone = request.form.get('contactPhone')
        language = request.form.get('language')
        maritalStatus = request.form.get('maritalStatus')

        # Crear el recurso JSON para el paciente
        patient_data = {
            "resourceType": "Patient",
            "identifier": [{
                "system": "http://hospital.org/patients",
                "value": patient_id
            }],
            "name": [{
                "use": "official",
                "family": family,
                "given": [name]
            }],
            "gender": gender,
            "birthDate": birthDate,
            "deceasedBoolean": deceased,
            "telecom": [
                {"system": "phone", "value": phone, "use": "home"},
                {"system": "email", "value": email, "use": "work"}
            ],
            "address": [{
                "line": [address],
                "city": city,
                "state": state,
                "postalCode": postalCode,
                "country": country
            }],
            "contact": [{
                "relationship": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                        "code": "E",
                        "display": "Emergency Contact"
                    }]
                }],
                "name": {"family": contactName},
                "telecom": [{"system": "phone", "value": contactPhone}]
            }],
            "communication": [{
                "language": {
                    "coding": [{"system": "urn:ietf:bcp:47", "code": language, "display": language}]
                },
                "preferred": True
            }],
            "maritalStatus": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus",
                    "code": maritalStatus,
                    "display": maritalStatus
                }]
            }
        }

        # URL del servidor HAPI FHIR para crear pacientes
        fhir_url = 'http://localhost:8080/fhir/Patient'
        
        # Realizar la solicitud POST para crear el paciente
        response = requests.post(fhir_url, json=patient_data)
        
        if response.status_code == 201:
            return redirect(url_for('index'))
        else:
            return f"Error: {response.status_code}, could not add patient"
    
    return render_template('add_patient.html')

@app.route('/edit_patient/<string:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    fhir_url = f'http://localhost:8080/fhir/Patient/{patient_id}'

    # Realizar solicitud GET para obtener los datos actuales del paciente
    response = requests.get(fhir_url)
    if response.status_code == 200:
        patient_data = response.json()
        
        # Manejar valores por defecto para evitar errores de clave faltante
        patient_data.setdefault('maritalStatus', {'coding': [{'code': 'UNK'}]})
        patient_data.setdefault('telecom', [{'value': ''}])
        patient_data.setdefault('address', [{'line': [''], 'city': '', 'state': '', 'postalCode': '', 'country': ''}])
        patient_data.setdefault('contact', [{'name': {'family': ''}, 'telecom': [{'value': ''}]}])
        patient_data.setdefault('communication', [{'language': {'coding': [{'display': ''}]}}])

        if request.method == 'POST':
            # Recoger datos del formulario
            patient_data['name'][0]['given'][0] = request.form.get('name')
            patient_data['name'][0]['family'] = request.form.get('family')
            patient_data['gender'] = request.form.get('gender')
            patient_data['birthDate'] = request.form.get('birthDate')
            patient_data['maritalStatus']['coding'][0]['code'] = request.form.get('maritalStatus')
            patient_data['deceasedBoolean'] = request.form.get('deceased') == 'true'
            patient_data['telecom'][0]['value'] = request.form.get('phone')
            patient_data['telecom'][1]['value'] = request.form.get('email')
            patient_data['address'][0]['line'][0] = request.form.get('address')
            patient_data['address'][0]['city'] = request.form.get('city')
            patient_data['address'][0]['state'] = request.form.get('state')
            patient_data['address'][0]['postalCode'] = request.form.get('postalCode')
            patient_data['address'][0]['country'] = request.form.get('country')
            patient_data['contact'][0]['name']['family'] = request.form.get('contactName')
            patient_data['contact'][0]['telecom'][0]['value'] = request.form.get('contactPhone')
            patient_data['communication'][0]['language']['coding'][0]['display'] = request.form.get('language')

            # Realizar solicitud PUT para actualizar el paciente
            put_response = requests.put(fhir_url, json=patient_data)
            if put_response.status_code == 200:
                return redirect(url_for('index'))
            else:
                return f"Error: {put_response.status_code}, could not update patient"
        
        return render_template('edit_patient.html', patient=patient_data)
    else:
        return f"Error: {response.status_code}, could not retrieve patient data"

@app.route('/delete_patient/<string:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    fhir_url = f'http://localhost:8080/fhir/Patient/{patient_id}'
    response = requests.delete(fhir_url)

    if response.status_code == 204:
        return redirect(url_for('index'))
    else:
        return f"Error: {response.status_code}, could not delete patient"

if __name__ == '__main__':
    app.run(debug=True)


