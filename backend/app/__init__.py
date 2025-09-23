import os
from flask import Flask
from .config import Config
from .models import db
from .routes import bp as main_blueprint

def create_app():
    app = Flask(__name__, instance_relative_config=True)  # Load configuration from the Config object
    
    app.config.from_object(Config)

    # Initialize the database with the app
    db.init_app(app)

    # Register the main blueprint for routes
    app.register_blueprint(main_blueprint)

    # Ensure the instance folder exists for configurations
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app