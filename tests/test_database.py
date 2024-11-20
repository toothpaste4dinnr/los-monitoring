import pytest
from src.app import DatabaseManager, Patient
from datetime import datetime

@pytest.fixture
def db_manager():
    return DatabaseManager(":memory:")

def test_add_patient(db_manager):
    patient = Patient(
        id="TEST001",
        admission_date=datetime.now(),
        predicted_los=5.0,
        department="Test Dept",
        diagnosis="Test Diagnosis",
        age=50,
        gender="Male",
        insurance="Test Insurance",
        severity=3
    )
    db_manager.add_patient(patient)
    
    patients = db_manager.get_all_active_patients()
    assert len(patients) == 1
    assert patients.iloc[0]['id'] == "TEST001"

def test_los_tracking(db_manager):
    patient = Patient(
        id="TEST002",
        admission_date=datetime.now(),
        predicted_los=5.0,
        department="Test Dept",
        diagnosis="Test Diagnosis",
        age=50,
        gender="Male",
        insurance="Test Insurance",
        severity=3
    )
    db_manager.add_patient(patient)
    
    vital_signs = {
        'heart_rate': 75,
        'blood_pressure': 120,
        'temperature': 37,
        'oxygen_saturation': 98
    }
    db_manager.add_tracking_record(
        patient.id,
        datetime.now(),
        1.5,
        vital_signs
    )
    
    _, los_df = db_manager.get_patient_data(patient.id)
    assert len(los_df) == 1
    assert los_df.iloc[0]['current_los'] == 1.5
