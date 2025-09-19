class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/estoque'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'estoque_secret_key'