from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from app.models.db_service import DatabaseService, get_db_service
from app.config import Config

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configure CORS with proper settings
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:3000",  # Next.js development server
                "http://127.0.0.1:3000",  # Alternative local address
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Configure app
    config = Config()
    app.config.from_object(config)

    # Initialize database service
    db_service = get_db_service()
    app.config['DB_SERVICE'] = db_service

    # Register blueprints
    from app.routes.stories import stories_bp
    app.register_blueprint(stories_bp, url_prefix='/api/stories')

    return app 