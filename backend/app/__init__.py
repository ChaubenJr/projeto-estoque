# __init__.py
import os
from flask import Flask
from .models import db, Usuario 
from flask_migrate import Migrate
from flask_mail import Mail
from flask_login import LoginManager
from config import Config # Assumindo que você tem um arquivo config.py

# Declaração das extensões globais
# É uma boa prática declarar a extensão sem instanciar no escopo global
mail = Mail()

def create_app():
    # 1. Configuração básica do Flask
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # Nota: Assumindo que a SECRET_KEY está em Config, se não, adicione:
    # app.config['SECRET_KEY'] = 'SUA_CHAVE_SECRETA_AQUI' 

    # 2. Inicialização do SQLAlchemy e Migrações
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # 3. Inicialização do Flask-Mail
    mail.init_app(app)

    # 4. Inicialização e Configuração do Flask-Login (A CORREÇÃO)
    login_manager = LoginManager() # Cria a instância dentro da factory
    login_manager.init_app(app)
    login_manager.login_view = 'main.login' # Endpoint do Blueprint para a tela de login
    login_manager.login_message = "Por favor, faça login para acessar esta página."
    login_manager.login_message_category = "danger"

    # 5. Configuração do user_loader
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # 6. Importa e registra o blueprint APÓS a inicialização das extensões
    from .routes import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    return app