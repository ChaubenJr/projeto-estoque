from flask_sqlalchemy import SQLAlchemy
from datetime import datetime # Agora usamos datetime completo

db = SQLAlchemy()

class EstoqueEmbalagem(db.Model):
    # ... (seu modelo EstoqueEmbalagem permanece o mesmo) ...
    __tablename__ = 'estoque_embalagem'
    cod_produto_embalagem = db.Column(db.String(50), primary_key=True)
    nome_produto = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(10), nullable=False)
    padrao_embalagem = db.Column(db.String(255), nullable=False)
    estoque_min = db.Column(db.Integer)
    estoque_max = db.Column(db.Integer)
    entradas = db.relationship('EntradasEmbalagens', backref='produto', lazy=True)
    saidas = db.relationship('SaidasEmbalagem', backref='produto', lazy=True)

class EntradasEmbalagens(db.Model):
    __tablename__ = 'entradas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    nf = db.Column(db.String(50), unique=True, nullable=False)
    pedido_compra = db.Column(db.String(5), nullable=False)
    quantidade_recebida = db.Column(db.Integer, nullable=False)
    responsavel_recebimento = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=True)
    
    # ALTERADO DE db.Date PARA db.DateTime
    data_recebimento = db.Column(db.DateTime, default=datetime.now)

class SaidasEmbalagem(db.Model):
    __tablename__ = 'saidas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    op = db.Column(db.String(50), nullable=False)
    quantidade_saida = db.Column(db.Integer, nullable=False)
    responsavel_saida = db.Column(db.String(100), nullable=False)
    
    # ALTERADO DE db.Date PARA db.DateTime
    data_saida = db.Column(db.DateTime, default=datetime.now)