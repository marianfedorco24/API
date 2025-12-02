from flask import Flask
from flask_cors import CORS
from auth.routes import init_oauth
import os

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-unsafe-key")
CORS(app, supports_credentials=True, origins=[
    "https://fedorco.dev",
    "https://www.fedorco.dev",
    "https://linkorganizer.fedorco.dev"
])

# Initialize oAuth
init_oauth(app)

# Register the auth blueprint under /auth URL prefix
from auth.routes import auth_bp  # Import your blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")

# Register the user blueprint under /user URL prefix
from user_info.routes import user_bp  # Import your blueprint
app.register_blueprint(user_bp, url_prefix="/user")

# Register the Link Organizer blueprint under /linkorganizer URL prefix
from link_organizer.routes import link_organizer_bp  # Import your blueprint
app.register_blueprint(link_organizer_bp, url_prefix="/linkorganizer")

# Register the Strava API blueprint under /stravaapi URL prefix
from strava_api.routes import strava_api_bp  # Import your blueprint
app.register_blueprint(strava_api_bp, url_prefix="/stravaapi")

# Register the Skolaonline API blueprint under /skolaonlineapi URL prefix
from skolaonline_api.routes import skolaonline_api_bp  # Import your blueprint
app.register_blueprint(skolaonline_api_bp, url_prefix="/skolaonlineapi")

if __name__ == "__main__":
    app.run(debug=True)
