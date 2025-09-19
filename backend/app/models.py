from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Modelo da tabela de produtos de embalagem (mantido como está)
class ProdutosEmbalagens(db.Model):
    __tablename__ = 'produtos_embalagem'
    cod_produto = db.Column(db.String(50), primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    padrao_embalagem = db.Column(db.String(50), nullable=False)
    unidade_de_medida = db.Column(db.String(10), nullable=False)
    quantidade_total = db.Column(db.Integer, default=0)

# ---

# Modelo da tabela de entrada de embalagens (com as novas colunas)
class EntradasEmbalagens(db.Model):
    __tablename__ = 'entradas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    
    # Chave estrangeira que vincula à tabela de produtos_embalagem
    # Corrigido o tipo para String para corresponder à tabela ProdutosEmbalagens
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('produtos_embalagem.cod_produto'), nullable=False)
    
    # NOVAS COLUNAS
    nf = db.Column(db.String(50), nullable=False)  # Número da Nota Fiscal
    unidade_medida = db.Column(db.String(10), nullable=False) # Unidade de medida na entrada (ex: 'un', 'kg')
    quantidade_recebida = db.Column(db.Integer, nullable=False) # Quantidade fornecida
    responsavel_recebimento = db.Column(db.String(100), nullable=False) # Nome do responsável pelo recebimento
    total = db.Column(db.String(10), nullable=False) # Valor da embalagem

    # A data de recebimento agora usa a função 'datetime.now()'
    data_recebimento = db.Column(db.DateTime, default=datetime.now)

    # RELACIONAMENTO: Corrigido para apontar para o nome de classe correto, 'ProdutosEmbalagens'
    produto = db.relationship('ProdutosEmbalagens', backref='entradas', lazy=True)