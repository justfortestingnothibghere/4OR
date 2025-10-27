from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
from datetime import datetime, timedelta
import random
import string
import sendgrid
from sendgrid.helpers.mail import Mail
import bcrypt
import os

app = Flask(__name__)
app.secret_key = '62ba68718aef3e88e30abca000d1309a'  # Replace with a secure key
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name, phone):
        self.id = id
        self.email = email
        self.name = name
        self.phone = phone

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, email, name, phone FROM users WHERE id = ?', (user_id,))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

# Database connection
def get_db_connection():
    conn = sqlite3.connect('data.db')
    conn.row_factory = sqlite3.Row
    return conn

# Send email function
def send_booking_email(name, phone, email, car_model, service_type, date, time, car_size, location, promo_code, discount, booking_id, price):
    sg = sendgrid.SendGridAPIClient(os.environ.get('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'))
    
    # User email (if provided)
    if email:
        message = Mail(
            from_email='armanhacker900@@gmail.com',
            to_emails=email,
            subject=f'Booking Confirmation - TEAM 4OR (ID: {booking_id})',
            html_content=f'''
                <h2>Booking Confirmed!</h2>
                <p>Dear {name},</p>
                <p>Your booking with TEAM 4OR has been successfully placed.</p>
                <p><strong>Booking ID:</strong> {booking_id}</p>
                <p><strong>Car Model:</strong> {car_model}</p>
                <p><strong>Service:</strong> {service_type}</p>
                <p><strong>Date:</strong> {date}</p>
                <p><strong>Time:</strong> {time}</p>
                <p><strong>Car Size:</strong> {car_size}</p>
                <p><strong>Location:</strong> {location}</p>
                <p><strong>Promo Code:</strong> {promo_code or 'None'}</p>
                <p><strong>Discount:</strong> ₹{discount}</p>
                <p><strong>Total Price:</strong> ₹{price - discount}</p>
                <p>Thank you for choosing TEAM 4OR!</p>
            '''
        )
        try:
            sg.send(message)
        except Exception as e:
            print(f"Error sending user email: {e}")

    # Admin email
    admin_message = Mail(
        from_email='armanhacker900@gmail.com',
        to_emails='khusi9999khan@gmail.com',  # Replace with your actual admin email
        subject=f'New Booking Received - ID: {booking_id}',
        html_content=f'''
            <h2>New Booking Details</h2>
            <p><strong>Booking ID:</strong> {booking_id}</p>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Phone:</strong> {phone}</p>
            <p><strong>Email:</strong> {email or 'Not provided'}</p>
            <p><strong>Car Model:</strong> {car_model}</p>
            <p><strong>Service:</strong> {service_type}</p>
            <p><strong>Date:</strong> {date}</p>
            <p><strong>Time:</strong> {time}</p>
            <p><strong>Car Size:</strong> {car_size}</p>
            <p><strong>Location:</strong> {location}</p>
            <p><strong>Promo Code:</strong> {promo_code or 'None'}</p>
            <p><strong>Discount:</strong> ₹{discount}</p>
            <p><strong>Total Price:</strong> ₹{price - discount}</p>
        '''
    )
    try:
        sg.send(admin_message)
    except Exception as e:
        print(f"Error sending admin email: {e}")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        phone = request.form['phone']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (email, password, name, phone, photo) VALUES (?, ?, ?, ?, ?)',
                      (email, hashed_password, name, phone, 'default.jpg'))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'danger')
        conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            login_user(User(user['id'], user['email'], user['name'], user['phone']))
            flash('Logged in successfully!', 'success')
            return redirect(url_for('profile'))
        flash('Invalid email or password!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (current_user.id,))
    user = c.fetchone()
    c.execute('SELECT * FROM bookings WHERE user_id = ?', (current_user.id,))
    bookings = c.fetchall()
    c.execute('SELECT AVG(rating) as avg_rating FROM reviews WHERE user_id = ?', (current_user.id,))
    avg_rating = c.fetchone()['avg_rating'] or 0.0
    conn.close()

    if request.method == 'POST':
        name = request.form.get('name', user['name'])
        phone = request.form.get('phone', user['phone'])
        photo = request.files.get('photo')
        photo_path = user['photo']
        if photo:
            photo_filename = f"{current_user.id}_{photo.filename}"
            photo.save(os.path.join('static/images', photo_filename))
            photo_path = photo_filename
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE users SET name = ?, phone = ?, photo = ? WHERE id = ?',
                  (name, phone, photo_path, current_user.id))
        conn.commit()
        conn.close()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user, bookings=bookings, avg_rating=avg_rating)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form.get('email', '')
        car_model = request.form['car_model']
        service_type = request.form['service_type']
        date = request.form['date']
        time = request.form['time']
        car_size = request.form['car_size']
        location = request.form['location']
        promo_code = request.form.get('promo_code', '')
        discount = 0.0
        user_id = current_user.id if current_user.is_authenticated else None

        # Check booking availability
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) as count FROM bookings WHERE date = ? AND time = ? AND location = ?',
                  (date, time, location))
        count = c.fetchone()['count']
        if count >= 5:  # Limit to 5 bookings per slot
            flash('Selected time slot is fully booked!', 'danger')
            conn.close()
            return redirect(url_for('booking'))

        # Validate promo code
        if promo_code:
            c.execute('SELECT discount FROM promotions WHERE code = ? AND expiry_date > ?', 
                      (promo_code, datetime.now().strftime('%Y-%m-%d')))
            promo = c.fetchone()
            if promo:
                discount = promo['discount']
            else:
                flash('Invalid or expired promo code!', 'danger')
                conn.close()
                return redirect(url_for('booking'))

        # Calculate price
        price = {
            'Normal Wash': {'Small': 700, 'Large': 800},
            'Body Wash': {'Small': 600, 'Large': 700},
            'Wax': {'Small': 3299, 'Large': 3299},
            'Teflon': {'Small': 3499, 'Large': 3499},
            'Interior Deep Cleaning': {'Small': 4000, 'Large': 4000},
            'Ceramic Coating': {'Small': 5000, 'Large': 5000},
            'Dog Hair Removal': {'Small': 1000, 'Large': 1200}
        }.get(service_type, {}).get(car_size, 0)

        # Insert booking
        c.execute('INSERT INTO bookings (user_id, name, phone, car_model, service_type, date, time, car_size, location, promo_code, discount, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                  (user_id, name, phone, car_model, service_type, date, time, car_size, location, promo_code, discount, 'Pending'))
        booking_id = c.lastrowid

        # Update user stats
        if user_id:
            c.execute('UPDATE users SET total_washes = total_washes + 1, total_spent = total_spent + ?, successful_washes = successful_washes + 1 WHERE id = ?',
                      (price - discount, user_id))
            c.execute('INSERT INTO loyalty (user_id, points) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET points = points + 1',
                      (user_id, 1))
        conn.commit()
        conn.close()

        # Send confirmation emails
        send_booking_email(name, phone, email, car_model, service_type, date, time, car_size, location, promo_code, discount, booking_id, price)
        flash('Booking successful! Check your email for confirmation (if provided).', 'success')
        return redirect(url_for('track'))

    # Get available time slots
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT date, time, COUNT(*) as count FROM bookings WHERE location = ? GROUP BY date, time', ('Hyderabad Kukatpally Nexus Mall',))
    booked_slots = c.fetchall()
    conn.close()
    available_slots = []
    today = datetime.now().date()
    for i in range(7):  # Next 7 days
        date = (today + timedelta(days=i)).strftime('%Y-%m-%d')
        for hour in range(9, 18):  # 9 AM to 5 PM
            time = f'{hour:02d}:00'
            count = next((slot['count'] for slot in booked_slots if slot['date'] == date and slot['time'] == time), 0)
            if count < 5:
                available_slots.append({'date': date, 'time': time})
    
    return render_template('booking.html', available_slots=available_slots)

@app.route('/gallery')
def gallery():
    # Sample images for gallery (replace with actual customer photos)
    images = [
        {'url': url_for('static', filename='images/before.jpg'), 'caption': 'Before Wash'},
        {'url': url_for('static', filename='images/after.jpg'), 'caption': 'After Wash'},
        {'url': url_for('static', filename='images/promo.jpg'), 'caption': 'Ceramic Coating Result'},
    ]
    return render_template('gallery.html', images=images)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email == 'admin@team4or.com' and password == 'admin123':  # Replace with secure authentication
            session['admin'] = True
            flash('Admin logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials!', 'danger')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users')
    users = c.fetchall()
    c.execute('SELECT * FROM bookings')
    bookings = c.fetchall()
    c.execute('SELECT * FROM reviews')
    reviews = c.fetchall()
    c.execute('SELECT * FROM promotions')
    promotions = c.fetchall()
    c.execute('SELECT * FROM loyalty')
    loyalty = c.fetchall()
    # Analytics
    c.execute('SELECT COUNT(*) as total_bookings, SUM(total_spent) as total_revenue FROM users')
    analytics = c.fetchone()
    conn.close()
    return render_template('admin_dashboard.html', users=users, bookings=bookings, reviews=reviews, promotions=promotions, loyalty=loyalty, analytics=analytics)

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    c.execute('DELETE FROM bookings WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM reviews WHERE user_id = ?', (user_id,))
    c.execute('DELETE FROM loyalty WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_booking/<int:booking_id>', methods=['POST'])
def update_booking(booking_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    status = request.form['status']
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE bookings SET status = ? WHERE id = ?', (status, booking_id))
    conn.commit()
    conn.close()
    flash('Booking status updated!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_review/<int:review_id>')
def delete_review(review_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
    conn.commit()
    conn.close()
    flash('Review deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Placeholder for Razorpay payment (enable when ready)
# @app.route('/pay/<int:booking_id>', methods=['POST'])
# def pay(booking_id):
#     import razorpay
#     client = razorpay.Client(auth=("YOUR_KEY_ID", "YOUR_KEY_SECRET"))
#     # Create order and redirect to payment page
#     pass

if __name__ == '__main__':
    app.run(debug=True)
