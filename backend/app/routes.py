from flask import render_template, Blueprint, request, redirect, url_for
from .models import EstoqueEmbalagem, SaidasEmbalagem, EntradasEmbalagens, db
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Rota da página inicial."""
    return render_template('index.html')

@bp.route('/entrada')
def entrada():
    """Rota para a página de entrada."""
    produtos = EstoqueEmbalagem.query.all()
    # Converte os objetos do modelo para uma lista de dicionários antes de passar para o template.
    produtos_dict = [produto.to_dict() for produto in produtos]
    return render_template("entrada.html", produtos=produtos_dict)

@bp.route('/saida')
def saida():
    """Rota para a página de saída."""
    produtos = EstoqueEmbalagem.query.all()
    # Converte os objetos do modelo para uma lista de dicionários antes de passar para o template.
    produtos_dict = [produto.to_dict() for produto in produtos]
    return render_template("saida.html", produtos=produtos_dict)

@bp.route('/estoque')
def estoque():
    """Rota para a página de estoque."""
    return render_template('estoque.html')

@bp.route('/entrada_embalagem', methods=['POST'])
def entrada_embalagem():
    """
    Rota para processar o formulário de entrada de embalagens.
    """
    try:
        cod_produto = request.form.get('cod_produto_embalagem')
        nf = request.form.get('nf')
        quantidade = request.form.get('quantidade_recebida')
        responsavel = request.form.get('responsavel_recebimento')
        total = request.form.get('total')
        data_recebimento_str = request.form.get('data_recebimento')

        if not all([cod_produto, nf, quantidade, responsavel, data_recebimento_str]):
            return "Erro: Todos os campos são obrigatórios.", 400

        data_recebimento = datetime.strptime(data_recebimento_str, '%Y-%m-%d')
        
        nova_entrada = EntradasEmbalagens(
            cod_produto_embalagem=cod_produto,
            nf=nf,
            quantidade_recebida=int(quantidade),
            responsavel_recebimento=responsavel,
            total=float(total),
            data_recebimento=data_recebimento
        )

        db.session.add(nova_entrada)
        db.session.commit()

        return redirect(url_for('main.entrada'))
    
    except Exception as e:
        db.session.rollback()
        return f"Ocorreu um erro: {str(e)}", 500

@bp.route('/saida_embalagem', methods=['POST'])
def saida_embalagem():
    """
    Rota para processar o formulário de saída de embalagens.
    """
    try:
        cod_produto = request.form.get('cod_produto_embalagem')
        op = request.form.get('op')
        quantidade = request.form.get('quantidade_saida')
        responsavel = request.form.get('responsavel_saida')
        data_saida_str = request.form.get('data_saida')

        # Validação simples
        if not all([cod_produto, op, quantidade, responsavel, data_saida_str]):
            return "Erro: Todos os campos são obrigatórios.", 400

        # Converte a string da data para um objeto datetime
        data_saida = datetime.strptime(data_saida_str, '%Y-%m-%d')
        
        # Cria uma nova entrada na tabela de saídas
        nova_saida = SaidasEmbalagem(
            cod_produto_embalagem=cod_produto,
            op=op,
            quantidade_saida=int(quantidade),
            responsavel_saida=responsavel,
            data_saida=data_saida
        )

        db.session.add(nova_saida)
        db.session.commit()

        # Redireciona de volta para a página de saída ou para uma página de sucesso
        return redirect(url_for('main.saida'))
        
    except Exception as e:
        db.session.rollback()
        return f"Ocorreu um erro: {str(e)}", 500
