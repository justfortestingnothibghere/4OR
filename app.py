from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
import csv
import os
from datetime import datetime, timedelta
import uuid
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = '62ba68718aef3e88e30abca000d1309a'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Database path
DB_PATH = 'database/data.db'

# SMTP Configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('armanhacker900@gmail.com')
SMTP_PASSWORD = os.getenv('mmge jjmr clrk dqnb')
ADMIN_EMAIL = 'khusi9999khan@gmail.com'

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

# Updated /booking route
@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        car_model = request.form['car_model']
        service_type = request.form['service_type']
        date = request.form['date']
        time = request.form['time']
        car_size = request.form['car_size']
        location = request.form['location']
        promo_code = request.form.get('promo_code', '')
        booking_id = str(uuid.uuid4())[:8]

        # Validate location (only Hyderabad Kukatpally Nexus Mall)
        if location != 'Hyderabad Kukatpally Nexus Mall':
            flash('Bookings are only accepted near Hyderabad Kukatpally Nexus Mall.', 'danger')
            return redirect(url_for('booking'))

        # Validate promo code
        discount = 0
        if promo_code:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT discount, expiry_date FROM promotions WHERE code = ?', (promo_code,))
            promo = cursor.fetchone()
            if promo and datetime.strptime(promo['expiry_date'], '%Y-%m-%d') >= datetime.now():
                discount = promo['discount']
            else:
                flash('Invalid or expired promo code.', 'danger')
            conn.close()

        # Save booking
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (booking_id, name, email, phone, car_model, service_type, date, time, car_size, location, promo_code, discount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (booking_id, name, email, phone, car_model, service_type, date, time, car_size, location, promo_code, discount, 'Booked'))
        conn.commit()

        # Update loyalty points
        cursor.execute('SELECT points FROM loyalty WHERE phone = ?', (phone,))
        loyalty = cursor.fetchone()
        points = (loyalty['points'] if loyalty else 0) + 1  # 1 point per booking
        cursor.execute('INSERT OR REPLACE INTO loyalty (phone, points) VALUES (?, ?)', (phone, points))
        conn.commit()
        conn.close()

        # Send confirmation email to customer and admin notification
        if SMTP_USERNAME and SMTP_PASSWORD:
            try:
                # Connect to SMTP server
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()  # Enable TLS
                server.login(SMTP_USERNAME, SMTP_PASSWORD)

                # Customer confirmation email
                customer_msg = MIMEMultipart()
                customer_msg['From'] = SMTP_USERNAME
                customer_msg['To'] = email
                customer_msg['Subject'] = 'TEAM 4OR Booking Confirmation'
                customer_body = f'''
                    <h2>Booking Confirmed!</h2>
                    <p>Dear {name},</p>
                    <p>Your booking has been confirmed with the following details:</p>
                    <ul>
                        <li><strong>Booking ID:</strong> {booking_id}</li>
                        <li><strong>Car Model:</strong> {car_model}</li>
                        <li><strong>Service:</strong> {service_type}</li>
                        <li><strong>Date:</strong> {date}</li>
                        <li><strong>Time:</strong> {time}</li>
                        <li><strong>Location:</strong> {location}</li>
                        <li><strong>Discount:</strong> ₹{discount}</li>
                    </p>
                    <p>Thank you for choosing TEAM 4OR!</p>
                '''
                customer_msg.attach(MIMEText(customer_body, 'html'))
                server.sendmail(SMTP_USERNAME, email, customer_msg.as_string())

                # Admin notification email
                admin_msg = MIMEMultipart()
                admin_msg['From'] = SMTP_USERNAME
                admin_msg['To'] = ADMIN_EMAIL
                admin_msg['Subject'] = 'New Booking Received - TEAM 4OR'
                admin_body = f'''
                    <h2>New Booking Notification</h2>
                    <p>A new booking has been received with the following details:</p>
                    <ul>
                        <li><strong>Booking ID:</strong> {booking_id}</li>
                        <li><strong>Customer Name:</strong> {name}</li>
                        <li><strong>Email:</strong> {email}</li>
                        <li><strong>Phone:</strong> {phone}</li>
                        <li><strong>Car Model:</strong> {car_model}</li>
                        <li><strong>Service:</strong> {service_type}</li>
                        <li><strong>Date:</strong> {date}</li>
                        <li><strong>Time:</strong> {time}</li>
                        <li><strong>Car Size:</strong> {car_size}</li>
                        <li><strong>Location:</strong> {location}</li>
                        <li><strong>Promo Code:</strong> {promo_code or 'None'}</li>
                        <li><strong>Discount:</strong> ₹{discount}</li>
                    </ul>
                    <p>Please review the booking in the admin dashboard.</p>
                '''
                admin_msg.attach(MIMEText(admin_body, 'html'))
                server.sendmail(SMTP_USERNAME, ADMIN_EMAIL, admin_msg.as_string())

                # Close SMTP connection
                server.quit()

            except Exception as e:
                flash('Booking successful, but email sending failed.', 'warning')
                print(f"SMTP Error: {str(e)}")  # For debugging

        flash(f'Booking successful! Your Booking ID is {booking_id}. Check your email for confirmation.', 'success')
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

@app.route('/services')
def services():
    return render_template('services.html')
    

@app.route('/calculator', methods=['GET', 'POST'])
def calculator():
    fee = None
    car_type = None
    service_type = None
    if request.method == 'POST':
        car_type = request.form['car_type']
        service_type = request.form['service_type']
        
        fees = {
            'Normal Wash': {'Big': 800, 'Hatchback': 700, 'Small': 600},
            'Body Wash': {'Big': 700, 'Hatchback': 600, 'Small': 500}
        }
        fee = fees.get(service_type, {}).get(car_type, 'Contact for pricing')
        if fee != 'Contact for pricing':
            fee = f"₹{fee}"
    
    return render_template('calculator.html', fee=fee, car_type=car_type, service_type=service_type)

@app.route('/promotions', methods=['GET', 'POST'])
def promotions():
    promo_code = None
    discount = None
    expiry_date = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'generate':
            discount = secrets.randbelow(41) + 10  # Random ₹10–₹50
            promo_code = secrets.token_hex(4).upper()  # 8-character code
            expiry_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO promotions (code, discount, expiry_date, location) VALUES (?, ?, ?, ?)',
                          (promo_code, discount, expiry_date, 'Hyderabad Kukatpally Nexus Mall'))
            conn.commit()
            conn.close()
            flash(f'Promo code {promo_code} generated! ₹{discount} off, valid until {expiry_date}.', 'success')
        elif action == 'validate':
            code = request.form['promo_code']
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT discount, expiry_date FROM promotions WHERE code = ? AND location = ?',
                          (code, 'Hyderabad Kukatpally Nexus Mall'))
            promo = cursor.fetchone()
            conn.close()
            if promo and datetime.strptime(promo['expiry_date'], '%Y-%m-%d') >= datetime.now():
                flash(f'Promo code valid! Get ₹{promo["discount"]} off your next booking.', 'success')
            else:
                flash('Invalid or expired promo code.', 'danger')
    
    return render_template('promotions.html', promo_code=promo_code, discount=discount, expiry_date=expiry_date)

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/home')
def home():
    return render_template('index.html')
    


@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/loyalty', methods=['GET', 'POST'])
def loyalty():
    points = 0
    phone = None
    if request.method == 'POST':
        phone = request.form['phone']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT points FROM loyalty WHERE phone = ?', (phone,))
        loyalty = cursor.fetchone()
        points = loyalty['points'] if loyalty else 0
        conn.close()
        if not loyalty:
            flash('No loyalty points found for this phone number.', 'warning')
    
    return render_template('loyalty.html', points=points, phone=phone)

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
    return render_template('admin_login.html')

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
    cursor.execute('SELECT * FROM promotions')
    promotions = cursor.fetchall()
    cursor.execute('SELECT * FROM loyalty')
    loyalty = cursor.fetchall()
    conn.close()
    return render_template('admin.html', bookings=bookings, reviews=reviews, promotions=promotions, loyalty=loyalty)

@app.route('/admin/export_bookings')
@login_required
def export_bookings():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings')
    bookings = cursor.fetchall()
    conn.close()

    with open('bookings.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Booking ID', 'Name', 'Phone', 'Car Model', 'Service Type', 'Date', 'Time', 'Car Size', 'Location', 'Promo Code', 'Discount', 'Status'])
        for booking in bookings:
            writer.writerow([booking['booking_id'], booking['name'], booking['phone'], booking['car_model'],
                           booking['service_type'], booking['date'], booking['time'], booking['car_size'],
                           booking['location'], booking['promo_code'], booking['discount'], booking['status']])
    
    return send_file('bookings.csv', as_attachment=True)

@app.route('/admin/export_reviews')
@login_required
def export_reviews():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reviews')
    reviews = cursor.fetchall()
    conn.close()

    with open('reviews.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Rating', 'Message'])
        for review in reviews:
            writer.writerow([review['id'], review['name'], review['rating'], review['message']])
    
    return send_file('reviews.csv', as_attachment=True)

@app.route('/admin/export_loyalty')
@login_required
def export_loyalty():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM loyalty')
    loyalty = cursor.fetchall()
    conn.close()

    with open('loyalty.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Phone', 'Points'])
        for record in loyalty:
            writer.writerow([record['phone'], record['points']])
    
    return send_file('loyalty.csv', as_attachment=True)

@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
