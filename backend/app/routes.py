# Mantenha todas as suas importações originais
from flask import request, jsonify, Blueprint, render_template, redirect, url_for, flash, current_app
from datetime import date, datetime
from .models import db, EstoqueEmbalagem, EntradasEmbalagens, SaidasEmbalagem
from sqlalchemy.exc import IntegrityError
from flask_mail import Message
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image 
from reportlab.lib.styles import getSampleStyleSheet 
from reportlab.lib import colors
from io import BytesIO
import pandas as pd
import os

# Seu Blueprint existente
bp = Blueprint("main", __name__)

# --- Constantes e Funções Auxiliares (mantidas como estão) ---
RED_SOFT = colors.HexColor("#FFA07A") 
BLUE_SOFT = colors.HexColor("#ADD8E6") 
GREEN_SOFT = colors.HexColor("#90EE90")
FATOR_PROXIMIDADE = 50

def get_cell_color(estoque_atual, estoque_min, estoque_max):
    # ... (sua função de cor permanece a mesma)
    atual = int(estoque_atual) if estoque_atual is not None else 0
    min_val = int(estoque_min) if estoque_min is not None else -1
    max_val = int(estoque_max) if estoque_max is not None else float('inf')
    if min_val != -1 and atual <= min_val: return RED_SOFT
    if max_val != float('inf') and atual >= max_val: return GREEN_SOFT
    if min_val != -1:
        proximity_buffer = FATOR_PROXIMIDADE
        if max_val != float('inf'):
            if (max_val - min_val) < FATOR_PROXIMIDADE:
                proximity_buffer = (max_val - min_val) * 0.3
        proximity_limit = min_val + proximity_buffer
        if atual <= proximity_limit: return RED_SOFT
    return BLUE_SOFT

def obter_estoque_calculado():
    sub_entradas = db.session.query(
        EntradasEmbalagens.cod_produto_embalagem,
        db.func.sum(EntradasEmbalagens.quantidade_recebida).label('total_entrada')
    ).group_by(EntradasEmbalagens.cod_produto_embalagem).subquery('entradas')
    sub_saidas = db.session.query(
        SaidasEmbalagem.cod_produto_embalagem,
        db.func.sum(SaidasEmbalagem.quantidade_saida).label('total_saida')
    ).group_by(SaidasEmbalagem.cod_produto_embalagem).subquery('saidas')
    estoque_total_query = db.session.query(
        EstoqueEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        (db.func.coalesce(sub_entradas.c.total_entrada, 0) -
         db.func.coalesce(sub_saidas.c.total_saida, 0)).label('estoque_atual'),
        EstoqueEmbalagem.estoque_min,
        EstoqueEmbalagem.estoque_max
    ).outerjoin(
        sub_entradas, EstoqueEmbalagem.cod_produto_embalagem == sub_entradas.c.cod_produto_embalagem
    ).outerjoin(
        sub_saidas, EstoqueEmbalagem.cod_produto_embalagem == sub_saidas.c.cod_produto_embalagem
    ).order_by(EstoqueEmbalagem.cod_produto_embalagem).all()
    return estoque_total_query

# --- Rotas Principais ---
@bp.route("/")
def index():
    return redirect(url_for("main.entrada"))

@bp.route("/entrada")
def entrada():
    produtos_objetos = EstoqueEmbalagem.query.all()
    produtos_para_template = [{"cod_produto_embalagem": p.cod_produto_embalagem, "nome_produto": p.nome_produto, "padrao_embalagem": p.padrao_embalagem, "unidade_medida": p.unidade_medida} for p in produtos_objetos]
    return render_template("entrada.html", produtos_para_template=produtos_para_template)

@bp.route("/saida")
def saida():
    produtos_objetos = EstoqueEmbalagem.query.all()
    produtos_para_template = [{"cod_produto_embalagem": p.cod_produto_embalagem, "nome_produto": p.nome_produto, "padrao_embalagem": p.padrao_embalagem, "unidade_medida": p.unidade_medida} for p in produtos_objetos]
    return render_template("saida.html", produtos_para_template=produtos_para_template)

# =======================================================
# CORREÇÃO 2: Rota /estoque agora usa a função correta
# =======================================================
@bp.route("/estoque")
def estoque():
    """Rota para a página de visualização do estoque."""
    # AGORA USA A FUNÇÃO CORRETA PARA CALCULAR O ESTOQUE
    estoque_total = obter_estoque_calculado()
    
    data_local = datetime.now()
    return render_template(
        "estoque.html",
        # A função já retorna uma lista de tuplas, então não precisa do .all()
        estoque_total_embalagens=estoque_total, 
        data_local=data_local
    )
    
# --- Rotas de Registros Diários (mantidas como estão) ---
@bp.route('/registro/entradas/diario')
def registro_diario_entradas():
    data_filtro_str = request.args.get('data_filtro')
    if data_filtro_str:
        try: data_selecionada = datetime.strptime(data_filtro_str, '%Y-%m-%d').date()
        except ValueError: data_selecionada = date.today()
    else: data_selecionada = date.today()
    registros_do_dia = db.session.query(EntradasEmbalagens.cod_produto_embalagem, EstoqueEmbalagem.nome_produto, EntradasEmbalagens.nf, EntradasEmbalagens.pedido_compra, EntradasEmbalagens.quantidade_recebida, EntradasEmbalagens.responsavel_recebimento, EntradasEmbalagens.total).join(EstoqueEmbalagem, EntradasEmbalagens.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem).filter(db.func.date(EntradasEmbalagens.data_recebimento) == data_selecionada).order_by(EntradasEmbalagens.id.desc()).all()
    return render_template('registro-diario.html', registros=registros_do_dia, data_formatada=data_selecionada.strftime('%d/%m/%Y'), data_iso=data_selecionada.isoformat())

@bp.route('/registro/saidas/diario')
def registro_diario_saidas():
    data_filtro_str = request.args.get('data_filtro')
    if data_filtro_str:
        try: data_selecionada = datetime.strptime(data_filtro_str, '%Y-%m-%d').date()
        except ValueError: data_selecionada = date.today()
    else: data_selecionada = date.today()
    registros_do_dia = db.session.query(SaidasEmbalagem.cod_produto_embalagem, EstoqueEmbalagem.nome_produto, SaidasEmbalagem.op, SaidasEmbalagem.quantidade_saida, SaidasEmbalagem.responsavel_saida).join(EstoqueEmbalagem, SaidasEmbalagem.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem).filter(db.func.date(SaidasEmbalagem.data_saida) == data_selecionada).order_by(SaidasEmbalagem.id.desc()).all()
    return render_template('registro-diario-saida.html', registros=registros_do_dia, data_formatada=data_selecionada.strftime('%d/%m/%Y'), data_iso=data_selecionada.isoformat())

# --- Rotas de Processamento de Formulário ---
@bp.route("/entrada_embalagem", methods=["POST"])
def entrada_embalagem():
    # ... (código inalterado)
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        nf = request.form.get("nf")
        pedido_compra = request.form.get("pedido_compra")
        quantidade_recebida = int(request.form.get("quantidade_recebida") or 0)
        responsavel = request.form.get("responsavel_recebimento")
        data_recebimento_str = request.form.get("data_recebimento")
        total = float(request.form.get("valor_total") or 0.0)
        data_recebimento = datetime.strptime(data_recebimento_str, '%Y-%m-%d').date() if data_recebimento_str else date.today()
        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "danger")
            return redirect(url_for("main.entrada"))
        nova_entrada = EntradasEmbalagens(cod_produto_embalagem=cod_produto, nf=nf, pedido_compra=pedido_compra, quantidade_recebida=quantidade_recebida, responsavel_recebimento=responsavel, data_recebimento=data_recebimento, total=total)
        db.session.add(nova_entrada)
        db.session.commit()
        flash("Entrada de embalagem registrada com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro: {str(e)}", "danger")
    return redirect(url_for("main.entrada"))

# ============================================================
# CORREÇÃO 1: Função de saída agora pega "quantidade"
# ============================================================
@bp.route("/saida_embalagem", methods=["POST"])
def saida_embalagem():
    """Processa a saída de embalagens e salva no banco de dados."""
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        op = request.form.get("op")
        # CORRIGIDO DE "quantidade_saida" PARA "quantidade" PARA BATER COM O HTML
        quantidade_saida = int(request.form.get("quantidade") or 0)
        responsavel = request.form.get("responsavel_saida")
        data_saida_str = request.form.get("data_saida")

        data_saida = datetime.strptime(data_saida_str, '%Y-%m-%d').date() if data_saida_str else date.today()

        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "danger")
            return redirect(url_for("main.saida"))

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

    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro inesperado: {str(e)}", "danger")

    return redirect(url_for("main.saida"))

# --- Rota de Envio de Relatórios (mantida como está) ---
@bp.route('/enviar_estoque_tudo', methods=['POST'])
def enviar_estoque_tudo():
    # ... (seu código de envio de relatório permanece inalterado)
    try:
        estoque_total = obter_estoque_calculado()
        
        # ... (código de geração de PDF e Excel omitido para brevidade, mantenha o seu) ...
        
        flash('Relatórios (PDF e Excel) enviados com sucesso!', 'success')
        
    except Exception as e:
        flash(f"Erro ao enviar os relatórios: {str(e)}", 'danger')
        
    return redirect(url_for('main.estoque'))