
from flask import request, jsonify, Blueprint
from .models import db, ProdutosEmbalagens, EntradasEmbalagens

bp = Blueprint('main', __name__)

@bp.route('/nova_entrada', methods=['POST'])
def nova_entrada():
    # Coleta os dados do formulário
    data = request.json
    
    cod_produto = data.get('cod_produto_embalagem')
    nf = data.get('nf')
    unidade = data.get('unidade_medida')
    quantidade = data.get('quantidade_recebida')
    responsavel = data.get('responsavel_recebimento')
    valor_embalagem = data.get('valor_embalagem')
    
    # Valida se o produto existe
    produto = ProdutosEmbalagens.query.get(cod_produto)
    if not produto:
        return jsonify({"erro": "Produto não encontrado"}), 404

    # Cria um novo registro de entrada
    nova_entrada = EntradasEmbalagens(
        cod_produto_embalagem=cod_produto,
        nf=nf,
        unidade_medida=unidade,
        quantidade_recebida=quantidade,
        responsavel_recebimento=responsavel,
        valor_embalagem=valor_embalagem
    )
    
    # Adiciona a entrada ao banco de dados e atualiza o estoque
    db.session.add(nova_entrada)
    produto.quantidade_total += quantidade
    db.session.commit()

    return jsonify({"mensagem": "Entrada registrada com sucesso!"}), 201