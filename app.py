from flask import Flask, render_template

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Přidáme auto-reload šablon
app.secret_key = 'your_secret_key'

# Import routes až po vytvoření app
from routes import *  # Změníme na explicitní import

if __name__ == '__main__':
    app.run(debug=True)
