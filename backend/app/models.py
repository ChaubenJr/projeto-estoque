from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

# ------------------------------
# 1. MODELO: USUÁRIO (Para autenticação e controle de acesso)
# ------------------------------
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    # MÉTODOS DE AUTENTICAÇÃO
    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        """Gera e armazena o hash da nova senha."""
        self.password_hash = generate_password_hash(password)

    # Requisito do Flask-Login
    def get_id(self):
        return str(self.id)
    
    # O UserMixin já fornece o atributo is_active
    @property
    def is_active(self):
        return self.ativo

    def __repr__(self):
        return f"Usuario('{self.username}', Ativo: {self.ativo})"

# ------------------------------
# 2. MODELO: PRODUTO / ESTOQUE (Modelo Único e Central)
#    (Modelo `Produto` duplicado foi removido)
# ------------------------------
class EstoqueEmbalagem(db.Model):
    __tablename__ = 'estoque_embalagem'
    # Usado como chave primária e Foreign Key nas movimentações
    cod_produto_embalagem = db.Column(db.String(50), primary_key=True)
    
    nome_produto = db.Column(db.String(255), nullable=False)
    unidade_medida = db.Column(db.String(10), nullable=False)
    padrao_embalagem = db.Column(db.String(255), nullable=False)
    
    estoque_min = db.Column(db.Integer, nullable=False)
    estoque_max = db.Column(db.Integer, nullable=False)
    
    ativo = db.Column(db.Boolean, default=True, nullable=False) 
    
    data_cadastro = db.Column(db.DateTime, default=datetime.now, nullable=False)
    data_atualizacao = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # RELAÇÕES (Backref garante que a coluna está na tabela referenciada)
    entradas = db.relationship('EntradasEmbalagens', backref='embalagem_entrada', lazy=True)
    saidas = db.relationship('SaidasEmbalagem', backref='embalagem_saida', lazy=True)

    def __repr__(self):
        return f"ProdutoEstoque('{self.cod_produto_embalagem}', {self.nome_produto}, Ativo: {self.ativo})"


# ------------------------------
# 3. MODELO: ENTRADAS EMBALAGENS
# ------------------------------
class EntradasEmbalagens(db.Model):
    __tablename__ = 'entradas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    cod_produto_embalagem = db.Column(db.String(50), 
                                      db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), 
                                      nullable=False)
    
    nf = db.Column(db.String(50), nullable=False)
    pedido_compra = db.Column(db.String(50), nullable=False)
    quantidade_recebida = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=True) 
    
    data_recebimento = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    # Campo para registrar o nome do responsável (string livre)
    responsavel_recebimento = db.Column(db.String(100), nullable=False) 
    
    hora_recebimento = db.Column(db.String(255), nullable=True) 

    def __repr__(self):
        return f"Entradas(ID: {self.id}, Produto: {self.cod_produto_embalagem}, NF: {self.nf})"

# ------------------------------
# 4. MODELO: SAIDAS EMBALAGEM
# ------------------------------
class SaidasEmbalagem(db.Model):
    __tablename__ = 'saidas_embalagem'
    id = db.Column(db.Integer, primary_key=True)
    cod_produto_embalagem = db.Column(db.String(50), 
                                      db.ForeignKey('estoque_embalagem.cod_produto_embalagem'), 
                                      nullable=False)
    
    op = db.Column(db.String(50), nullable=False)
    quantidade_saida = db.Column(db.Integer, nullable=False)
    data_saida = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    # Campo para registrar o nome do responsável (string livre)
    responsavel_saida = db.Column(db.String(100), nullable=False) 

    def __repr__(self):
        return f"Saidas(ID: {self.id}, Produto: {self.cod_produto_embalagem}, OP: {self.op})"