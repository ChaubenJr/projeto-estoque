class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/estoque'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'estoque_secret_key'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'cdss.snf25@uea.edu.br'
    MAIL_PASSWORD = 'acwv poqt jkvw plbj' 