import sqlite3
import os

# Ensure database directory exists
if not os.path.exists('database'):
    os.makedirs('database')

# Database path
DB_PATH = 'database/data.db'

# Create database and tables
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create bookings table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT UNIQUE,
        name TEXT,
        phone TEXT,
        car_model TEXT,
        service_type TEXT,
        date TEXT,
        time TEXT,
        car_size TEXT,
        status TEXT
    )
''')

# Create reviews table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        rating INTEGER,
        message TEXT
    )
''')

conn.commit()
conn.close()
print("Database initialized successfully.")