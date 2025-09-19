class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://estoque@localhost/entrada_embalagem'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'estoque_secret_key'.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/produtos'