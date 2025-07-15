import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

class ParkingSystem:
    def __init__(self):
        # Connexion lors de l'instanciation
        self.conn = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='root',
            database='Parking_App'
        )

    def _execute_query(self, query, params=None, fetch=False):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
            cursor.close()
            return result
        self.conn.commit()
        last_id = cursor.lastrowid
        cursor.close()
        return last_id

    def get_database_structure(self):
        """Get information about existing tables"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            cursor.close()
            
            table_info = {}
            for table in tables:
                table_name = table[0]
                cursor = self.conn.cursor()
                cursor.execute(f"DESCRIBE {table_name}")
                columns = cursor.fetchall()
                cursor.close()
                table_info[table_name] = columns
            
            return table_info
        except Exception as e:
            print(f"Error getting database structure: {e}")
            return {}

    def add_city(self, name):
        existing = self._execute_query("SELECT city_id FROM cities WHERE name = %s", (name,), fetch=True)
        if existing:
            return existing[0]['city_id']
        return self._execute_query("INSERT INTO cities (name) VALUES (%s)", (name,))

    def get_all_cities(self):
        return self._execute_query("SELECT * FROM cities", fetch=True)

    def get_municipalities_by_city(self, city_id):
        """Get municipalities for a specific city"""
        try:
            return self._execute_query(
                "SELECT * FROM municipalities WHERE city_id = %s ORDER BY name",
                (city_id,),
                fetch=True
            )
        except:
            return []

    def get_zones_by_municipality(self, municipality_id):
        """Get zones for a specific municipality"""
        try:
            return self._execute_query(
                "SELECT * FROM zones WHERE mun_id = %s ORDER BY name",
                (municipality_id,),
                fetch=True
            )
        except:
            return []

    def get_available_spots_by_zone(self, zone_id):
        """Get available spots for a specific zone"""
        try:
            return self._execute_query(
                """
                SELECT s.*, pl.name as location, pl.address, pl.hourly_rate as price_per_hour,
                       z.name as zone_name, m.name as municipality_name, c.name as city_name,
                       c.city_id, m.mun_id, z.zone_id
                FROM slots s
                LEFT JOIN parking_lots pl ON s.lot_id = pl.lot_id
                LEFT JOIN zones z ON pl.zone_id = z.zone_id
                LEFT JOIN municipalities m ON z.mun_id = m.mun_id
                LEFT JOIN cities c ON m.city_id = c.city_id
                WHERE s.status = 'AVAILABLE' AND pl.is_active = TRUE AND pl.zone_id = %s
                """,
                (zone_id,),
                fetch=True
            )
        except:
            return []

    def authenticate(self, login_identifier, password):
        # Try to find user by email or phone
        user = self._execute_query(
            "SELECT * FROM users WHERE (email = %s OR phone = %s) AND password_hash = %s",
            (login_identifier, login_identifier, password),
            fetch=True
        )
        
        if user:
            user_data = user[0]
            return {'id': user_data['user_id'], 'role': 'USER'}

        # Try admin authentication
        admin = self._execute_query(
            "SELECT * FROM admins WHERE email = %s AND password_hash = %s",
            (login_identifier, password),
            fetch=True
        )
        
        if admin:
            admin_data = admin[0]
            return {'id': admin_data['admin_id'], 'role': 'ADMIN'}

        return None

    def get_user_by_phone(self, phone):
        """Check if a user exists with the given phone number"""
        user = self._execute_query(
            "SELECT * FROM users WHERE phone = %s",
            (phone,),
            fetch=True
        )
        return user[0] if user else None

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        user = self._execute_query(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,),
            fetch=True
        )
        return user[0] if user else None

    def create_user(self, phone, email, password, vehicle_plate):
        """Create a new user in the database with plain text password"""
        user_id = self._execute_query(
            "INSERT INTO users (phone, email, password_hash, vehicle_plate) VALUES (%s, %s, %s, %s)",
            (phone, email, password, vehicle_plate)
        )
        return {'id': user_id, 'role': 'USER'}

    # Admin dashboard methods - updated for actual schema
    def get_total_users(self):
        """Get total number of users"""
        try:
            result = self._execute_query("SELECT COUNT(*) as count FROM users", fetch=True)
            return result[0]['count'] if result else 0
        except:
            return 0

    def get_active_reservations(self):
        """Get number of active reservations"""
        try:
            result = self._execute_query(
                "SELECT COUNT(*) as count FROM reservations WHERE status IN ('PENDING', 'PAID')",
                fetch=True
            )
            return result[0]['count'] if result else 0
        except:
            return 0

    def get_total_revenue(self):
        """Get total revenue from completed reservations in GNF"""
        try:
            result = self._execute_query(
                "SELECT SUM(total_price) as total FROM reservations WHERE status = 'COMPLETED'",
                fetch=True
            )
            return result[0]['total'] if result and result[0]['total'] else 0.00
        except:
            return 0.00

    def format_currency(self, amount):
        """Format amount as Guinea Franc"""
        if amount is None:
            return "0 GNF"
        return f"{amount:,.0f} GNF"

    def get_available_spots(self):
        """Get number of available spots"""
        try:
            result = self._execute_query(
                "SELECT COUNT(*) as count FROM slots WHERE status = 'AVAILABLE'",
                fetch=True
            )
            return result[0]['count'] if result else 0
        except:
            return 0

    def get_all_parking_lots(self):
        """Get all parking lots with zone and municipality info"""
        try:
            return self._execute_query(
                """
                SELECT pl.*, z.name as zone_name, m.name as municipality_name, c.name as city_name
                FROM parking_lots pl
                LEFT JOIN zones z ON pl.zone_id = z.zone_id
                LEFT JOIN municipalities m ON z.mun_id = m.mun_id
                LEFT JOIN cities c ON m.city_id = c.city_id
                WHERE pl.is_active = TRUE
                """,
                fetch=True
            )
        except:
            return []

    def get_all_reservations(self):
        """Get all reservations with user and slot info"""
        try:
            return self._execute_query(
                """
                SELECT r.*, u.phone as user_phone, u.email as user_email,
                       CONCAT(u.phone, ' (', COALESCE(u.email, 'No email'), ')') as user_name,
                       s.slot_number, pl.name as lot_name
                FROM reservations r
                LEFT JOIN users u ON r.user_id = u.user_id
                LEFT JOIN slots s ON r.slot_id = s.slot_id
                LEFT JOIN parking_lots pl ON s.lot_id = pl.lot_id
                ORDER BY r.start_time DESC
                """,
                fetch=True
            )
        except:
            return []

    def get_all_users(self):
        """Get all users"""
        try:
            return self._execute_query("SELECT * FROM users ORDER BY user_id DESC", fetch=True)
        except:
            return []

    # User dashboard methods
    def get_user_active_reservations(self, user_id):
        """Get user's active reservations count"""
        try:
            result = self._execute_query(
                "SELECT COUNT(*) as count FROM reservations WHERE user_id = %s AND status IN ('PENDING', 'PAID')",
                (user_id,),
                fetch=True
            )
            return result[0]['count'] if result else 0
        except:
            return 0

    def get_user_total_spent(self, user_id):
        """Get user's total spent"""
        try:
            result = self._execute_query(
                "SELECT SUM(total_price) as total FROM reservations WHERE user_id = %s AND status = 'COMPLETED'",
                (user_id,),
                fetch=True
            )
            return result[0]['total'] if result and result[0]['total'] else 0.00
        except:
            return 0.00

    def get_available_spots_list(self):
        """Get list of available spots with details"""
        try:
            return self._execute_query(
                """
                SELECT s.*, pl.name as location, pl.address, pl.hourly_rate as price_per_hour,
                       z.name as zone_name, m.name as municipality_name, c.name as city_name
                FROM slots s
                LEFT JOIN parking_lots pl ON s.lot_id = pl.lot_id
                LEFT JOIN zones z ON pl.zone_id = z.zone_id
                LEFT JOIN municipalities m ON z.mun_id = m.mun_id
                LEFT JOIN cities c ON m.city_id = c.city_id
                WHERE s.status = 'AVAILABLE' AND pl.is_active = TRUE
                """,
                fetch=True
            )
        except:
            return []

    def get_user_reservations(self, user_id):
        """Get user's reservations"""
        try:
            return self._execute_query(
                """
                SELECT r.*, s.slot_number, pl.name as lot_name
                FROM reservations r
                LEFT JOIN slots s ON r.slot_id = s.slot_id
                LEFT JOIN parking_lots pl ON s.lot_id = pl.lot_id
                WHERE r.user_id = %s
                ORDER BY r.start_time DESC
                """,
                (user_id,),
                fetch=True
            )
        except:
            return []

    def get_cities_with_stats(self):
        """
        Returns a list of cities, each with:
        - parking_lots_count: number of parking lots in all its municipalities/zones
        - total_spots: number of slots in all those parking lots
        """
        query = '''
            SELECT c.*, 
                COUNT(DISTINCT pl.lot_id) AS parking_lots_count,
                COUNT(s.slot_id) AS total_spots
            FROM cities c
            LEFT JOIN municipalities m ON m.city_id = c.city_id
            LEFT JOIN zones z ON z.mun_id = m.mun_id
            LEFT JOIN parking_lots pl ON pl.zone_id = z.zone_id
            LEFT JOIN slots s ON s.lot_id = pl.lot_id
            GROUP BY c.city_id
        '''
        return self._execute_query(query, fetch=True)

    def __enter__(self):
        # Connexion déjà ouverte dans __init__
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.conn.is_connected():
            self.conn.close()