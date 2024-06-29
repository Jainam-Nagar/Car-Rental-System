from flask import Flask, flash, jsonify, render_template, request, redirect, send_from_directory, session, Response, url_for
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, datetime, os

app = Flask(__name__, static_folder='static')
app.config.update(
    UPLOAD_FOLDER='uploads',
    SECRET_KEY='-\xf8\x9e\x86\xe2$\xc4\x9f\x0el\x15\x9a\xb2\x18\xa1\xf4U|_\xbc\xbf\xc0vD'
)
csrf = CSRFProtect(app)

# Ensure the upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Connect to the SQLite database
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Create tables for admins and clients
c.execute('''CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE,
                password TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE,
                password TEXT
            )''')

# Create a table to store car information
c.execute('''CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY,
                make TEXT,
                model TEXT,
                year INTEGER,
                daily_rate REAL,
                owner_id INTEGER,
                cover_image TEXT,
                images TEXT,
                availability TEXT,
                FOREIGN KEY(owner_id) REFERENCES admins(id)
            )''')


# Create a table to store booking information
c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY,
                car_id INTEGER,
                client_id INTEGER,
                start_date DATE,
                end_date DATE,
                status TEXT DEFAULT 'Pending',  -- Add default value for status
                FOREIGN KEY(car_id) REFERENCES cars(id),
                FOREIGN KEY(client_id) REFERENCES clients(id)
            )''')

# Close the database connection
conn.close()

# Function to register a new admin
def register_admin(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    try:
        c.execute('''INSERT INTO admins (email, password) VALUES (?, ?)''', (email, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return False  # Return False if admin already exists
    conn.close()
    return True  # Return True if registration is successful

# Function to register a new client
def register_client(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    try:
        c.execute('''INSERT INTO clients (email, password) VALUES (?, ?)''', (email, hashed_password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        return False  # Return False if client already exists
    conn.close()
    return True  # Return True if registration is successful


# Function to validate admin login
def login_admin(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM admins WHERE email = ?''', (email,))
    admin = c.fetchone()
    conn.close()
    if admin and check_password_hash(admin[2], password):
        return admin
    else:
        return None

# Function to validate client login
def login_client(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM clients WHERE email = ?''', (email,))
    client = c.fetchone()
    conn.close()
    if client and check_password_hash(client[2], password):
        return client
    else:
        return None
    
# Function to fetch all cars
def fetch_available_cars():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT id, make, model, year, daily_rate, cover_image, availability FROM cars WHERE availability = "Available"''')
    cars = c.fetchall()
    conn.close()
    return cars

def fetch_client_summary_data(client_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Fetch total bookings
    c.execute('''SELECT COUNT(id) FROM bookings WHERE client_id = ?''', (client_id,))
    total_bookings = c.fetchone()[0]
    
    # Fetch total spending
    c.execute('''SELECT SUM(cars.daily_rate) 
                FROM cars JOIN bookings ON cars.id = bookings.car_id
                WHERE bookings.client_id = ? and bookings.status = "Approved"''', (client_id,))
    total_spending = c.fetchone()[0]
    conn.close()
    
    if total_bookings is None:
        total_bookings = 0.0
    if total_spending is None:
        total_spending = 0.0

    return {
        'total_bookings': total_bookings,
        'total_spending': total_spending
    }
    
# Function to fetch bookings for the current client
def fetch_client_bookings(client_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT b.id, c.make || ' ' || c.model AS car_name, b.start_date, b.end_date, c.daily_rate, b.status, c.cover_image
                 FROM bookings b
                 JOIN cars c ON b.car_id = c.id
                 WHERE b.client_id = ?''', (client_id,))
    bookings = c.fetchall()
    conn.close()
    return bookings

# Function to fetch summary data for the current admin
def fetch_admin_summary_data(admin_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Fetch total number of cars belonging to the admin
        c.execute('''SELECT COUNT(*) FROM cars WHERE owner_id = ?''', (admin_id,))
        total_cars = c.fetchone()[0]
        
        # Fetch count of active bookings for cars belonging to the admin
        today = datetime.date.today()
        c.execute('''
            SELECT COUNT(*)
            FROM bookings b JOIN cars c ON b.car_id = c.id
            WHERE c.owner_id = ? AND start_date <= ? AND end_date >= ?
        ''', (admin_id, today, today))
        active_bookings = c.fetchone()[0]
        
        # Fetch total revenue from bookings for cars belonging to the admin
        c.execute('''SELECT IFNULL(SUM((julianday(end_date) - julianday(start_date)) * daily_rate), 0) 
                    FROM bookings b JOIN cars c ON b.car_id = c.id
                    WHERE c.owner_id = ?''', (admin_id,))
        total_revenue = c.fetchone()[0]
        if total_revenue is None:
            total_revenue = 0

        # Fetch average daily rate of cars belonging to the admin
        c.execute('''SELECT AVG(daily_rate) FROM cars WHERE owner_id = ?''', (admin_id,))
        average_daily_rate = c.fetchone()[0]
        if average_daily_rate is None:
            average_daily_rate=0

        conn.close()
        return total_cars, active_bookings, total_revenue, average_daily_rate
    except Exception as e:
        conn.rollback()
        conn.close()
        print("Error fetching summary data:", e)
        return None, None, None, None
    
# Function to fetch car data for the current admin
def fetch_admin_car_data(admin_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT id, make, model, year, daily_rate, cover_image, availability FROM cars WHERE owner_id = ?''', (admin_id,))
    cars = c.fetchall()
    conn.close()
    return cars

# Function to fetch booking data for the current admin
def fetch_admin_booking_data(admin_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT b.id, u.email AS client_email, c.make || ' ' || c.model AS car, b.start_date, b.end_date, b.status
                 FROM bookings b
                 JOIN cars c ON b.car_id = c.id
                 JOIN clients u ON b.client_id = u.id
                 WHERE c.owner_id = ?''', (admin_id,))
    bookings = c.fetchall()
    conn.close()
    return bookings


# Define a function to retrieve the admin ID from the database
def get_admin_id(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT id FROM admins WHERE email = ?''', (email,))
    admin = c.fetchone()
    conn.close()
    return admin[0] if admin else None

# Define a function to retrieve the client ID from the database
def get_client_id(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT id FROM clients WHERE email = ?''', (email,))
    client = c.fetchone()
    conn.close()
    return client[0] if client else None

# Define a function to retrieve admin information by email
def get_admin_by_email(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM admins WHERE email = ?''', (email,))
    admin = c.fetchone()
    conn.close()
    return admin

# Define a function to retrieve client information by email
def get_client_by_email(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM clients WHERE email = ?''', (email,))
    client = c.fetchone()
    conn.close()
    return client

# Helper function to add cache control headers to responses
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    return response

@app.route('/')
def index():
    cars = fetch_available_cars()
    if cars is not None:
        response = Response(render_template('index.html', cars=cars))
        return add_no_cache_headers(response)
    else:
        return "Failed to retrieve cars data. Please try again later."
    
@app.route('/rent_cars')
def rent_cars():
    cars = fetch_available_cars()
    if cars is not None:
        response = Response(render_template('rent_cars.html', cars=cars))
        return add_no_cache_headers(response)
    else:
        return "Failed to retrieve cars data. Please try again later."

# Function to handle client login
@app.route('/client_login', methods=['GET', 'POST'])
def client_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate client login
        client = login_client(email, password)
        if client:
            session['is_client'] = True
            session['email'] = email
            client_id = get_client_id(email)
            if client_id:
                summary_data = fetch_client_summary_data(client_id)
                total_bookings = summary_data['total_bookings']
                total_spending = summary_data['total_spending']
                response = Response(render_template('client_dashboard.html', total_bookings=total_bookings, total_spending=total_spending))
                return add_no_cache_headers(response)
            else:
                error = 'Client ID not found.'
                response = Response(render_template('client_login.html', error=error))
                return add_no_cache_headers(response)
        else:
            error = 'Invalid email or password.'
            response = Response(render_template('client_login.html', error=error))
            return add_no_cache_headers(response)
    else:
        session.pop('is_client', None)
        session.pop('email', None)
        return render_template('client_login.html', error=None, email=None)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate admin login
        admin = login_admin(email, password)
        if admin:
            session['is_admin'] = True
            session['email'] = email
            admin_id = get_admin_id(email)
            total_cars, active_bookings, total_revenue, average_daily_rate = fetch_admin_summary_data(admin_id)
            response = Response(render_template('dashboard.html', total_cars=total_cars, active_bookings=active_bookings, total_revenue=total_revenue, average_daily_rate=average_daily_rate))
            return add_no_cache_headers(response)
        else:
            error = 'Invalid email or password.'
            response = Response(render_template('admin_login.html', error=error))
            return add_no_cache_headers(response)
    else:
        session.pop('is_admin', None)
        session.pop('email', None)
        return render_template('admin_login.html', error=None, email=None)

# Update signup route
@app.route('/signup/<origin>', methods=['GET', 'POST'])
def signup(origin):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            error = "Passwords do not match."
            return render_template('signup.html', error=error, email=email, origin=origin)
        
        # Check if the email already exists in either admins or clients table
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''SELECT * FROM admins WHERE email = ?''', (email,))
        existing_admin = c.fetchone()
        c.execute('''SELECT * FROM clients WHERE email = ?''', (email,))
        existing_client = c.fetchone()
        
        if (existing_admin and origin == 'admin') or (existing_client and origin == 'admin'):
            return render_template('signup.html', error="Email already exists", email=email, origin=origin)
        
        # Proceed with registration based on origin
        if origin == 'admin':
            if register_admin(email, password):
                return redirect(url_for('admin_login'))
        elif origin == 'client':
            if register_client(email, password):
                return redirect(url_for('client_login'))
        
        conn.close()
    
    return render_template('signup.html', origin=origin)

@app.route('/client_dashboard')
def client_dashboard():
    if session.get('is_client'):
        email = session.get('email')
        client = get_client_by_email(email)
        if client:
            client_id = client[0]
            summary_data = fetch_client_summary_data(client_id)
            total_bookings = summary_data['total_bookings']
            total_spending = summary_data['total_spending']
            response = Response(render_template('client_dashboard.html', total_bookings=total_bookings, total_spending=total_spending))
            return add_no_cache_headers(response)
        else:
            return "Client not found."
    else:
        return redirect(url_for('client_login'))

@app.route('/browse_cars')
def browse_cars():
    cars = fetch_available_cars()
    if cars is not None:
        response = Response(render_template('browse_cars.html', cars=cars))
        return add_no_cache_headers(response)
    else:
        return "Failed to retrieve cars data. Please try again later."
    
# Route to handle renting a car
@app.route('/rent_car', methods=['POST'])
def rent_car():
    data = request.json
    car_id = int(data['car_id'])
    client_id = get_client_id(session.get('email'))
    start_date = data.get('start_date', datetime.date.today())  # Default to today if not provided
    end_date = data.get('end_date', start_date + datetime.timedelta(days=1))  # Default to one day if not provided

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    car = conn.execute('SELECT * FROM cars WHERE id = ?', (car_id,)).fetchone()

    if not car:
        conn.close()
        return jsonify({'success': False, 'error': 'Car not found.'})

    if car[8] != "Available":
        conn.close()
        return jsonify({'success': False, 'error': 'Car is not available for rent.'})

    # Update car availability in the database
    conn.execute('UPDATE cars SET availability = ? WHERE id = ?', ('Unavailable', car_id))

    # Insert the booking into the database
    conn.execute('INSERT INTO bookings (car_id, client_id, start_date, end_date) VALUES (?, ?, ?, ?)',
                 (car_id, client_id, start_date, end_date))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/my_bookings')
def my_bookings():
    if session.get('is_client'):
        client_id = get_client_id(session.get('email'))
        if client_id:
            bookings = fetch_client_bookings(client_id)
            if bookings is not None:
                response = Response(render_template('my_bookings.html', bookings=bookings))
                return add_no_cache_headers(response)
            else:
                return "Failed to retrieve bookings data. Please try again later."
        else:
            return "Client ID not found."
    else:
        flash('Please log in as a client to access this page.', 'error')
        return redirect(url_for('client_login'))

@app.route('/dashboard')
def dashboard():
    if session.get('is_admin'):
        admin_id = get_admin_id(session.get('email'))
        total_cars, active_bookings, total_revenue, average_daily_rate = fetch_admin_summary_data(admin_id)
        if total_cars is not None and total_revenue is not None and active_bookings is not None and average_daily_rate is not None:
            response = Response(render_template('dashboard.html', total_cars=total_cars, active_bookings=active_bookings, total_revenue=total_revenue, average_daily_rate=average_daily_rate))
            return add_no_cache_headers(response)
        else:
            return "Error fetching summary data. Please try again later."
    else:
        return redirect(url_for('admin_login'))

@app.route('/manage_cars')
def manage_cars():
    if session.get('is_admin'):
        admin_id = get_admin_id(session.get('email'))
        cars = fetch_admin_car_data(admin_id)
        response = Response(render_template('manage_cars.html', cars=cars))
        return add_no_cache_headers(response)
    else:
        return redirect(url_for('admin_login'))
    
# Flask route to delete a car
@app.route('/delete_car/<int:car_id>', methods=['POST'])
def delete_car(car_id):
    if session.get('is_admin'):
        # Ensure the user has the correct permissions
        admin_id = get_admin_id(session.get('email'))
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        # Check if the car belongs to the current admin
        c.execute('''SELECT owner_id FROM cars WHERE id = ?''', (car_id,))
        owner_id = c.fetchone()[0]
        if owner_id != admin_id:
            return "Unauthorized", 403  # Return 403 Forbidden if the car does not belong to the current admin
        
        # Delete the car from the database
        c.execute('''DELETE FROM cars WHERE id = ?''', (car_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('manage_cars'))
    else:
        return redirect(url_for('admin_login'))
    
# Flask route to add a car
@app.route('/add_car', methods=['POST'])
def add_car():
    if session.get('is_admin'):
        make = request.form['car_make']
        model = request.form['car_model']
        year = request.form['car_year']
        daily_rate = request.form['daily_rate']
        admin_id = get_admin_id(session.get('email'))
        availability = "Available"
        
        if admin_id:
            # Handle cover image upload
            cover_image = request.files['cover_image']
            cover_filename = secure_filename(cover_image.filename)
            cover_image_path = os.path.join(app.config['UPLOAD_FOLDER'], cover_filename)
            cover_image.save(cover_image_path)
            
            # Handle additional images upload
            additional_images_paths = []
            additional_images = request.files.getlist('additional_images')
            if additional_images:
                for image in additional_images:
                    if image.filename != '':
                        filename = secure_filename(image.filename)
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        image.save(image_path)
                        additional_images_paths.append(image_path)
            
            # Insert car data into the database
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('''INSERT INTO cars (make, model, year, daily_rate, owner_id, cover_image, images, availability) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (make, model, year, daily_rate, admin_id, cover_image_path, ','.join(additional_images_paths), availability))
            conn.commit()
            conn.close()
            
            return redirect(url_for('manage_cars'))
        else:
            return "User ID not found."
    else:
        return redirect(url_for('admin_login'))

@app.route('/manage_bookings', methods=['GET', 'POST'])
def manage_bookings():
    if session.get('is_admin'):
        if request.method == 'POST':
            booking_id = request.form.get('booking_id')
            action = request.form.get('action')
            if action == 'approve':
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('''UPDATE bookings SET status = ? WHERE id = ?''', ('Approved', booking_id))
                conn.commit()
                conn.close()
            elif action == 'reject':
                conn = sqlite3.connect('users.db')
                c = conn.cursor()
                c.execute('''UPDATE bookings SET status = ? WHERE id = ?''', ('Rejected', booking_id))
                booking = c.execute('''SELECT car_id FROM bookings WHERE id = ?''', (booking_id,)).fetchone()
                c.execute('''UPDATE cars SET availability = 'Available' WHERE id = ?''', (booking[0],))
                conn.commit()
                conn.close()
            return redirect(url_for('manage_bookings'))
        else:
            admin_id = get_admin_id(session.get('email'))
            if admin_id:
                bookings = fetch_admin_booking_data(admin_id)
                response = Response(render_template('manage_bookings.html', bookings=bookings))
                return add_no_cache_headers(response)
            else:
                return "User ID not found."
    else:
        return redirect(url_for('admin_login'))

@app.route('/support')
def support():
    response = Response(render_template('support.html', is_admin=session.get('is_admin'), is_client=session.get('is_client')))
    return add_no_cache_headers(response)

@app.route('/logout')
def logout():
    if(session.get('is_admin')):
        response = Response(render_template('admin_login.html'))
        session.pop('is_admin', None)
    else:
        response = Response(render_template('client_login.html'))
        session.pop('is_client', None)
    return add_no_cache_headers(response)

# Add this route to serve uploaded files
@app.route('/uploads/<path:filename>')
def get_uploaded_file(filename):
    return send_from_directory('uploads', filename)

if __name__ == '__main__':
    app.run(debug=True)
