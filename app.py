# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import sqlite3
import csv
import os
from datetime import datetime, timedelta
import uuid
import secrets
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

# Optional: load local .env if you want during local testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------- App + logging ----------
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', '62ba68718aef3e88e30abca000d1309a')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("team4or")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# ---------- Config ----------
DB_PATH = os.getenv('DB_PATH', 'database/data.db')

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')  # Put this in Render environment variables
FROM_EMAIL = os.getenv('FROM_EMAIL', 'armanhacker900@gmail.com')  # Verified sender in SendGrid
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'khusi9999khan@gmail.com')

# ---------- Simple User class ----------
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# ---------- DB helper ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---------- Email helper using SendGrid ----------
def send_email_sendgrid(to_email: str, subject: str, html_content: str) -> (bool, str):
    """
    Sends email using SendGrid. Returns (success, message).
    """
    if not SENDGRID_API_KEY:
        msg = "SendGrid API key not configured."
        logger.error(msg)
        return False, msg

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        mail = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        response = sg.send(mail)
        # Consider 2xx status codes success
        if 200 <= response.status_code < 300:
            logger.info(f"Email sent to {to_email} (status {response.status_code})")
            return True, f"Sent (status {response.status_code})"
        else:
            logger.warning(f"SendGrid returned {response.status_code}: {response.body}")
            return False, f"SendGrid error {response.status_code}: {response.body}"
    except Exception as e:
        logger.exception("Exception when sending email via SendGrid")
        return False, str(e)

# ---------- Routes ----------
@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        # Read form
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        car_model = request.form.get('car_model', '').strip()
        service_type = request.form.get('service_type', '').strip()
        date = request.form.get('date', '').strip()
        time = request.form.get('time', '').strip()
        car_size = request.form.get('car_size', '').strip()
        location = request.form.get('location', '').strip()
        promo_code = request.form.get('promo_code', '').strip()
        booking_id = str(uuid.uuid4())[:8]

        # Basic validation
        if not (name and email and phone and service_type and date and time):
            flash("Please fill required fields (name, email, phone, service, date, time).", "danger")
            return redirect(url_for('booking'))

        # Validate location
        if location != 'Hyderabad Kukatpally Nexus Mall':
            flash('Bookings are only accepted near Hyderabad Kukatpally Nexus Mall.', 'danger')
            return redirect(url_for('booking'))

        # Validate promo code (if provided)
        discount = 0
        if promo_code:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT discount, expiry_date FROM promotions WHERE code = ?', (promo_code,))
                promo = cursor.fetchone()
                if promo:
                    expiry = promo['expiry_date']
                    try:
                        if datetime.strptime(expiry, '%Y-%m-%d') >= datetime.now():
                            discount = promo['discount']
                        else:
                            flash('Promo code expired.', 'danger')
                    except Exception:
                        flash('Promo code date format invalid on server.', 'warning')
                else:
                    flash('Invalid promo code.', 'danger')
            except Exception as e:
                logger.exception("DB error during promo validation")
                flash('Error validating promo code.', 'danger')
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

        # Save booking into DB
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bookings (booking_id, name, email, phone, car_model, service_type, date, time, car_size, location, promo_code, discount, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (booking_id, name, email, phone, car_model, service_type, date, time, car_size, location, promo_code, discount, 'Booked'))
            conn.commit()
        except Exception as e:
            logger.exception("DB error saving booking")
            flash('Failed to save booking. Try again later.', 'danger')
            return redirect(url_for('booking'))
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

        # Update loyalty points (best-effort)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT points FROM loyalty WHERE phone = ?', (phone,))
            loyalty = cursor.fetchone()
            points = (loyalty['points'] if loyalty else 0) + 1
            cursor.execute('INSERT OR REPLACE INTO loyalty (phone, points) VALUES (?, ?)', (phone, points))
            conn.commit()
        except Exception:
            logger.exception("Failed to update loyalty points")
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

        # Prepare email bodies
        customer_subject = "TEAM 4OR Booking Confirmation"
        customer_html = f"""
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
            </ul>
            <p>Thank you for choosing TEAM 4OR!</p>
        """

        admin_subject = "New Booking Received - TEAM 4OR"
        admin_html = f"""
            <h2>New Booking Notification</h2>
            <p>A new booking has been received:</p>
            <ul>
                <li><strong>Booking ID:</strong> {booking_id}</li>
                <li><strong>Name:</strong> {name}</li>
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
            <p>Please check the admin dashboard for details.</p>
        """

        # Send customer email (best-effort)
        cust_ok, cust_msg = send_email_sendgrid(email, customer_subject, customer_html)
        if not cust_ok:
            flash(f"Booking saved but customer email failed: {cust_msg}", "warning")
            logger.warning(f"Customer email failed: {cust_msg}")
        else:
            logger.info("Customer email delivered")

        # Send admin notification (best-effort)
        admin_ok, admin_msg = send_email_sendgrid(ADMIN_EMAIL, admin_subject, admin_html)
        if not admin_ok:
            logger.warning(f"Admin notification failed: {admin_msg}")

        flash(f'Booking successful! Your Booking ID is {booking_id}.', 'success')
        return redirect(url_for('track', booking_id=booking_id))

    return render_template('booking.html')


@app.route('/track', methods=['GET', 'POST'])
def track():
    booking = None
    if request.method == 'POST':
        booking_id = request.form.get('booking_id', '').strip()
        if not booking_id:
            flash('Please enter Booking ID.', 'warning')
            return redirect(url_for('track'))
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM bookings WHERE booking_id = ?', (booking_id,))
            booking = cursor.fetchone()
            if not booking:
                flash('Invalid Booking ID', 'danger')
        except Exception:
            logger.exception("DB error fetching booking")
            flash('Error fetching booking details.', 'danger')
        finally:
            try:
                conn.close()
            except Exception:
                pass
    else:
        # Optionally, prefill booking if passed as query param
        b_id = request.args.get('booking_id')
        if b_id:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bookings WHERE booking_id = ?', (b_id,))
                booking = cursor.fetchone()
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    return render_template('track.html', booking=booking)


@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        if request.method == 'POST':
            name = request.form.get('name', 'Anonymous')
            rating = request.form.get('rating', '5')
            message = request.form.get('message', '')
            cursor.execute('INSERT INTO reviews (name, rating, message) VALUES (?, ?, ?)', (name, rating, message))
            conn.commit()
            flash('Review submitted successfully!', 'success')
        cursor.execute('SELECT * FROM reviews ORDER BY id DESC')
        reviews = cursor.fetchall()
    except Exception:
        logger.exception("Error handling reviews")
        flash('Error loading reviews.', 'danger')
        reviews = []
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass
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
        car_type = request.form.get('car_type')
        service_type = request.form.get('service_type')
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
            discount = secrets.randbelow(41) + 10  # ₹10-50
            promo_code = secrets.token_hex(4).upper()
            expiry_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO promotions (code, discount, expiry_date, location) VALUES (?, ?, ?, ?)',
                            (promo_code, discount, expiry_date, 'Hyderabad Kukatpally Nexus Mall'))
                conn.commit()
                flash(f'Promo code {promo_code} generated! ₹{discount} off valid until {expiry_date}.', 'success')
            except Exception:
                logger.exception("Error creating promo")
                flash('Error creating promo code.', 'danger')
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        elif action == 'validate':
            code = request.form.get('promo_code', '').strip()
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('SELECT discount, expiry_date FROM promotions WHERE code = ? AND location = ?',
                            (code, 'Hyderabad Kukatpally Nexus Mall'))
                promo = cursor.fetchone()
                if promo and datetime.strptime(promo['expiry_date'], '%Y-%m-%d') >= datetime.now():
                    flash(f'Promo code valid! ₹{promo["discount"]} off your next booking.', 'success')
                else:
                    flash('Invalid or expired promo code.', 'danger')
            except Exception:
                logger.exception("Error validating promo")
                flash('Error validating promo code.', 'danger')
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
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
        phone = request.form.get('phone', '').strip()
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT points FROM loyalty WHERE phone = ?', (phone,))
            loyalty = cursor.fetchone()
            points = loyalty['points'] if loyalty else 0
            if not loyalty:
                flash('No loyalty points found for this phone number.', 'warning')
        except Exception:
            logger.exception("Error fetching loyalty")
            flash('Error fetching loyalty points.', 'danger')
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return render_template('loyalty.html', points=points, phone=phone)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # TODO: Replace with real auth in production
        if username == 'admin' and password == 'admin123':
            user = User('admin')
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin_login.html')


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    try:
        conn = get_db()
        cursor = conn.cursor()
        if request.method == 'POST':
            booking_id = request.form.get('booking_id')
            new_status = request.form.get('status')
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
    except Exception:
        logger.exception("Error loading admin dashboard")
        flash('Error loading admin data.', 'danger')
        bookings = reviews = promotions = loyalty = []
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return render_template('admin.html', bookings=bookings, reviews=reviews, promotions=promotions, loyalty=loyalty)


@app.route('/admin/export_bookings')
@login_required
def export_bookings():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM bookings')
        bookings = cursor.fetchall()
        with open('bookings.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Booking ID', 'Name', 'Phone', 'Car Model', 'Service Type', 'Date', 'Time', 'Car Size', 'Location', 'Promo Code', 'Discount', 'Status'])
            for booking in bookings:
                writer.writerow([booking['booking_id'], booking['name'], booking['phone'], booking['car_model'],
                                 booking['service_type'], booking['date'], booking['time'], booking['car_size'],
                                 booking['location'], booking['promo_code'], booking['discount'], booking['status']])
        return send_file('bookings.csv', as_attachment=True)
    except Exception:
        logger.exception("Error exporting bookings")
        flash('Failed to export bookings.', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/admin/export_reviews')
@login_required
def export_reviews():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reviews')
        reviews = cursor.fetchall()
        with open('reviews.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Name', 'Rating', 'Message'])
            for review in reviews:
                writer.writerow([review['id'], review['name'], review['rating'], review['message']])
        return send_file('reviews.csv', as_attachment=True)
    except Exception:
        logger.exception("Error exporting reviews")
        flash('Failed to export reviews.', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/admin/export_loyalty')
@login_required
def export_loyalty():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM loyalty')
        loyalty = cursor.fetchall()
        with open('loyalty.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Phone', 'Points'])
            for record in loyalty:
                writer.writerow([record['phone'], record['points']])
        return send_file('loyalty.csv', as_attachment=True)
    except Exception:
        logger.exception("Error exporting loyalty")
        flash('Failed to export loyalty data.', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/admin/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))


# Simple test route to test sendgrid email (useful during deployment)
@app.route('/test_email')
def test_email():
    test_to = request.args.get('to', FROM_EMAIL)
    subject = "Test Email - TEAM 4OR"
    html = "<p>This is a test email from TEAM 4OR app (SendGrid)</p>"
    ok, msg = send_email_sendgrid(test_to, subject, html)
    if ok:
        return f"Test email sent to {test_to} (msg: {msg})"
    else:
        return f"Failed to send test email: {msg}", 500


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    # Use 0.0.0.0 when deploying to render or external host
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
