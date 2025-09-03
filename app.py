from flask import Flask
from flask_cors import CORS
from auth.routes import init_oauth

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=["https://fedorco.dev", "https://www.fedorco.dev", "http://127.0.0.1:5500"])
app.secret_key = "your-secret-key"  # Needed if you use sessions or flash

# Initialize oAuth
init_oauth(app)

# Register the auth blueprint under /auth URL prefix
from auth.routes import auth_bp  # Import your blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")

# Register the user blueprint under /user URL prefix
from user_info.routes import user_bp  # Import your blueprint
app.register_blueprint(user_bp, url_prefix="/user")

@app.route("/")
def index():
    return "Welcome to the portfolio main page!"

if __name__ == "__main__":
    app.run(debug=True)
