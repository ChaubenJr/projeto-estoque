import os

class Config:
    # CLAVE SECRETA É ESSENCIAL PARA SESSÕES E FLASK-LOGIN
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sua_chave_secreta_padrao_muito_forte_aqui'
    
    # Configuração do SQLAlchemy (use seu caminho real)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///estoque.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/estoque'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'estoque_secret_key'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'cdss.snf25@uea.edu.br'
    MAIL_PASSWORD = 'acwv poqt jkvw plbj' 