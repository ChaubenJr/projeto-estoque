from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Se você for usar 'pytz' para datas consistentes em UTC, importe-o aqui.
# Por exemplo: import pytz 
# Caso contrário, remova a referência 'pytz.utc' nas classes.

db = SQLAlchemy()

# Modelo da tabela de definição de produtos de embalagem
# Este modelo atua como o "cadastro" de todos os produtos de embalagem.
class EstoqueEmbalagem(db.Model):
    __tablename__ = 'estoque_embalagem'
    
    # A coluna de código do produto é a chave primária
    cod_produto_embalagem = db.Column(db.String(50), primary_key=True)
    nome_produto = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(10), nullable=False)
    padrao_embalagem = db.Column(db.String(255), nullable=False)
    estoque_min = db.Column(db.Integer, default=0, nullable=True)
    estoque_max = db.Column(db.Integer, default=0, nullable=True)

    
    # Define as relações com as tabelas de entrada e saída, permitindo consultas fáceis.
    # O 'backref' cria uma propriedade 'produto' nas classes EntradasEmbalagens e SaidasEmbalagem.
    entradas = db.relationship('EntradasEmbalagens', backref='produto', lazy=True)
    saidas = db.relationship('SaidasEmbalagem', backref='produto', lazy=True)

    def to_dict(self):
        """Método opcional para serializar o objeto em um dicionário."""
        return {
            'cod_produto_embalagem': self.cod_produto_embalagem,
            'nome_produto': self.nome_produto,
            'unidade_medida': self.unidade_medida,
            'padrao_embalagem': self.padrao_embalagem
        }

# ---

# Modelo da tabela de entrada de embalagens
class EntradasEmbalagens(db.Model):
    __tablename__ = 'entradas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    
    # Chave estrangeira, apontando para a chave primária da tabela de estoque
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    
    # Adicionando 'unique=True' na NF para evitar duplicatas, uma boa prática de integridade.
    nf = db.Column(db.String(50), unique=True, nullable=False)
    quantidade_recebida = db.Column(db.Integer, nullable=False)
    responsavel_recebimento = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=True)
    
    # Usando `datetime.now` como valor padrão.
    data_recebimento = db.Column(db.DateTime, default=datetime.now)

# Modelo da tabela de saída de embalagens
class SaidasEmbalagem(db.Model):
    __tablename__ = 'saidas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    
    # Chave estrangeira, apontando para a chave primária da tabela de estoque
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    
    op = db.Column(db.String(50), nullable=False)
    quantidade_saida = db.Column(db.Integer, nullable=False)
    responsavel_saida = db.Column(db.String(100), nullable=False)
    
    # Usando `datetime.now` como valor padrão.
    data_saida = db.Column(db.DateTime, default=datetime.now)