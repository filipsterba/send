import os
import json
import requests
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app


import time
from config import DEEPSEEK_API_KEY  # Přidáme import
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from werkzeug.security import generate_password_hash, check_password_hash

USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

app.config['GOOGLE_ID'] = "YOUR_GOOGLE_CLIENT_ID"
app.config['GOOGLE_SECRET'] = "YOUR_GOOGLE_CLIENT_SECRET"
app.config['FACEBOOK_ID'] = "YOUR_FACEBOOK_APP_ID"
app.config['FACEBOOK_SECRET'] = "YOUR_FACEBOOK_APP_SECRET"

oauth = OAuth(app)

# Google OAuth konfigurace
google = oauth.remote_app(
    'google',
    consumer_key=app.config['GOOGLE_ID'],
    consumer_secret=app.config['GOOGLE_SECRET'],
    request_token_params={
        'scope': 'email profile'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

# Facebook OAuth konfigurace
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

# YouTube API key
YOUTUBE_API_KEY = "AIzaSyDz5HB5ZwNYGgfjncH89AakkZl3eJgocoY"
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

TRUSTED_CHANNELS = [
    'iFixit',
    'JerryRigEverything',
    'Hugh Jeffreys',
    'Phone Repair Guru',
    'REWA Technology',
    'fixmyphone'
]

def get_user_data():
    """Helper function to get user data"""
    if 'user' in session:
        users = load_users()
        user_email = session['user']
        return users.get(user_email)
    return None

@app.route('/')
def index():
    return render_template('uvod.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    user = get_user_data()
    if not user:
        return redirect(url_for('logout'))
    return render_template('user-page.html', username=user['username'], user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('home'))
    users = load_users()
    if request.method == 'POST':
        identity = request.form.get('loginIdentity')
        password = request.form.get('loginPassword')
        user_email = None
        for email, user in users.items():
            if identity == email or identity == user['username']:
                user_email = email
                break
        if user_email and users[user_email]['password'] == password:
            session['user'] = user_email
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials or user does not exist')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' in session:
        return redirect(url_for('home'))
    users = load_users()
    if request.method == 'POST':
        username = request.form.get('registerUsername')
        email = request.form.get('registerEmail')
        password = request.form.get('registerPassword')
        if email in users:
            flash('This email is already registered.')
            return redirect(url_for('register'))
        users[email] = {'username': username, 'password': password}
        save_users(users)
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/about-us')
def about_us():
    return render_template('about-us.html', user=get_user_data())

@app.route('/price-list')
def price_list():
    return render_template('price-list.html', user=get_user_data())

@app.route('/my-repairs')
def my_repairs():
    """Handle My Repairs page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    user = get_user_data()
    if not user:
        return redirect(url_for('logout'))
    
    repairs = [
        {
            'device': 'iPhone 14 Pro',
            'status': 'In Progress',
            'description': 'Screen replacement',
            'eta': '2 days',
            'progress': 75
        },
        {
            'device': 'MacBook Air',
            'status': 'In Progress', 
            'description': 'Battery replacement',
            'eta': '1 day',
            'progress': 90
        }
    ]
    
    return render_template('repairs.html', 
                         user=user,
                         repairs=repairs)

@app.route('/api/ai-analyze', methods=['POST'])
def ai_analyze():
    description = request.form.get('description', '')
    if not description:
        return jsonify({'error': 'Missing description'}), 400

    prompt = (
        "Diagnose the device problem from this description. "
        "Recommend the best repair shop in the user's area. "
        f"Description: {description}"
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": prompt}
    ]

    client = OpenAI(
        api_key="<sk-c68ab6ddc34c41b7bdeeea7459f7e999>",
        base_url="https://api.deepseek.com"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        recommendation = response.choices[0].message.content.strip()
        return jsonify({"recommendation": recommendation})
    except Exception as e:
        print("AI error:", e)
        return jsonify({"error": "AI service error"}), 500

@app.route('/test')
def test():
    return "Test OK"

@app.route('/auth/google')
def google_auth():
    return google.authorize(callback=url_for('google_callback', _external=True))

@app.route('/auth/google/callback')
def google_callback():
    try:
        resp = google.authorized_response()
        if resp is None or resp.get('access_token') is None:
            return redirect(url_for('login'))
        
        user_info = google.get('userinfo', token=(resp['access_token'], '')).data
        email = user_info['email']
        
        # Kontrola existence uživatele nebo vytvoření nového
        users = load_users()
        if email not in users:
            users[email] = {
                'username': user_info['name'],
                'password': None,  # OAuth uživatelé nemají heslo
                'oauth_provider': 'google'
            }
            save_users(users)
        
        session['user'] = email
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Google Auth Error: {e}")
        return redirect(url_for('login'))

@app.route('/auth/facebook')
def facebook_auth():
    return facebook.authorize(callback=url_for('facebook_callback', _external=True))

@app.route('/auth/facebook/callback')
def facebook_callback():
    try:
        resp = facebook.authorized_response()
        if resp is None or resp.get('access_token') is None:
            return redirect(url_for('login'))
        
        user_info = facebook.get('/me?fields=email,name', token=(resp['access_token'], '')).data
        email = user_info.get('email')
        
        if not email:
            flash('Email is required')
            return redirect(url_for('login'))
        
        users = load_users()
        if email not in users:
            users[email] = {
                'username': user_info['name'],
                'password': None,
                'oauth_provider': 'facebook'
            }
            save_users(users)
        
        session['user'] = email
        return redirect(url_for('home'))
    except Exception as e:
        print(f"Facebook Auth Error: {e}")
        return redirect(url_for('login'))

@app.route('/repairs/new', methods=['GET'])
def create_repair():
    """Zobrazí formulář pro novou opravu"""
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('start-repair.html')

@app.route('/repairs/submit', methods=['POST'])
def submit_repair():
    """Zpracuje odeslaný formulář"""
    if 'user' not in session:
        return redirect(url_for('login'))
    # TODO: Zpracování formuláře
    return redirect(url_for('my_repairs'))

@app.route('/ai-chat')
def ai_chat():
    if 'user' not in session:
        return redirect(url_for('login'))
    users = load_users()
    user_email = session.get('user')
    username = users[user_email]['username']
    return render_template('ai-chat.html', username=username)

@app.route('/api/chat', methods=['POST'])
def ai_chat_api():
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    try:
        print("Initializing Deepseek API client...")
        client = OpenAI(
            api_key="sk-324c3796d9304113a43eefa9a437ba5c",
            base_url="https://api-inference.deepseek.com/v1"  # Správný endpoint
        )

        messages = [
            {
                "role": "system",
                "content": "You are an expert device repair technician. Help diagnose device issues and provide repair solutions."
            },
            {
                "role": "user",
                "content": data['message']
            }
        ]

        print(f"Sending request to Deepseek API...")
        response = client.chat.completions.create(
            model="deepseek-1.3b-chat",  # Správný model
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            stream=False
        )
        
        ai_response = response.choices[0].message.content.strip()
        print(f"Got AI response: {ai_response[:100]}...")
        return jsonify({"response": ai_response})

    except Exception as e:
        print(f"Deepseek API Error: {str(e)}")
        raise e  # Necháme chybu projít pro debugging

        if "402" in error_msg or "Insufficient Balance" in error_msg:
            # Return friendly message to user
            return jsonify({
                "response": "I'm currently taking a short break for maintenance. Please try again in a few minutes."
            })
        
        # For other errors, use mock response
        mock_responses = {
            "screen": "Based on your description...",
            "battery": "This appears to be...",
            "default": "To help you better, please tell me:\n1. What device you have\n2. What problems you're experiencing\n3. When it started"
        }
        
        user_message = data['message'].lower()
        for keyword, response in mock_responses.items():
            if keyword in user_message:
                return jsonify({"response": response})
        return jsonify({"response": mock_responses["default"]})

@app.route('/repair-guides')
def repair_guides():
    if 'user' not in session:
        return redirect(url_for('login'))
    users = load_users()
    user_email = session.get('user')
    username = users[user_email]['username']
    
    guides = [
        {
            'title': 'iPhone Screen Replacement',
            'difficulty': 'Intermediate',
            'time': '30 min',
            'category': 'phones',
            'image': 'iphone-repair.jpg',  # Obrázek musí být v static/images/
            'video_id': 'FkE9osrB2Pc'
        },
        {
            'title': 'MacBook Battery Replacement',
            'difficulty': 'Easy',
            'time': '45 min',
            'category': 'laptops',
            'image': 'macbook-repair.jpg',
            'video_id': 'wSJ0U3tJmbQ'
        },
        {
            'title': 'iPad Screen Repair',
            'difficulty': 'Advanced',
            'time': '60 min',
            'category': 'tablets',
            'image': 'ipad-repair.jpg',
            'video_id': '0YGgS7gZUqQ'
        }
    ]
    
    return render_template('repair-guides.html', username=username, guides=guides)

@app.route('/api/search-tutorials')
def search_tutorials():
    query = request.args.get('q', '')
    print(f"Searching for: {query}")  # Debug log

    # Testovací data místo YouTube API
    test_videos = [
        {
            'id': 'abc123',
            'title': f'How to repair {query}',
            'thumbnail': 'https://i.ytimg.com/vi/abc123/hqdefault.jpg',
            'channelTitle': 'iFixit',
            'description': 'Step by step repair guide'
        },
        {
            'id': 'def456',
            'title': f'Fix your {query} in 10 minutes',
            'thumbnail': 'https://i.ytimg.com/vi/def456/hqdefault.jpg',
            'channelTitle': 'Phone Repair Guru',
            'description': 'Professional repair tutorial'
        }
    ]
    
    return jsonify({'youtube': test_videos})

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # Vylepšený search query pro relevantnější výsledky
        search_query = f"{query} repair tutorial guide how to fix"
        
        # Přidáme filtr pro důvěryhodné kanály
        channel_filter = ' OR '.join([f'channel:"{channel}"' for channel in TRUSTED_CHANNELS])
        search_query = f"({search_query}) ({channel_filter})"

        search_response = youtube.search().list(
            q=search_query,
            part="snippet",
            type="video",
            videoDefinition="high",
            relevanceLanguage="en",
            maxResults=8,
            videoDuration="medium"  # Vyfiltruje příliš krátká/dlouhá videa
        ).execute()

        videos = []
        for item in search_response.get('items', []):
            # Kontrola kvality videa podle názvu a popisu
            title = item['snippet']['title'].lower()
            description = item['snippet']['description'].lower()
            
            if any(keyword in title or keyword in description 
                  for keyword in ['repair', 'fix', 'guide', 'tutorial', 'how to']):
                videos.append({
                    'id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'channelTitle': item['snippet']['channelTitle'],
                    'description': item['snippet']['description'][:100] + '...'
                })

        return jsonify({'youtube': videos})

    except Exception as e:
        print(f"YouTube API Error: {str(e)}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return jsonify({'success': False, 'msg': 'Not logged in'}), 401
    
    data = request.get_json()
    users = load_users()
    user_email = session['user']
    user = users.get(user_email)
    
    if not user:
        return jsonify({'success': False, 'msg': 'User not found'}), 404
    
    # Update user information
    user['username'] = data.get('displayName', user['username'])
    user['phone'] = data.get('phone', '')
    
    users[user_email] = user
    save_users(users)
    
    return jsonify({'success': True})

@app.route('/api/change-password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return jsonify({'success': False, 'msg': 'Not logged in'}), 401
    
    data = request.get_json()
    users = load_users()
    user_email = session['user']
    user = users.get(user_email)
    
    if not user:
        return jsonify({'success': False, 'msg': 'User not found'}), 404
    
    old_password = data.get('oldPassword')
    new_password = data.get('newPassword')
    
    if user['password'] != old_password:
        return jsonify({'success': False, 'msg': 'Incorrect old password'}), 400
    
    user['password'] = new_password
    users[user_email] = user
    save_users(users)
    
    return jsonify({'success': True})

from flask import render_template, session, redirect, url_for

@app.route('/settings')
def settings():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    users = load_users()
    user_email = session['user']
    user = users.get(user_email)
    
    if not user:
        return redirect(url_for('logout'))
    
    return render_template('settings.html', 
                         user=user, 
                         user_email=user_email)


