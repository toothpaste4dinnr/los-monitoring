# Now update tests/test_database.py:

import pytest
import sqlite3
from datetime import datetime
import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import DatabaseManager, Patient

class TestDatabaseManager:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test database"""
        self.db_manager = DatabaseManager(":memory:")
        yield self.db_manager
        self.db_manager.conn.close()

    def test_database_initialization(self):
        """Test if database tables are created properly"""
        cursor = self.db_manager.conn.cursor()
        
        # Check if tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND (name='patients' OR name='los_tracking')
        """)
        tables = cursor.fetchall()
        assert len(tables) == 2, "Both tables should exist"

    def test_add_patient(self):
        """Test adding a patient"""
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
        
        self.db_manager.add_patient(patient)
        
        cursor = self.db_manager.conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id=?", (patient.id,))
        result = cursor.fetchone()
        
        assert result is not None, "Patient should be in database"
        assert result[0] == "TEST001", "Patient ID should match"

    def test_los_tracking(self):
        """Test adding and retrieving LOS tracking data"""
        # First add a patient
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
        self.db_manager.add_patient(patient)
        
        # Add tracking data
        test_time = datetime.now()
        vital_signs = {
            'heart_rate': 75,
            'blood_pressure': 120,
            'temperature': 37,
            'oxygen_saturation': 98
        }
        
        self.db_manager.add_tracking_record(
            patient.id,
            test_time,
            1.5,
            vital_signs
        )
        
        # Verify tracking data
        cursor = self.db_manager.conn.cursor()
        cursor.execute("SELECT * FROM los_tracking WHERE patient_id=?", (patient.id,))
        result = cursor.fetchone()
        
        assert result is not None, "Tracking record should exist"
        assert float(result[2]) == 1.5, "LOS should match"

    def test_get_department_stats(self):
        """Test department statistics"""
        # Add two patients in the same department
        for i in range(2):
            patient = Patient(
                id=f"TEST00{i+3}",
                admission_date=datetime.now(),
                predicted_los=5.0,
                department="Cardiology",
                diagnosis="Test Diagnosis",
                age=50,
                gender="Male",
                insurance="Test Insurance",
                severity=3
            )
            self.db_manager.add_patient(patient)
        
        stats = self.db_manager.get_department_stats()
        assert len(stats) > 0, "Should have department stats"
        cardiology_stats = stats[stats['department'] == 'Cardiology'].iloc[0]
        assert cardiology_stats['patient_count'] == 2, "Should have 2 patients in Cardiology"

    def test_get_los_distribution(self):
        """Test LOS distribution"""
        # Add a patient with tracking data
        patient = Patient(
            id="TEST006",
            admission_date=datetime.now(),
            predicted_los=5.0,
            department="Cardiology",
            diagnosis="Test Diagnosis",
            age=50,
            gender="Male",
            insurance="Test Insurance",
            severity=3
        )
        self.db_manager.add_patient(patient)
        
        # Add tracking record
        self.db_manager.add_tracking_record(
            patient.id,
            datetime.now(),
            2.5,
            {'heart_rate': 75, 'blood_pressure': 120, 'temperature': 37, 'oxygen_saturation': 98}
        )
        
        distribution = self.db_manager.get_los_distribution()
        assert not distribution.empty, "Should have LOS distribution data"

if __name__ == "__main__":
    pytest.main([__file__])