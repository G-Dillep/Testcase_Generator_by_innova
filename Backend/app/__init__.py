from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
from app.models.db_service import DatabaseService
from app.config import Config

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configure app
    config = Config()
    app.config.from_object(config)

    # Initialize database service
    db_service = DatabaseService(
        postgres_config=config.postgres_config,
        lance_db_path=app.config['LANCE_DB_PATH']
    )
    app.config['DB_SERVICE'] = db_service

    # Register blueprints
    from app.routes.stories import stories_bp


    app.register_blueprint(stories_bp, url_prefix='/api/stories')


    return app 