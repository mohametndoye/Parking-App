from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_cors import CORS
# from backend.parking_system import ParkingSystem
from parking_system import ParkingSystem
import os
from datetime import datetime

app = Flask(
    __name__,
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend/templates')),
    static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../static'))
)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.getenv('SECRET_KEY', 'mysecret')  # idéalement en .env

# API Routes for hierarchical selection
@app.route('/cities')
def get_cities():
    with ParkingSystem() as db:
        cities = db.get_all_cities()
    return jsonify(cities)

@app.route('/municipalities/by-city/<int:city_id>')
def get_municipalities_by_city(city_id):
    with ParkingSystem() as db:
        municipalities = db.get_municipalities_by_city(city_id)
    return jsonify(municipalities)

@app.route('/zones/by-municipality/<int:municipality_id>')
def get_zones_by_municipality(municipality_id):
    if not municipality_id or municipality_id < 1:
        return jsonify({"error": "Invalid municipality ID"}), 400

    with ParkingSystem() as db:
        zones = db.get_zones_by_municipality(municipality_id)
    return jsonify(zones)

@app.route('/spots/by-zone/<int:zone_id>')
def get_spots_by_zone(zone_id):
    with ParkingSystem() as db:
        spots = db.get_available_spots_by_zone(zone_id)
    return jsonify(spots)

# Debug route to check database structure
@app.route('/debug/db')
def debug_database():
    with ParkingSystem() as db:
        structure = db.get_database_structure()
        return f"<h1>Database Structure</h1><pre>{structure}</pre>"

# Test route for frontend debugging
@app.route('/test')
def test_frontend():
    return render_template('test_frontend.html')

# Landing page redirige vers login
@app.route('/')
def landing():
    return render_template('index.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get either email or phone from the form
        email = request.form.get('email', '')
        phone = request.form.get('phone', '')
        password = request.form['password']
        
        # Use email if provided, otherwise use phone
        login_identifier = email if email else phone
        
        if not login_identifier:
            return "Please provide either email or phone number", 400

        with ParkingSystem() as db:
            user = db.authenticate(login_identifier, password)

        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            if user['role'] == 'ADMIN':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            return "Incorrect email/phone or password", 401

    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form.get('email', '')
        password = request.form['password']
        vehicle_plate = request.form.get('vehicle_plate', '')

        # 1. Validate data
        if not phone or not password:
            return "Missing required fields", 400

        # 2. Check if user exists
        with ParkingSystem() as db:
            existing_user = db.get_user_by_phone(phone)
            if existing_user:
                return "Phone number already registered", 400

        # 3. Save password as plain text (no hashing)
        with ParkingSystem() as db:
            new_user = db.create_user(phone, email, password, vehicle_plate)

        # 4. Log user in
        session['user_id'] = new_user['id']
        session['role'] = new_user['role']
        
        return redirect(url_for('user_dashboard'))

    return render_template('register.html')

# Admin dashboard - protégé
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'ADMIN':
        return redirect(url_for('login'))
    
    # Get data for admin dashboard
    with ParkingSystem() as db:
        # Get statistics
        total_users = db.get_total_users()
        active_reservations = db.get_active_reservations()
        total_revenue_raw = db.get_total_revenue()
        total_revenue_formatted = db.format_currency(total_revenue_raw)
        available_spots = db.get_available_spots()
        
        # Get lists for management
        cities = db.get_cities_with_stats()  # <-- use new method
        parking_lots = db.get_all_parking_lots()
        reservations = db.get_all_reservations()
        users = db.get_all_users()
    
    return render_template('admin.html', 
                         total_users=total_users,
                         active_reservations=active_reservations,
                         total_revenue=total_revenue_formatted,
                         available_spots=available_spots,
                         cities=cities,
                         parking_lots=parking_lots,
                         reservations=reservations,
                         users=users)

# User dashboard - protégé
@app.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'USER':
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    
    # Get data for user dashboard
    with ParkingSystem() as db:
        # Get user info
        user = db.get_user_by_id(user_id)
        
        # Get user statistics
        active_reservations = db.get_user_active_reservations(user_id)
        total_spent_raw = db.get_user_total_spent(user_id)
        total_spent_formatted = db.format_currency(total_spent_raw)
        available_spots = db.get_available_spots()
        
        # Get lists for user
        cities = db.get_all_cities()
        available_spots_list = db.get_available_spots_list()
        user_reservations = db.get_user_reservations(user_id)
    
    return render_template('user.html',
                         user=user,
                         active_reservations=active_reservations,
                         total_spent=total_spent_formatted,
                         available_spots=available_spots,
                         cities=cities,
                         available_spots_list=available_spots_list,
                         user_reservations=user_reservations)

# Reservation page
@app.route('/reservation')
def reservation_page():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    # Get data for reservation page
    with ParkingSystem() as db:
        cities = db.get_all_cities()
        available_spots = db.get_available_spots_list()
        today_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('reservation.html',
                         cities=cities,
                         available_spots=available_spots,
                         today_date=today_date)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Add this temporary route for testing
@app.route('/test-zones')
def test_zones():
    with ParkingSystem() as db:
        zones = db.get_zones_by_municipality(3)  # Test with ID 1
    return jsonify({"zones": zones})


if __name__ == '__main__':
    app.run(debug=True, port=5001)