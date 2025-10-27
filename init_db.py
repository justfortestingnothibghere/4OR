import sqlite3

conn = sqlite3.connect('database/data.db')
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
        location TEXT,
        promo_code TEXT,
        discount INTEGER,
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

# Create promotions table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS promotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        discount INTEGER,
        expiry_date TEXT,
        location TEXT
    )
''')

# Create loyalty table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS loyalty (
        phone TEXT PRIMARY KEY,
        points INTEGER
    )
''')

conn.commit()
conn.close()
print("Database initialized successfully.")