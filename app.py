from flask import Flask, request, render_template, redirect, url_for, flash, session
import os
import config
import json

app = Flask(__name__)

# Load configuration from config.py
app.config.from_object(config)

# Basic app settings
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.environ.get("FIXIT_SECRET_KEY", getattr(config, 'SECRET_KEY', os.urandom(24)))

# Create necessary directories
if app.config.get('DATA_DIR'):
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
if app.config.get('UPLOADS_DIR'):
    os.makedirs(app.config['UPLOADS_DIR'], exist_ok=True)

# Import ONLY ONE routes file - not both
import routes_new  # Keep this one
# import routes    # Comment out or remove this import if it exists

# The /submit_repair route should be moved to routes_new.py for better organization.
# Remove this route from app.py and define it in routes_new.py instead.

# Přidejte tuto konfiguraci, pokud chybí
app.config['REPAIR_SHOPS_FILE'] = os.path.join(app.config['DATA_DIR'], 'repair_shops_data.json')

# Run the app
if __name__ == '__main__':
    print("Starting Fix-It application...")
    print(f"Open in your browser: http://127.0.0.1:5000/")
    app.run(debug=True, host='127.0.0.1', port=5000)
