import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('instance/blood_tests.db')
        cursor = conn.cursor()

        # Add category column to blood_test table
        cursor.execute("ALTER TABLE blood_test ADD COLUMN category VARCHAR(100);")

        # Add category column to blood_test_info table
        cursor.execute("ALTER TABLE blood_test_info ADD COLUMN category VARCHAR(100);")

        # Create vital_sign table
        cursor.execute("""
            CREATE TABLE vital_sign (
                id INTEGER NOT NULL,
                date DATE NOT NULL,
                weight FLOAT,
                heart_rate INTEGER,
                systolic_bp INTEGER,
                diastolic_bp INTEGER,
                PRIMARY KEY (id)
            );
        """)

        conn.commit()
        print("Migration applied successfully.")
    except sqlite3.OperationalError as e:
        print(f"Migration error (might already be applied): {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
