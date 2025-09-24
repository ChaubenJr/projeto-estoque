import os
from flask import Flask
from .config import Config
from .models import db
from flask_migrate import Migrate
from flask_mail import Mail

# Declara a variável 'mail' no escopo global
mail = Mail()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Inicializa a extensão Flask-Mail com o aplicativo
    mail.init_app(app)

    # Importa e registra o blueprint APÓS a inicialização das extensões
    from .routes import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app