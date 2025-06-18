import os

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
UPLOADS_DIR = os.path.join(STATIC_DIR, 'uploads')

# Data paths
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
REPAIRS_DATA_FILE = os.path.join(DATA_DIR, 'repairs.json')
REPAIR_SHOPS_FILE = os.path.join(DATA_DIR, 'repair_shops_data.json')

# Secret key for sessions - should be set via env vars in production
SECRET_KEY = os.environ.get('FIXIT_SECRET_KEY') or os.urandom(24)

# OAuth credentials - these should be set via env vars in production
GOOGLE_ID = os.environ.get("GOOGLE_ID", "YOUR_GOOGLE_CLIENT_ID")
GOOGLE_SECRET = os.environ.get("GOOGLE_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")
FACEBOOK_ID = os.environ.get("FACEBOOK_ID", "YOUR_FACEBOOK_APP_ID")
FACEBOOK_SECRET = os.environ.get("FACEBOOK_SECRET", "YOUR_FACEBOOK_APP_SECRET")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "YOUR_YOUTUBE_API_KEY")

# Other app settings
DEBUG = True
FACEBOOK_SECRET = os.environ.get("FACEBOOK_SECRET", "YOUR_FACEBOOK_APP_SECRET")

# YouTube API Key
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "AIzaSyDz5HB5ZwNYGgfjncH89AakkZl3eJgocoY") # Ponecháno prozatím, ale lepší přes env

# Flask Config
SECRET_KEY = os.urandom(24)
