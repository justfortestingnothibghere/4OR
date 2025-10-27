import sqlite3
import sys
import os

def initialize_database(db_path='database/data.db'):
    """
    Initialize the SQLite database with required tables for the Flask application.
    
    Args:
        db_path (str): Path to the SQLite database file.
    
    Returns:
        bool: True if initialization is successful, False otherwise.
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create bookings table with email column
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                car_model TEXT NOT NULL,
                service_type TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                car_size TEXT NOT NULL,
                location TEXT NOT NULL,
                promo_code TEXT,
                discount INTEGER DEFAULT 0,
                status TEXT NOT NULL
            )
        ''')

        # Create reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rating INTEGER NOT NULL,
                message TEXT
            )
        ''')

        # Create promotions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount INTEGER NOT NULL,
                expiry_date TEXT NOT NULL,
                location TEXT NOT NULL
            )
        ''')

        # Create loyalty table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loyalty (
                phone TEXT PRIMARY KEY NOT NULL,
                points INTEGER DEFAULT 0
            )
        ''')

        # Commit changes
        conn.commit()

        # Verify table creation
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        expected_tables = {'bookings', 'reviews', 'promotions', 'loyalty'}
        created_tables = {table[0] for table in tables}
        
        if expected_tables.issubset(created_tables):
            print(f"Database initialized successfully at {db_path}.")
            return True
        else:
            print(f"Error: Not all tables were created. Found: {created_tables}")
            return False

    except sqlite3.Error as e:
        print(f"Database initialization failed: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    # Ensure database directory exists
    db_dir = 'database'
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Initialize the database
    success = initialize_database('database/data.db')
    if not success:
        sys.exit(1)
