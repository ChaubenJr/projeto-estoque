from flask import Flask, render_template
from config import Config
from app.models import db
from app.routes import bp
from waitress import serve


def create_app():
    # Cria a aplicação com a configuração da pasta 'static' aqui dentro
    app = Flask(__name__, static_folder='app/static')
    app.config.from_object(Config)
    db.init_app(app)
    app.register_blueprint(bp)
    return app

# A partir daqui, a variável 'app' já estará configurada corretamente
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    serve(app, host='0.0.0.0', port=5000)