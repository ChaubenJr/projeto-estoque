from flask import request, jsonify, Blueprint, render_template, redirect, url_for, flash
from datetime import datetime
from .models import db, EstoqueEmbalagem, EntradasEmbalagens, SaidasEmbalagem

bp = Blueprint("main", __name__)
 
@bp.route("/")
def index():
    return redirect(url_for("main.entrada"))
 
@bp.route("/entrada")
def entrada():
    produtos = EstoqueEmbalagem.query.all()
    return render_template("entrada.html", produtos=produtos)
 
@bp.route("/saida")
def saida():
    produtos = EstoqueEmbalagem.query.all()
    return render_template("saida.html", produtos=produtos)
 
@bp.route("/estoque")
def estoque():
    # Consulta a VIEW que criamos para obter o estoque total
    # (Supondo que você criou um modelo para a view)
    estoque_total = db.session.query(
        EstoqueEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        db.func.coalesce(db.func.sum(EntradasEmbalagens.quantidade_recebida), 0) -
        db.func.coalesce(db.func.sum(SaidasEmbalagem.quantidade_saida), 0)
    ).outerjoin(
        EntradasEmbalagens,
        EstoqueEmbalagem.cod_produto_embalagem == EntradasEmbalagens.cod_produto_embalagem
    ).outerjoin(
        SaidasEmbalagem,
        EstoqueEmbalagem.cod_produto_embalagem == SaidasEmbalagem.cod_produto_embalagem
    ).group_by(
        EstoqueEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto
    ).all()
    
    return render_template("estoque.html", estoque_total=estoque_total)

@bp.route("/entrada_embalagem", methods=["POST"])
def entrada_embalagem():
    try:
        # Coleta os dados do formulário
        cod_produto = request.form.get("cod_produto_embalagem")
        nf = request.form.get("nf")
        quantidade_recebida = int(request.form.get("quantidade_recebida") or 0)
        responsavel = request.form.get("responsavel_recebimento")
        data_recebimento_str = request.form.get("data_recebimento")
        total = float(request.form.get("total") or 0.0)

        data_recebimento = datetime.strptime(data_recebimento_str, '%Y-%m-%d') if data_recebimento_str else datetime.now()
        
        # Valida se o produto existe
        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "error")
            return redirect(url_for("main.entrada"))

        # Cria um novo registro de entrada
        nova_entrada = EntradasEmbalagens(
            cod_produto_embalagem=cod_produto,
            nf=nf,
            quantidade_recebida=quantidade_recebida,
            responsavel_recebimento=responsavel,
            data_recebimento=data_recebimento,
            total=total,
        )
 
        db.session.add(nova_entrada)
        db.session.commit()
        flash("Entrada de embalagem registrada com sucesso!", "success")
 
    except (ValueError, TypeError) as e:
        flash(f"Erro ao processar o formulário: {e}", "error")
    
    return redirect(url_for("main.entrada"))

@bp.route("/saida_embalagem", methods=["POST"])
def saida_embalagem():
    try:
        # Coleta os dados do formulário de saída
        cod_produto = request.form.get("cod_produto_embalagem")
        op = request.form.get("op")
        quantidade_saida = int(request.form.get("quantidade_saida") or 0)
        responsavel = request.form.get("responsavel_saida")
        data_saida_str = request.form.get("data_saida")

        # Valida se o produto existe
        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "error")
            return redirect(url_for("main.saida"))

        data_saida = datetime.strptime(data_saida_str, '%Y-%m-%d') if data_saida_str else datetime.now()

        # Cria um novo registro de saída
        nova_saida = SaidasEmbalagem(
            cod_produto_embalagem=cod_produto,
            op=op,
            quantidade_saida=quantidade_saida,
            responsavel_saida=responsavel,
            data_saida=data_saida
        )
 
        db.session.add(nova_saida)
        db.session.commit()
        flash("Saída de embalagem registrada com sucesso!", "success")

    except (ValueError, TypeError) as e:
        flash(f"Erro ao processar o formulário: {e}", "error")
 
    return redirect(url_for("main.saida"))