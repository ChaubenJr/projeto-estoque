# Em app/__init__.py

from flask import Flask
from .config import Config
from .models import db
from .routes import bp as main_blueprint

def create_app():
    # Correção: Remover os caminhos explícitos.
    # O Flask encontrará 'templates' e 'static' dentro do pacote 'app'.
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_object(Config)

    db.init_app(app)

    app.register_blueprint(main_blueprint)

    return app