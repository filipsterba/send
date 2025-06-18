# Spouštění aplikace z tohoto souboru
from app import app
import routes_new  # Tento import musí být zde, aby se načetly definice cest

if __name__ == "__main__":
    print("=== Fix-IT Aplikace ===")
    print("Otevřete prohlížeč na adrese: http://127.0.0.1:5000/")
    app.run(debug=True)
