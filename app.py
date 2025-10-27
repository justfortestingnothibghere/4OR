from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
import csv
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = '62ba68718aef3e88e30abca000d1309a'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Database path
DB_PATH = 'database/data.db'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Database connection
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        car_model = request.form['car_model']
        service_type = request.form['service_type']
        date = request.form['date']
        time = request.form['time']
        car_size = request.form['car_size']
        booking_id = str(uuid.uuid4())[:8]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (booking_id, name, phone, car_model, service_type, date, time, car_size, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (booking_id, name, phone, car_model, service_type, date, time, car_size, 'Booked'))
        conn.commit()
        conn.close()

        flash(f'Booking successful! Your Booking ID is {booking_id}', 'success')
        return redirect(url_for('track', booking_id=booking_id))
    
    return render_template('booking.html')

@app.route('/track', methods=['GET', 'POST'])
def track():
    booking = None
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM bookings WHERE booking_id = ?', (booking_id,))
        booking = cursor.fetchone()
        conn.close()
        if not booking:
            flash('Invalid Booking ID', 'danger')
    return render_template('track.html', booking=booking)

@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        rating = request.form['rating']
        message = request.form['message']
        cursor.execute('INSERT INTO reviews (name, rating, message) VALUES (?, ?, ?)', 
                      (name, rating, message))
        conn.commit()
        flash('Review submitted successfully!', 'success')
    
    cursor.execute('SELECT * FROM reviews ORDER BY id DESC')
    reviews = cursor.fetchall()
    conn.close()
    return render_template('reviews.html', reviews=reviews)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            user = User('admin')
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin.html')

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        new_status = request.form['status']
        cursor.execute('UPDATE bookings SET status = ? WHERE booking_id = ?', (new_status, booking_id))
        conn.commit()
        flash('Status updated successfully!', 'success')
    
    cursor.execute('SELECT * FROM bookings')
    bookings = cursor.fetchall()
    cursor.execute('SELECT * FROM reviews')
    reviews = cursor.fetchall()
    conn.close()
    return render_template('admin.html', bookings=bookings, reviews=reviews, admin_view=True)

@app.route('/admin/export_bookings')
@login_required
def export_bookings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings')
    bookings = cursor.fetchall()
    conn.close()
    
    with open('bookings_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Booking ID', 'Name', 'Phone', 'Car Model', 'Service Type', 'Date', 'Time', 'Car Size', 'Status'])
        for booking in bookings:
            writer.writerow([booking['booking_id'], booking['name'], booking['phone'], booking['car_model'],
                           booking['service_type'], booking['date'], booking['time'], booking['car_size'], booking['status']])
    
    return send_file('bookings_export.csv', as_attachment=True)

@app.route('/admin/export_reviews')
@login_required
def export_reviews():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reviews')
    reviews = cursor.fetchall()
    conn.close()
    
    with open('reviews_export.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Rating', 'Message'])
        for review in reviews:
            writer.writerow([review['id'], review['name'], review['rating'], review['message']])
    
    return send_file('reviews_export.csv', as_attachment=True)

@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)