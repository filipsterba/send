import os
import json
import random
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from flask_oauthlib.client import OAuth
from googleapiclient.discovery import build
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

# Configuration paths from app.config
USERS_FILE = app.config['USERS_FILE']
REPAIRS_DATA_FILE = app.config['REPAIRS_DATA_FILE']
REPAIR_SHOPS_FILE = app.config.get('REPAIR_SHOPS_FILE', 'repair_shops_data.json')  # Added constant

# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def load_users():
    """Load users from JSON file, create if doesn't exist"""
    if not os.path.exists(USERS_FILE):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
        return {}
    
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            if not isinstance(users_data, dict):
                app.logger.warning(f"File {USERS_FILE} doesn't contain a valid JSON object. Returning empty dict.")
                return {}
            return users_data
    except json.JSONDecodeError:
        app.logger.error(f"Error decoding JSON from file: {USERS_FILE}")
        return {}
    except Exception as e:
        app.logger.error(f"Unexpected error loading users: {e}")
        return {}

def save_users(users):
    """Save users to JSON file"""
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def save_repair_to_json(repair_data):
    """Save repair data to JSON file"""
    repairs_list = []
    os.makedirs(os.path.dirname(REPAIRS_DATA_FILE), exist_ok=True)
    
    if os.path.exists(REPAIRS_DATA_FILE) and os.path.getsize(REPAIRS_DATA_FILE) > 0:
        try:
            with open(REPAIRS_DATA_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if isinstance(loaded_data, list):
                    repairs_list = loaded_data
                else:
                    app.logger.warning(f"File {REPAIRS_DATA_FILE} doesn't contain a list. Creating new.")
        except json.JSONDecodeError:
            app.logger.warning(f"File {REPAIRS_DATA_FILE} is corrupted. Creating new repair list.")
    
    repairs_list.append(repair_data)
    with open(REPAIRS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(repairs_list, f, indent=2, ensure_ascii=False)

def get_device_icon(device_type):
    """Return appropriate icon class for device type"""
    icons = {
        'phone': 'fa-mobile-alt', 
        'laptop': 'fa-laptop', 
        'tablet': 'fa-tablet-alt',
        'console': 'fa-gamepad', 
        'other': 'fa-microchip'
    }
    return icons.get(str(device_type).lower(), 'fa-tools')

def get_user_data():
    """Get current user data from session"""
    if 'user' in session:
        users = load_users()
        user_email = session['user']
        user_data = users.get(user_email)
        if user_data:
            # Ensure avatar and phone fields exist
            if 'avatar' not in user_data:
                user_data['avatar'] = '/static/img/default-avatar.png'
            if 'phone' not in user_data:
                user_data['phone'] = ''
        return user_data
    return None

# ==========================================================
# OAUTH SETUP
# ==========================================================

oauth = OAuth(app)

google = oauth.remote_app(
    'google',
    consumer_key=app.config['GOOGLE_ID'],
    consumer_secret=app.config['GOOGLE_SECRET'],
    request_token_params={'scope': 'email profile'},
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

facebook = oauth.remote_app(
    'facebook',
    consumer_key=app.config['FACEBOOK_ID'],
    consumer_secret=app.config['FACEBOOK_SECRET'],
    request_token_params={'scope': 'email'},
    base_url='https://graph.facebook.com/',
    request_token_url=None,
    access_token_method='GET',
    access_token_url='/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth'
)

try:
    youtube = build('youtube', 'v3', developerKey=app.config['YOUTUBE_API_KEY'])
    TRUSTED_CHANNELS = [
        'iFixit', 'JerryRigEverything', 'Hugh Jeffreys',
        'Phone Repair Guru', 'REWA Technology', 'fixmyphone'
    ]
except Exception as e:
    app.logger.warning(f"Failed to initialize YouTube API: {e}")
    youtube = None
    TRUSTED_CHANNELS = []

# ==========================================================
# PUBLIC ROUTES
# ==========================================================

@app.route('/')
def index():
    """Homepage - publicly accessible"""
    return render_template('uvod.html', user=get_user_data())

# ==========================================================
# PROTECTED ROUTES - Require authentication
# ==========================================================

@app.route('/about-us')
def about_us():
    """About us page - protected"""
    if 'user' not in session:
        flash("Please log in to access this page", "warning")
        return redirect(url_for('login'))
    return render_template('about-us.html', user=get_user_data())

@app.route('/price-list')
def price_list():
    """Price list page - protected"""
    if 'user' not in session:
        flash("Please log in to access this page", "warning")
        return redirect(url_for('login'))
    return render_template('price-list.html', user=get_user_data())

@app.route('/repair-guides')
def repair_guides():
    """Repair guides and shops page - protected"""
    if 'user' not in session:
        flash("Please log in to access this page", "warning")
        return redirect(url_for('login'))
    return render_template('repair-guides.html', 
                          title="Find Repair Shops",
                          user=get_user_data())

@app.route('/test')
def test():
    """Test endpoint"""
    return "API Test Endpoint - OK"

# Alternative routes for main pages - all publicly accessible
@app.route('/index')
@app.route('/uvod')
def alt_index():
    """Alternative routes to homepage"""
    return redirect(url_for('index'))

@app.route('/home')
def home():
    """Legacy home route"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('index'))

# ==========================================================
# AUTHENTICATION ROUTES
# ==========================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and form handler"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        identity = request.form.get('loginIdentity')
        password = request.form.get('loginPassword')
        
        if not identity or not password:
            flash('Please provide both username/email and password', 'warning')
            return render_template('login.html')
            
        users = load_users()
        user_email_found = None
        
        # Find user by email or username
        for email_key, user_data in users.items():
            if identity == email_key or identity == user_data.get('username'):
                user_email_found = email_key
                break
        
        # Validate password (should use password hashing in production)
        if user_email_found and users[user_email_found].get('password') == password:
            session['user'] = user_email_found
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials or user does not exist', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page and form handler"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('registerUsername')
        email = request.form.get('registerEmail')
        password = request.form.get('registerPassword')  # Should be hashed in production
        
        if not all([username, email, password]):
            flash('All fields are required', 'warning')
            return render_template('register.html')

        users = load_users()
        
        # Check if email is already registered
        if email in users:
            flash('This email is already registered', 'warning')
            return render_template('register.html')
        
        # Check if username is already taken
        for user_data in users.values():
            if user_data.get('username') == username:
                flash('This username is already taken', 'warning')
                return render_template('register.html')

        # Create user
        users[email] = {
            'username': username, 
            'password': password,  # Should be hashed in production
            'avatar': '/static/img/default-avatar.png',
            'phone': ''
        }
        
        save_users(users)
        flash('Registration successful! You can now log in', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    """User logout handler"""
    session.clear()
    flash('You have been successfully logged out', 'info')
    return redirect(url_for('index'))

@app.route('/auth/google')
def google_auth():
    """Google OAuth login initiation"""
    return google.authorize(callback=url_for('google_callback', _external=True))

@app.route('/auth/google/callback')
def google_callback():
    """Google OAuth callback handler"""
    try:
        resp = google.authorized_response()
        if resp is None or resp.get('access_token') is None:
            flash('Google login failed. Please try again', 'danger')
            return redirect(url_for('login'))
        
        user_info = google.get('userinfo', token=(resp['access_token'], '')).data
        email = user_info.get('email')
        
        if not email:
            flash('Could not get email from Google', 'danger')
            return redirect(url_for('login'))
            
        # Create or update user
        users = load_users()
        if email not in users:
            users[email] = {
                'username': user_info.get('name', email.split('@')[0]),
                'password': None,  # OAuth users have no password
                'oauth_provider': 'google',
                'avatar': user_info.get('picture', '/static/img/default-avatar.png'),
                'phone': ''
            }
            save_users(users)
            
        session['user'] = email
        flash('Google login successful!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        app.logger.error(f"Google Auth Error: {e}")
        flash('Error during Google login', 'danger')
        return redirect(url_for('login'))

@app.route('/auth/facebook')
def facebook_auth():
    """Facebook OAuth login initiation"""
    return facebook.authorize(callback=url_for('facebook_callback', _external=True))

@app.route('/auth/facebook/callback')
def facebook_callback():
    """Facebook OAuth callback handler"""
    try:
        resp = facebook.authorized_response()
        if resp is None or resp.get('access_token') is None:
            flash('Facebook login failed. Please try again', 'danger')
            return redirect(url_for('login'))
        
        user_info = facebook.get('/me?fields=email,name', token=(resp['access_token'], '')).data
        email = user_info.get('email')
        
        if not email:
            flash('Facebook login requires email permission', 'warning')
            return redirect(url_for('login'))
            
        # Create or update user
        users = load_users()
        if email not in users:
            users[email] = {
                'username': user_info.get('name', email.split('@')[0]),
                'password': None,  # OAuth users have no password
                'oauth_provider': 'facebook',
                'avatar': f"https://graph.facebook.com/{user_info.get('id')}/picture?type=large" if user_info.get('id') else '/static/img/default-avatar.png',
                'phone': ''
            }
            save_users(users)
            
        session['user'] = email
        flash('Facebook login successful!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        app.logger.error(f"Facebook Auth Error: {e}")
        flash('Error during Facebook login', 'danger')
        return redirect(url_for('login'))

# ==========================================================
# USER ACCOUNT ROUTES
# ==========================================================

@app.route('/dashboard')
def dashboard():
    """User dashboard"""
    if 'user' not in session:
        flash("Please log in to access this page", "warning")
        return redirect(url_for('login'))
        
    user = get_user_data()
    if not user:
        flash("User data not found. Please log in again", "error")
        session.clear()
        return redirect(url_for('login'))
        
    username = user.get('username', 'User')
    return render_template('user-page.html', username=username, user=user)

@app.route('/settings')
def settings():
    """User settings page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = get_user_data()
    if not user:
        return redirect(url_for('logout'))
    
    return render_template('settings.html', title="User Settings", user=user)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    """AJAX endpoint for updating user profile"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        users = load_users()
        user_email = session['user']
        
        if user_email not in users:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Update fields - upraveno pro příjem JSON i form-data
        user_data = users[user_email]
        
        # Zkusíme načíst data z JSON, pokud jsou dostupná
        json_data = request.get_json(silent=True)
        if json_data:
            display_name = json_data.get('displayName')
            phone = json_data.get('phone')
        else:
            # Jinak zkusíme form data
            display_name = request.form.get('displayName')
            phone = request.form.get('phone')
        
        if display_name:
            user_data['username'] = display_name
        if phone:
            user_data['phone'] = phone
        
        save_users(users)
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/change_password', methods=['POST'])
def change_password():
    """AJAX endpoint for changing password"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        users = load_users()
        user_email = session['user']
        
        if user_email not in users:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Zkusíme načíst data z JSON, pokud jsou dostupná
        json_data = request.get_json(silent=True)
        if json_data:
            current_password = json_data.get('oldPassword', '')
            new_password = json_data.get('newPassword', '')
        else:
            # Jinak zkusíme form data
            current_password = request.form.get('currentPassword', '') or request.form.get('oldPassword', '')
            new_password = request.form.get('newPassword', '')
        
        if not new_password:
            return jsonify({'success': False, 'message': 'New password cannot be empty'}), 400
            
        # Kontrola, zda uživatel má heslo (OAuth uživatelé ho nemají)
        stored_password = users[user_email].get('password')
        if stored_password is None:
            # OAuth uživatel - nastavíme nové heslo
            users[user_email]['password'] = new_password
            save_users(users)
            return jsonify({'success': True, 'message': 'Password set successfully'})
        elif stored_password != current_password:
            return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
        
        # Update password (v produkci by mělo být hashované)
        users[user_email]['password'] = new_password
        save_users(users)
        return jsonify({'success': True, 'message': 'Password changed successfully'})
    except Exception as e:
        app.logger.error(f"Error changing password: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==========================================================
# REPAIR MANAGEMENT ROUTES
# ==========================================================

@app.route('/my_repairs')
def my_repairs():
    """User's repair list page"""
    if 'user' not in session:
        flash("Please login to view your repairs", "warning")
        return redirect(url_for('login'))
        
    user = get_user_data()
    if not user:
        flash("User data not found. Please login again", "error")
        session.clear()
        return redirect(url_for('login'))
    
    # Get active and completed repairs
    active_repairs = []
    completed_repairs = []
    
    if os.path.exists(REPAIRS_DATA_FILE):
        try:
            with open(REPAIRS_DATA_FILE, 'r', encoding='utf-8') as f:
                all_repairs = json.load(f)
                
                if isinstance(all_repairs, list):
                    current_user_email = session.get('user')
                    for repair in all_repairs:
                        if repair.get('user_id') == current_user_email:
                            # Add device_name for proper display
                            device_info = repair.get('device_info', {})
                            repair['device_name'] = f"{device_info.get('brand', 'Unknown')} {device_info.get('model', '')}"
                            repair['repair_type'] = device_info.get('issue_description', 'General repair')
                            repair['completed_date'] = repair.get('dates', {}).get('completed', 'Unknown')
                            
                            # Add enhanced status display
                            status_key = repair.get('status_key')
                            if status_key == 'pending':
                                repair['status_display'] = 'Pending Pickup'
                                repair['progress_width'] = 10
                            elif status_key == 'in_progress':
                                repair['status_display'] = 'In Progress'
                                repair['progress_width'] = 50
                            elif status_key == 'waiting_parts':
                                repair['status_display'] = 'Waiting for Parts'
                                repair['progress_width'] = 35
                            elif status_key == 'diagnosed':
                                repair['status_display'] = 'Diagnosed'
                                repair['progress_width'] = 30
                            elif status_key == 'ready':
                                repair['status_display'] = 'Ready for Pickup'
                                repair['progress_width'] = 90
                            elif status_key == 'completed':
                                repair['status_display'] = 'Completed'
                                repair['progress_width'] = 100
                            else:
                                repair['status_display'] = 'Unknown Status'
                                repair['progress_width'] = 0
                            
                            if status_key == 'completed':
                                completed_repairs.append(repair)
                            else:
                                active_repairs.append(repair)
                else:
                    app.logger.warning(f"File {REPAIRS_DATA_FILE} doesn't contain a list")
        except Exception as e:
            app.logger.error(f"Error loading repairs: {e}")
    
    return render_template('repairs.html', 
                          user=user, 
                          active_repairs=active_repairs,
                          completed_repairs=completed_repairs)

@app.route('/repairs/new', methods=['GET'])
def create_repair():
    """Redirect to submit_repair for consistent form handling"""
    return redirect(url_for('submit_repair'))

@app.route('/submit_repair', methods=['GET', 'POST'])
def submit_repair():
    """First step of repair form - device information"""
    if 'user' not in session:
        flash("Please login to submit a repair request", "warning")
        return redirect(url_for('login'))
        
    user = get_user_data()
    if not user:
        flash("User data not found. Please login again", "error")
        session.clear()
        return redirect(url_for('login'))
    
    # Load repair shops for dropdown (even for GET)
    repair_shops = []
    try:
        with open(REPAIR_SHOPS_FILE, "r", encoding="utf-8") as f:
            repair_shops = json.load(f)
    except FileNotFoundError:
        app.logger.error(f"Repair shops file not found: {REPAIR_SHOPS_FILE}")
        flash("Repair shop data is currently unavailable. Please contact support.", "error")
        repair_shops = []
    except json.JSONDecodeError:
        app.logger.error(f"Error decoding JSON from file: {REPAIR_SHOPS_FILE}")
        flash("Error reading repair shop data. Please contact support.", "error")
        repair_shops = []
    except Exception as e:
        app.logger.error(f"Unexpected error loading repair shops: {e}")
        flash("An unexpected error occurred. Please try again later.", "error")
        repair_shops = []
    
    if request.method == 'POST':
        # Save form data to session
        session['repair_form'] = {
            'device_type': request.form.get('deviceType', ''),
            'brand': request.form.get('brand', ''),
            'model': request.form.get('model', ''),
            'issue': request.form.get('issue', ''),
            'full_name': request.form.get('full_name', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'address': request.form.get('address', ''),
            'city': request.form.get('city', ''),
            'zip_code': request.form.get('zip_code', ''),
            'pickupDate': request.form.get('pickupDate', ''),
            'pickupTime': request.form.get('pickupTime', '')
        }

        required_fields = ['device_type', 'brand', 'model', 'issue', 'full_name', 'email', 'phone']
        missing_fields = [field for field in required_fields if not session['repair_form'].get(field)]
        
        if missing_fields:
            flash("Please fill in all required fields", "warning")
            return render_template('submit.html', user=user,
                                   now=datetime.now(),
                                   repair_shops=repair_shops,
                                   form_data=session.get('repair_form', {}))
                                   
        # Filter repair shops based on device_type
        device_type = session['repair_form']['device_type']
        filtered_shops = [shop for shop in repair_shops if device_type in shop.get("supported_devices", [])]
        
        if not filtered_shops:
            flash("No repair shops are currently available for this device type. Please choose a different device type or contact us directly.", "error")
            return render_template('submit.html', user=user,
                                   now=datetime.now(),
                                   repair_shops=repair_shops,
                                   form_data=session.get('repair_form', {}))
        
        if 'photo' in request.files and request.files['photo'].filename:
            photo = request.files['photo']
            filename = secure_filename(photo.filename)
            timestamp = int(datetime.now().timestamp())
            filename = f"temp_{timestamp}_{filename}"
            upload_folder = app.config['UPLOADS_DIR']
            
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
                
            photo_path = os.path.join(upload_folder, filename)
            photo.save(photo_path)
            session['repair_form']['photo_path'] = photo_path
        
        # Store filtered shops in session for select_shop route
        session['filtered_shops'] = filtered_shops
        return redirect(url_for('select_shop'))
    
    # GET request
    return render_template('submit.html', user=user,
                           now=datetime.now(),
                           repair_shops=repair_shops,
                           form_data=session.get('repair_form', {}))

@app.route('/select-shop', methods=['GET', 'POST'])
def select_shop():
    """Second step of repair form - shop selection"""
    if 'user' not in session:
        flash("Please login to submit a repair request", "warning")
        return redirect(url_for('login'))
        
    user = get_user_data()
    if not user:
        flash("User data not found. Please login again", "error")
        session.clear()
        return redirect(url_for('login'))
    
    # Check if first step is completed
    if 'repair_form' not in session:
        flash("Please complete the first step of the form", "warning")
        return redirect(url_for('submit_repair'))
    
    # Use filtered shops from session or load all shops as fallback
    repair_shops = session.get('filtered_shops', [])
    
    # If no shops in session (shouldn't happen), load from file
    if not repair_shops:
        try:
            with open(REPAIR_SHOPS_FILE, "r", encoding="utf-8") as f:
                all_shops = json.load(f)
                
                # Filter by device type
                device_type = session['repair_form'].get('device_type', '')
                repair_shops = [shop for shop in all_shops if device_type in shop.get("supported_devices", [])]
                
                if not repair_shops:
                    flash("No repair shops found for your device type. Please try a different device.", "error")
                    return redirect(url_for('submit_repair'))
        except Exception as e:
            app.logger.error(f"Error loading repair shops: {str(e)}")
            flash("Error loading repair shops. Please try again.", "error")
            return redirect(url_for('submit_repair'))
    
    if request.method == 'POST':
        selected_shop = request.form.get('repair_shop', '')
        
        if not selected_shop:
            flash("Please select a repair shop", "warning")
            return render_template('select_shop.html', user=user,
                                  repair_shops=repair_shops,
                                  device_type=session['repair_form']['device_type'])
        
        try:
            # Generate unique ID and timestamp
            now = datetime.now()
            timestamp = int(now.timestamp() * 1000)
            repair_id = f"REP{timestamp}"
            today = now.strftime('%Y-%m-%d')
            
            # Get shop details
            shop_name = ''
            shop_address = ''
            shop_phone = ''
            
            for shop in repair_shops:
                if str(shop.get('id')) == str(selected_shop):
                    shop_name = shop.get('name', '')
                    shop_address = shop.get('address', '')
                    shop_phone = shop.get('phone', '')
                    break
            
            # Create complete repair data
            form_data = session['repair_form']
            
            # For initial submission, use "pending" status
            status_key = "pending"
            status_display = "Pending Pickup"
            progress_width = 10
            
            # Create timeline events
            timeline_events = [
                {"text": f"Repair request submitted ({today})", "date": today, "completed": True},
                {"text": "Waiting for device pickup", "date": "", "completed": False},
                {"text": "Device received by repair shop", "date": "", "completed": False},
                {"text": "Diagnostics completed", "date": "", "completed": False},
                {"text": "Repair in progress", "date": "", "completed": False},
                {"text": "Repair completed", "date": "", "completed": False}
            ]
            
            user_email_session = session.get('user', 'guest_repair')
            
            # Create repair data structure
            repair_data = {
                "id": repair_id,
                "user_id": user_email_session,
                "status": status_key,
                "status_key": status_key,
                "progress_width": progress_width,
                "device_info": {
                    "type": form_data['device_type'],
                    "brand": form_data['brand'],
                    "model": form_data['model'],
                    "issue_description": form_data['issue']
                },
                "user_info": {
                    "full_name": form_data['full_name'],
                    "email": form_data['email'],
                    "phone": form_data['phone'],
                    "address": form_data['address'],
                    "city": form_data['city'],
                    "zip_code": form_data['zip_code']
                },
                "shop_info": {
                    "id": selected_shop,
                    "name": shop_name,
                    "address": shop_address,
                    "phone": shop_phone
                },
                "dates": {
                    "submitted": today,
                    "pickup": form_data['pickupDate'],
                    "pickup_time": form_data['pickupTime'],
                    "estimated_completion": (datetime.now() + timedelta(days=random.randint(2,7))).strftime('%Y-%m-%d')
                },
                "timeline_events": timeline_events,
                "price": "To be determined",
                "device_icon_class": get_device_icon(form_data['device_type']),
                "status_display": status_display,
                "eta": f"Estimated pickup: {form_data['pickupDate'] or 'Not specified'}"
            }
            
            # Handle photo if uploaded in step 1
            if 'photo_path' in form_data:
                photo_path = form_data['photo_path']
                if os.path.exists(photo_path):
                    final_filename = f"{repair_id}_{os.path.basename(photo_path).replace('temp_', '')}"
                    upload_folder = app.config['UPLOADS_DIR']
                    final_path = os.path.join(upload_folder, final_filename)
                    os.rename(photo_path, final_path)
                    photo_url = f"/static/uploads/{final_filename}"
                    repair_data["photo_url"] = photo_url
            
            # Save repair data
            save_repair_to_json(repair_data)
            
            # Clear form session data
            session.pop('repair_form', None)
            
            flash('Repair request successfully submitted!', 'success')
            return redirect(url_for('my_repairs'))
            
        except Exception as e:
            app.logger.error(f"Error submitting repair: {str(e)}")
            flash(f"Error submitting repair: {str(e)}", "danger")
            return render_template('select_shop.html', user=user,
                                  repair_shops=repair_shops,
                                  device_type=session['repair_form']['device_type'])
    
    # Handle GET request
    return render_template('select_shop.html', user=user,
                          repair_shops=repair_shops,
                          device_type=session['repair_form']['device_type'])

@app.route('/get_repairs_data')
def get_repairs_data_api():
    """API endpoint for repair data"""
    try:
        user_email = session.get('user')
        if not user_email:
            return jsonify({'success': True, 'repairs': []})
        
        if not os.path.exists(REPAIRS_DATA_FILE):
            return jsonify({'success': True, 'repairs': []})
        
        with open(REPAIRS_DATA_FILE, 'r', encoding='utf-8') as f:
            all_repairs = json.load(f)
            
            if not isinstance(all_repairs, list):
                return jsonify({'success': True, 'repairs': []})
                
            # Filter repairs for current user
            user_repairs = [r for r in all_repairs if r.get('user_id') == user_email]
            return jsonify({'success': True, 'repairs': user_repairs})
            
    except json.JSONDecodeError:
        app.logger.error(f"Error decoding repair data from: {REPAIRS_DATA_FILE}")
        return jsonify({'success': False, 'message': 'Error reading repair data', 'repairs': []})
    except Exception as e:
        app.logger.error(f"Error in get_repairs_data_api: {e}")
        return jsonify({'success': False, 'message': str(e), 'repairs': []})

# ==========================================================
# API ENDPOINTS
# ==========================================================

@app.route('/api/ai-analyze', methods=['POST'])
def ai_analyze():
    """AI diagnostic analysis endpoint"""
    recommendation = (
        "AI diagnostics are currently unavailable. "
        "We recommend visiting our repair shop for a personal consultation."
    )
    return jsonify({"success": True, "recommendation": recommendation})

@app.route('/send_support_message', methods=['POST'])
def send_support_message():
    """Handle support message submission"""
    if 'user' not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    try:
        email = request.form.get('supportEmail')
        subject = request.form.get('supportSubject')
        body = request.form.get('supportBody')
        
        if not all([email, subject, body]):
            return jsonify({"success": False, "message": "All fields are required"}), 400
        
        # In a real app, you would send this message via email or store in database
        # For this demo, we'll just log it and return success
        app.logger.info(f"Support message from {email}, Subject: {subject}")
        
        return jsonify({"success": True, "message": "Support message sent successfully"})
    except Exception as e:
        app.logger.error(f"Error sending support message: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/submit_review', methods=['POST'])
def submit_review():
    """Handle review submission"""
    if 'user' not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    try:
        repair_id = request.form.get('repairId')
        review_text = request.form.get('reviewText')
        
        if not all([repair_id, review_text]):
            return jsonify({"success": False, "message": "Repair ID and review text are required"}), 400
        
        # In a real app, you would save the review to database
        # For this demo, we'll just log it and return success
        app.logger.info(f"Review for repair {repair_id}: {review_text}")
        
        return jsonify({"success": True, "message": "Review submitted successfully"})
    except Exception as e:
        app.logger.error(f"Error submitting review: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_repair', methods=['POST'])
def delete_repair():
    """Delete a repair record"""
    if 'user' not in session:
        return jsonify({"success": False, "message": "Please login first"}), 401
    
    try:
        repair_id = request.form.get('repairId')
        
        if not repair_id:
            return jsonify({"success": False, "message": "Repair ID is required"}), 400
        
        if os.path.exists(REPAIRS_DATA_FILE):
            with open(REPAIRS_DATA_FILE, 'r', encoding='utf-8') as f:
                repairs = json.load(f)
                
            # Filter out the repair to delete
            user_email = session.get('user')
            filtered_repairs = [r for r in repairs if not (r.get('id') == repair_id and r.get('user_id') == user_email)]
            
            # If we didn't filter anything out, the repair wasn't found
            if len(filtered_repairs) == len(repairs):
                return jsonify({"success": False, "message": "Repair not found or you don't have permission"}), 404
            
            # Write back the filtered list
            with open(REPAIRS_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(filtered_repairs, f, indent=2, ensure_ascii=False)
            
            return jsonify({"success": True, "message": "Repair deleted successfully"})
        else:
            return jsonify({"success": False, "message": "No repairs found"}), 404
    except Exception as e:
        app.logger.error(f"Error deleting repair: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# End of routes_new.py
