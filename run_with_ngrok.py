from pyngrok import ngrok
from app import app  # your Flask app

# Start ngrok tunnel on port 5000
public_url = ngrok.connect(5000)
print("Ngrok URL:", public_url)

# Start Flask app
app.run(port=5000)
