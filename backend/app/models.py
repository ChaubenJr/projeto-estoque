from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

# Modelo da tabela de estoque
class EstoqueEmbalagem(db.Model):
    __tablename__ = 'estoque_total_embalagens'
    
    # A coluna de código do produto deve ser a chave primária
    cod_produto_embalagem = db.Column(db.String(20), primary_key=True)
    nome_produto = db.Column(db.String(100), nullable=False)
    total_embalagens_estoque = db.Column(db.Integer, nullable=False)
    
    # Define as relações com as tabelas de entrada e saída
    entradas = db.relationship('EntradasEmbalagens', backref='produto_estoque', lazy=True)
    saidas = db.relationship('SaidasEmbalagem', backref='produto_estoque', lazy=True)
    
    def to_dict(self):
        return {
            'cod_produto_embalagem': self.cod_produto_embalagem,
            'nome_produto': self.nome_produto,
            'total_embalagens_estoque': self.total_embalagens_estoque
        }

# --- 

# Modelo da tabela de entrada de embalagens
class EntradasEmbalagens(db.Model):
    __tablename__ = 'entradas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    
    # Chave estrangeira corrigida, apontando para a chave primária da tabela de estoque
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_total_embalagens.cod_produto_embalagem'), nullable=False)
    
    nf = db.Column(db.String(50), unique=True, nullable=False)
    quantidade_recebida = db.Column(db.Integer, nullable=False)
    responsavel_recebimento = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=True)
    
    # Usando UTC para consistência de data e hora
    data_recebimento = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc))

# Modelo da tabela de saída de embalagens
class SaidasEmbalagem(db.Model):
    __tablename__ = 'saidas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    
    # Chave estrangeira corrigida
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_total_embalagens.cod_produto_embalagem'), nullable=False)
    
    op = db.Column(db.String(50), nullable=False)
    quantidade_saida = db.Column(db.Integer, nullable=False)
    responsavel_saida = db.Column(db.String(100), nullable=False)
    
    # Usando UTC para consistência de data e hora
    data_saida = db.Column(db.DateTime, default=lambda: datetime.now(pytz.utc))