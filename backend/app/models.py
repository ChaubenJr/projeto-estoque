from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Modelo da tabela de definição de produtos de embalagem
class EstoqueEmbalagem(db.Model):
    __tablename__ = 'estoque_embalagem'
    cod_produto_embalagem = db.Column(db.String(50), primary_key=True)
    nome_produto = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(10), nullable=False)
    padrao_embalagem = db.Column(db.String(255), nullable=False)

# ---

# Modelo da tabela de entrada de embalagens
class EntradasEmbalagens(db.Model):
    __tablename__ = 'entradas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    nf = db.Column(db.String(50), nullable=False)
    quantidade_recebida = db.Column(db.Integer, nullable=False)
    responsavel_recebimento = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=True)
    data_recebimento = db.Column(db.DateTime, default=datetime.now)

    produto = db.relationship('EstoqueEmbalagem', backref=db.backref('entradas', lazy=True))

# Modelo da tabela de saída de embalagens
class SaidasEmbalagem(db.Model):
    __tablename__ = 'saidas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    op = db.Column(db.String(50), nullable=False)
    quantidade_saida = db.Column(db.Integer, nullable=False)
    responsavel_saida = db.Column(db.String(100), nullable=False)
    data_saida = db.Column(db.DateTime, default=datetime.now)

    produto = db.relationship('EstoqueEmbalagem', backref=db.backref('saidas', lazy=True))