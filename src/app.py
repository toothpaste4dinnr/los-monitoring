import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np
import sqlite3
import threading
import time
from dataclasses import dataclass
import logging
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='los_monitor.log'
)
logger = logging.getLogger(__name__)

@dataclass
class Patient:
    id: str
    admission_date: datetime
    predicted_los: float
    department: str
    diagnosis: str
    age: int
    gender: str
    insurance: str
    severity: int  # 1-5 scale
    status: str = "Active"
    discharge_date: datetime = None

class DatabaseManager:
    def __init__(self, db_path="hospital.db"):
        self.db_path = db_path
        self.setup_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def setup_database(self):
        """Create necessary tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Drop existing tables if they exist
            cursor.execute('DROP TABLE IF EXISTS los_tracking')
            cursor.execute('DROP TABLE IF EXISTS patients')
            
            # Create patients table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id TEXT PRIMARY KEY,
                    admission_date TEXT,
                    predicted_los FLOAT,
                    department TEXT,
                    diagnosis TEXT,
                    age INTEGER,
                    gender TEXT,
                    insurance TEXT,
                    severity INTEGER,
                    status TEXT,
                    discharge_date TEXT NULL
                )
            ''')
            
            # Create tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS los_tracking (
                    patient_id TEXT,
                    tracking_date TEXT,
                    current_los FLOAT,
                    vital_signs TEXT,
                    FOREIGN KEY (patient_id) REFERENCES patients(id)
                )
            ''')
            
            conn.commit()

    def add_patient(self, patient: Patient):
        """Add a new patient to the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            admission_date_str = patient.admission_date.isoformat()
            discharge_date_str = patient.discharge_date.isoformat() if patient.discharge_date else None
            
            cursor.execute('''
                INSERT INTO patients 
                (id, admission_date, predicted_los, department, diagnosis, 
                 age, gender, insurance, severity, status, discharge_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient.id, admission_date_str, patient.predicted_los,
                  patient.department, patient.diagnosis, patient.age,
                  patient.gender, patient.insurance, patient.severity,
                  patient.status, discharge_date_str))
            conn.commit()

    def add_tracking_record(self, patient_id: str, tracking_date: datetime, 
                          current_los: float, vital_signs: dict):
        """Add a tracking record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO los_tracking 
                (patient_id, tracking_date, current_los, vital_signs)
                VALUES (?, ?, ?, ?)
            ''', (patient_id, tracking_date.isoformat(), current_los, str(vital_signs)))
            conn.commit()

    def generate_sample_data(self):
        """Generate sample data for testing"""
        departments = ['Cardiology', 'Orthopedics', 'General Medicine']
        diagnoses = {
            'Cardiology': ['Heart Failure', 'Myocardial Infarction'],
            'Orthopedics': ['Hip Fracture', 'Knee Replacement'],
            'General Medicine': ['Pneumonia', 'Diabetes']
        }
        insurance_types = ['Medicare', 'Medicaid', 'Private']
        genders = ['Male', 'Female']

        # Generate 5 sample patients
        for i in range(1, 6):
            department = random.choice(departments)
            severity = random.randint(1, 5)
            base_los = severity * 2
            predicted_los = max(3, np.random.normal(base_los, 1.5))
            days_ago = random.randint(0, 3)
            admission_date = datetime.now() - timedelta(days=days_ago)

            patient = Patient(
                id=f"P{i:03d}",
                admission_date=admission_date,
                predicted_los=predicted_los,
                department=department,
                diagnosis=random.choice(diagnoses[department]),
                age=random.randint(25, 85),
                gender=random.choice(genders),
                insurance=random.choice(insurance_types),
                severity=severity
            )
            
            # Add patient to database
            self.add_patient(patient)
            
            # Generate tracking records (every 8 hours)
            current_time = datetime.now()
            tracking_time = admission_date
            while tracking_time <= current_time:
                current_los = (tracking_time - admission_date).total_seconds() / 86400
                
                vital_signs = {
                    'heart_rate': random.normalvariate(75, 5),
                    'blood_pressure': random.normalvariate(120, 10),
                    'temperature': random.normalvariate(37, 0.3),
                    'oxygen_saturation': min(100, random.normalvariate(98, 1))
                }
                
                self.add_tracking_record(
                    patient.id,
                    tracking_time,
                    current_los,
                    vital_signs
                )
                
                tracking_time += timedelta(hours=8)


    
    def get_patient_data(self, patient_id: str):
        """Get all data for a specific patient"""
        with self.get_connection() as conn:
            # Get patient details
            patient_df = pd.read_sql('''
                SELECT * FROM patients WHERE id = ?
            ''', conn, params=(patient_id,))
            
            # Convert string dates to datetime
            if not patient_df.empty:
                patient_df['admission_date'] = pd.to_datetime(patient_df['admission_date'])
                patient_df['discharge_date'] = pd.to_datetime(patient_df['discharge_date'])
            
            # Get LOS tracking history
            los_df = pd.read_sql('''
                SELECT tracking_date, current_los, vital_signs
                FROM los_tracking 
                WHERE patient_id = ?
                ORDER BY tracking_date
            ''', conn, params=(patient_id,))
            
            # Convert tracking_date to datetime
            if not los_df.empty:
                los_df['tracking_date'] = pd.to_datetime(los_df['tracking_date'])
            
            return patient_df.iloc[0] if not patient_df.empty else None, los_df

    def get_department_stats(self):
        """Get department-wise statistics"""
        with self.get_connection() as conn:
            return pd.read_sql('''
                SELECT 
                    department,
                    COUNT(*) as patient_count,
                    AVG(predicted_los) as avg_predicted_los,
                    AVG(severity) as avg_severity
                FROM patients 
                WHERE status = 'Active'
                GROUP BY department
            ''', conn)

    def get_los_distribution(self):
        """Get LOS distribution data"""
        with self.get_connection() as conn:
            return pd.read_sql('''
                SELECT 
                    p.department,
                    t.current_los
                FROM patients p
                JOIN los_tracking t ON p.id = t.patient_id
                WHERE p.status = 'Active'
                AND t.tracking_date = (
                    SELECT MAX(tracking_date) 
                    FROM los_tracking 
                    WHERE patient_id = p.id
                )
            ''', conn)

    def get_all_active_patients(self):
        """Get all active patients"""
        with self.get_connection() as conn:
            patients_df = pd.read_sql('''
                SELECT 
                    id,
                    admission_date,
                    predicted_los,
                    department,
                    diagnosis,
                    age,
                    gender,
                    insurance,
                    severity,
                    status,
                    discharge_date
                FROM patients 
                WHERE status = 'Active'
                ORDER BY admission_date DESC
            ''', conn)
            
            if not patients_df.empty:
                patients_df['admission_date'] = pd.to_datetime(patients_df['admission_date'])
                patients_df['discharge_date'] = pd.to_datetime(patients_df['discharge_date'])
            
            return patients_df


class LOSMonitor:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.running = False
    
    def calculate_current_los(self, admission_date):
        """Calculate current length of stay"""
        return (datetime.now() - pd.to_datetime(admission_date)).total_seconds() / 86400
    
    def generate_vital_signs(self, baseline_vitals=None):
        """Generate vital signs with small variations"""
        if baseline_vitals:
            return {
                'heart_rate': baseline_vitals['heart_rate'] + random.normalvariate(0, 2),
                'blood_pressure': baseline_vitals['blood_pressure'] + random.normalvariate(0, 3),
                'temperature': baseline_vitals['temperature'] + random.normalvariate(0, 0.1),
                'oxygen_saturation': min(100, baseline_vitals['oxygen_saturation'] + random.normalvariate(0, 0.5))
            }
        else:
            return {
                'heart_rate': random.normalvariate(75, 5),
                'blood_pressure': random.normalvariate(120, 10),
                'temperature': random.normalvariate(37, 0.3),
                'oxygen_saturation': min(100, random.normalvariate(98, 1))
            }
    
    def monitor_loop(self):
        """Continuous monitoring loop"""
        vital_signs_cache = {}  # Cache for maintaining consistent vital signs per patient
        
        while self.running:
            try:
                # Get all active patients
                active_patients = self.db_manager.get_all_active_patients()
                
                for _, patient in active_patients.iterrows():
                    current_los = self.calculate_current_los(patient['admission_date'])
                    
                    # Get or generate baseline vital signs
                    if patient['id'] not in vital_signs_cache:
                        vital_signs_cache[patient['id']] = self.generate_vital_signs()
                    
                    # Generate new vitals based on baseline
                    vital_signs = self.generate_vital_signs(vital_signs_cache[patient['id']])
                    vital_signs_cache[patient['id']] = vital_signs
                    
                    # Add tracking record
                    self.db_manager.add_tracking_record(
                        patient['id'],
                        datetime.now(),
                        current_los,
                        vital_signs
                    )
                    
                    logger.info(f"Updated LOS for patient {patient['id']}: {current_los:.1f} days")
                
                # Sleep for 5 minutes before next check
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait before retrying
    
    def start(self):
        """Start the monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join()

class LOSDashboard:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_los_chart(self, los_df, predicted_los):
        """Create LOS trend chart"""
        fig = go.Figure()
        
        # Convert vital signs string to dict
        vital_signs_data = los_df['vital_signs'].apply(eval)
        
        # Add actual LOS line
        fig.add_trace(go.Scatter(
            x=los_df['tracking_date'],
            y=los_df['current_los'],
            name='Actual LOS',
            line=dict(color='#2563eb', width=2)
        ))
        
        # Add heart rate
        fig.add_trace(go.Scatter(
            x=los_df['tracking_date'],
            y=vital_signs_data.apply(lambda x: x['heart_rate']),
            name='Heart Rate',
            yaxis='y2',
            line=dict(color='#dc2626', width=1, dash='dot')
        ))
        
        # Add predicted LOS reference line
        fig.add_hline(
            y=predicted_los,
            line_dash="dash",
            line_color="red",
            annotation_text="Predicted LOS",
            annotation_position="bottom right"
        )
        
        # Update layout
        fig.update_layout(
            title='Length of Stay and Vital Signs Trends',
            xaxis_title='Date',
            yaxis_title='Days',
            yaxis2=dict(
                title='Heart Rate',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=400,
            template='plotly_white'
        )
        
        return fig

    def create_department_stats_chart(self, stats_df):
        """Create department statistics chart"""
        fig = go.Figure()
        
        # Add bars for patient count
        fig.add_trace(go.Bar(
            x=stats_df['department'],
            y=stats_df['patient_count'],
            name='Patient Count',
            marker_color='#2563eb'
        ))
        
        # Add line for average severity
        fig.add_trace(go.Scatter(
            x=stats_df['department'],
            y=stats_df['avg_severity'],
            name='Avg Severity',
            yaxis='y2',
            line=dict(color='#dc2626', width=2)
        ))
        
        # Update layout
        fig.update_layout(
            title='Department Statistics',
            xaxis_title='Department',
            yaxis_title='Patient Count',
            yaxis2=dict(
                title='Average Severity',
                overlaying='y',
                side='right'
            ),
            height=300,
            template='plotly_white',
            barmode='group'
        )
        
        return fig

    def create_los_distribution_chart(self, los_df):
        """Create LOS distribution chart"""
        fig = px.box(
            los_df,
            x='department',
            y='current_los',
            title='Length of Stay Distribution by Department',
            height=300
        )
        
        fig.update_layout(
            xaxis_title='Department',
            yaxis_title='Length of Stay (Days)',
            template='plotly_white'
        )
        
        return fig

    def run_dashboard(self):
        """Main dashboard interface"""
        st.title('Hospital Length of Stay Monitor')
        
        # Department Overview Section
        st.header('Department Overview')
        col1, col2 = st.columns(2)
        
        with col1:
            # Department statistics
            dept_stats = self.db_manager.get_department_stats()
            if not dept_stats.empty:
                st.plotly_chart(
                    self.create_department_stats_chart(dept_stats),
                    use_container_width=True
                )
            else:
                st.info("No department statistics available.")
        
        with col2:
            # LOS distribution
            los_dist = self.db_manager.get_los_distribution()
            if not los_dist.empty:
                st.plotly_chart(
                    self.create_los_distribution_chart(los_dist),
                    use_container_width=True
                )
            else:
                st.info("No LOS distribution data available.")
        
        # Patient Details Section
        st.header('Patient Details')
        
        # Get all active patients for selection
        active_patients = self.db_manager.get_all_active_patients()
        
        if not active_patients.empty:
            # Patient selector
            patient_id = st.selectbox(
                'Select Patient',
                active_patients['id'].tolist(),
                index=0
            )
            
            patient_data, los_df = self.db_manager.get_patient_data(patient_id)
            
            if patient_data is not None:
                # Patient Info Cards
                col1, col2, col3, col4 = st.columns(4)
                
                current_los = los_df['current_los'].iloc[-1] if not los_df.empty else 0
                
                with col1:
                    st.metric(
                        label="Current LOS",
                        value=f"{current_los:.1f} days"
                    )
                
                with col2:
                    st.metric(
                        label="Predicted LOS",
                        value=f"{patient_data['predicted_los']:.1f} days"
                    )
                
                with col3:
                    is_within_prediction = current_los <= patient_data['predicted_los']
                    status_color = "green" if is_within_prediction else "red"
                    status_text = "Within Prediction" if is_within_prediction else "Exceeds Prediction"
                    
                    st.markdown(
                        f"""
                        <div style='text-align: center;'>
                            <p style='color: gray; margin-bottom: 0;'>Status</p>
                            <p style='color: {status_color}; font-weight: bold; font-size: 1.2em;'>
                                {status_text}
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                with col4:
                    st.metric(
                        label="Severity Level",
                        value=f"Level {patient_data['severity']}"
                    )
                
                # Patient Details
                st.markdown("### Patient Information")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown(f"**Department:** {patient_data['department']}")
                    st.markdown(f"**Diagnosis:** {patient_data['diagnosis']}")
                
                with col2:
                    st.markdown(f"**Age:** {patient_data['age']}")
                    st.markdown(f"**Gender:** {patient_data['gender']}")
                
                with col3:
                    st.markdown(f"**Insurance:** {patient_data['insurance']}")
                    admission_date = pd.to_datetime(patient_data['admission_date'])
                    st.markdown(f"**Admitted:** {admission_date.strftime('%Y-%m-%d %H:%M')}")
                
                # LOS Trends Chart
                if not los_df.empty:
                    st.plotly_chart(
                        self.create_los_chart(los_df, patient_data['predicted_los']),
                        use_container_width=True
                    )
                else:
                    st.info("No LOS tracking data available yet.")
        else:
            st.warning("No active patients in the system.")

def setup_page_styling():
    """Set up custom CSS styling for the dashboard"""
    st.markdown("""
        <style>
        /* Main container styling */
        .main {
            padding: 1rem;
        }
        
        /* Metric container styling */
        div[data-testid="metric-container"] {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }
        
        /* Metric label styling */
        div[data-testid="metric-container"] > div:first-child {
            font-size: 1rem;
            color: #4b5563;
        }
        
        /* Metric value styling */
        div[data-testid="metric-container"] > div:nth-child(2) {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1e3a8a;
        }
        
        /* Chart container styling */
        .stPlotlyChart {
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            padding: 1rem;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }
        
        /* Header styling */
        h1, h2, h3 {
            color: #1e3a8a;
            margin-bottom: 1rem;
        }
        
        /* Selectbox styling */
        .stSelectbox {
            margin-bottom: 1rem;
        }
        
        /* Info message styling */
        .stInfo {
            background-color: #e1effe;
            color: #1e40af;
        }
        
        /* Warning message styling */
        .stWarning {
            background-color: #fef3c7;
            color: #92400e;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_database():
    """Initialize database with sample data if needed"""
    try:
        db_manager = DatabaseManager()
        active_patients = db_manager.get_all_active_patients()
        
        if active_patients.empty:
            status_placeholder = st.empty()
            status_placeholder.text('Initializing database with sample data...')
            db_manager.generate_sample_data()
            status_placeholder.text('Database initialized successfully!')
            time.sleep(2)  # Show success message briefly
            status_placeholder.empty()
        
        return db_manager
    
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        logger.error(f"Database initialization error: {str(e)}", exc_info=True)
        return None

def main():
    # Configure page
    st.set_page_config(
        page_title="Hospital LOS Monitor",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom styling
    setup_page_styling()
    
    try:
        # Initialize database if needed
        if 'db_manager' not in st.session_state:
            db_manager = initialize_database()
            if db_manager is None:
                st.error("Failed to initialize the application. Please check the logs.")
                return
            st.session_state.db_manager = db_manager
        
        # Initialize monitor if needed
        if 'monitor' not in st.session_state:
            monitor = LOSMonitor(st.session_state.db_manager)
            monitor.start()
            st.session_state.monitor = monitor
        
        # Create and run dashboard
        dashboard = LOSDashboard(st.session_state.db_manager)
        dashboard.run_dashboard()
        
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logger.error(f"Application error: {str(e)}", exc_info=True)
    
    finally:
        # Add footer
        st.markdown("""
            <div style='text-align: center; color: #6b7280; padding: 2rem;'>
                Hospital Length of Stay Monitoring System
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()