import sqlite3
import pandas as pd

def view_database():
    """View all tables and their contents in hospital.db"""
    
    # Connect to the database
    conn = sqlite3.connect('hospital.db')
    
    # Get list of all tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\n=== Database Tables ===")
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        print("=" * (len(table_name) + 7))
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print("\nColumns:")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        # Get and display the data using pandas
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        print("\nData:")
        print(df)
        print("\n" + "-"*50)
    
    conn.close()

def get_patient_summary():
    """Get a summary of patient data"""
    conn = sqlite3.connect('hospital.db')
    
    # Get patient summary
    patient_df = pd.read_sql("""
        SELECT 
            p.id,
            p.department,
            p.diagnosis,
            p.admission_date,
            p.predicted_los,
            COUNT(t.tracking_date) as tracking_records
        FROM patients p
        LEFT JOIN los_tracking t ON p.id = t.patient_id
        GROUP BY p.id
    """, conn)
    
    print("\n=== Patient Summary ===")
    print(patient_df)
    
    conn.close()

def get_recent_vitals():
    """Get most recent vital signs for each patient"""
    conn = sqlite3.connect('hospital.db')
    
    # Get the most recent vital signs for each patient
    query = """
    WITH RankedVitals AS (
        SELECT 
            patient_id,
            tracking_date,
            vital_signs,
            ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY tracking_date DESC) as rn
        FROM los_tracking
    )
    SELECT 
        p.id,
        p.department,
        rv.tracking_date,
        rv.vital_signs
    FROM patients p
    LEFT JOIN RankedVitals rv ON p.id = rv.patient_id AND rv.rn = 1
    """
    
    vitals_df = pd.read_sql(query, conn)
    
    print("\n=== Recent Vital Signs ===")
    print(vitals_df)
    
    conn.close()

if __name__ == "__main__":
    print("Viewing database contents...")
    view_database()
    
    print("\nViewing patient summary...")
    get_patient_summary()
    
    print("\nViewing recent vital signs...")
    get_recent_vitals()