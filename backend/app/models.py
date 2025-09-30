from flask_sqlalchemy import SQLAlchemy
from datetime import date # Importe 'date' em vez de 'datetime' para os padrões

db = SQLAlchemy()

class EstoqueEmbalagem(db.Model):
    __tablename__ = 'estoque_embalagem'
    
    cod_produto_embalagem = db.Column(db.String(50), primary_key=True)
    nome_produto = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(10), nullable=False)
    padrao_embalagem = db.Column(db.String(255), nullable=False)
    estoque_min = db.Column(db.Integer, default=0, nullable=True)
    estoque_max = db.Column(db.Integer, default=0, nullable=True)
    
    entradas = db.relationship('EntradasEmbalagens', backref='produto', lazy=True)
    saidas = db.relationship('SaidasEmbalagem', backref='produto', lazy=True)

    def to_dict(self):
        return {
            'cod_produto_embalagem': self.cod_produto_embalagem,
            'nome_produto': self.nome_produto,
            'unidade_medida': self.unidade_medida,
            'padrao_embalagem': self.padrao_embalagem
        }

# ---

class EntradasEmbalagens(db.Model):
    __tablename__ = 'entradas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    
    nf = db.Column(db.String(50), unique=True, nullable=False)
    
    # =======================================================
    # LINHA ADICIONADA AQUI
    # =======================================================
    pedido_compra = db.Column(db.String(5), nullable=False)
    
    quantidade_recebida = db.Column(db.Integer, nullable=False)
    responsavel_recebimento = db.Column(db.String(100), nullable=False)
    total = db.Column(db.Float, nullable=True)
    
    # Ajustado para db.Date para maior consistência
    data_recebimento = db.Column(db.Date, default=date.today)

# ---

class SaidasEmbalagem(db.Model):
    __tablename__ = 'saidas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    
    cod_produto_embalagem = db.Column(db.String(50), db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), nullable=False)
    
    op = db.Column(db.String(50), nullable=False)
    quantidade_saida = db.Column(db.Integer, nullable=False)
    responsavel_saida = db.Column(db.String(100), nullable=False)
    
    # Ajustado para db.Date para maior consistência
    data_saida = db.Column(db.Date, default=date.today)