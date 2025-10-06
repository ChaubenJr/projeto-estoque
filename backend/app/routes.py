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
    # 1. Obter todos os valores dos filtros da URL
    filtro_data_str = request.args.get('filtro_data')
    filtro_codigo = request.args.get('filtro_codigo', '').strip()
    filtro_nf = request.args.get('filtro_nf', '').strip()

    # Define a data selecionada (se não houver, usa a data de hoje)
    data_selecionada = None
    if filtro_data_str:
        try:
            data_selecionada = datetime.strptime(filtro_data_str, '%Y-%m-%d').date()
        except ValueError:
            data_selecionada = date.today() # Fallback em caso de data inválida
    else:
        # Se nenhum filtro de data for usado, não filtra por data (mostra tudo)
        # Se quiser que o padrão seja hoje, mude para: data_selecionada = date.today()
        pass

    # 2. Iniciar a consulta base, já com o JOIN
    query = db.session.query(
        EntradasEmbalagens.cod_produto_embalagem, 
        EstoqueEmbalagem.nome_produto, 
        EntradasEmbalagens.nf, 
        EntradasEmbalagens.pedido_compra, 
        EntradasEmbalagens.quantidade_recebida, 
        EntradasEmbalagens.responsavel_recebimento, 
        EntradasEmbalagens.total
    ).join(
        EstoqueEmbalagem, EntradasEmbalagens.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem
    )

    # 3. Aplicar os filtros na consulta SE eles foram preenchidos
    if data_selecionada:
        query = query.filter(db.func.date(EntradasEmbalagens.data_recebimento) == data_selecionada)
    
    if filtro_codigo:
        query = query.filter(EntradasEmbalagens.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))

    if filtro_nf:
        query = query.filter(EntradasEmbalagens.nf.ilike(f'%{filtro_nf}%'))

    # 4. Ordenar e executar a consulta final
    registros_do_dia = query.order_by(EntradasEmbalagens.id.desc()).all()
    
    # Prepara a data para exibição no subtítulo e para preencher o campo de data
    data_formatada = data_selecionada.strftime('%d/%m/%Y') if data_selecionada else "Todas as Datas"
    data_iso = data_selecionada.isoformat() if data_selecionada else ""

    # 5. Renderizar o template, passando os resultados E os filtros de volta
    return render_template(
        'registro-diario.html', 
        registros=registros_do_dia, 
        data_formatada=data_formatada, 
        data_iso=data_iso,
        filtro_codigo=filtro_codigo,
        filtro_nf=filtro_nf
    )

@bp.route('/registro/saidas/diario')
def registro_diario_saidas():
    # 1. Obter todos os valores dos filtros da URL
    filtro_data_str = request.args.get('filtro_data')
    filtro_codigo = request.args.get('filtro_codigo', '').strip()
    filtro_op = request.args.get('filtro_op', '').strip() # Filtro de OP

    # Define a data selecionada
    data_selecionada = None
    if filtro_data_str:
        try:
            data_selecionada = datetime.strptime(filtro_data_str, '%Y-%m-%d').date()
        except ValueError:
            data_selecionada = date.today()
    else:
        # Se nenhuma data for selecionada, não filtra por data
        pass

    # 2. Iniciar a consulta base com o JOIN
    query = db.session.query(
        SaidasEmbalagem.cod_produto_embalagem, 
        EstoqueEmbalagem.nome_produto, 
        SaidasEmbalagem.op, 
        SaidasEmbalagem.quantidade_saida, 
        SaidasEmbalagem.responsavel_saida
    ).join(
        EstoqueEmbalagem, SaidasEmbalagem.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem
    )

    # 3. Aplicar os filtros na consulta SE eles foram preenchidos
    if data_selecionada:
        query = query.filter(db.func.date(SaidasEmbalagem.data_saida) == data_selecionada)
    
    if filtro_codigo:
        query = query.filter(SaidasEmbalagem.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))

    if filtro_op:
        query = query.filter(SaidasEmbalagem.op.ilike(f'%{filtro_op}%'))

    # 4. Ordenar e executar a consulta final
    registros_do_dia = query.order_by(SaidasEmbalagem.id.desc()).all()
    
    # Prepara a data para exibição e para preencher o campo de data
    data_formatada = data_selecionada.strftime('%d/%m/%Y') if data_selecionada else "Todas as Datas"
    data_iso = data_selecionada.isoformat() if data_selecionada else ""

    # 5. Renderizar o template, passando os resultados E os filtros de volta
    return render_template(
        'registro-diario-saida.html', 
        registros=registros_do_dia, 
        data_formatada=data_formatada, 
        data_iso=data_iso,
        filtro_codigo=filtro_codigo,
        filtro_op=filtro_op
    )

# --- Rotas de Processamento de Formulário ---
@bp.route("/entrada_embalagem", methods=["POST"])
def entrada_embalagem():
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        nf = request.form.get("nf")
        pedido_compra = request.form.get("pedido_compra")
        quantidade_recebida = int(request.form.get("quantidade_recebida") or 0)
        responsavel = request.form.get("responsavel_recebimento")
        total = float(request.form.get("valor_total") or 0.0)

        # Captura data e hora separadamente
        data_str = request.form.get("data_recebimento")
        hora_str = request.form.get("hora_recebimento")

        # Combina data e hora e converte para um objeto datetime
        if data_str and hora_str:
            data_recebimento = datetime.strptime(f"{data_str} {hora_str}", '%Y-%m-%d %H:%M')
        else:
            data_recebimento = datetime.now() # Fallback para data e hora atuais

        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "danger")
            return redirect(url_for("main.entrada"))
            
        nova_entrada = EntradasEmbalagens(
            cod_produto_embalagem=cod_produto, 
            nf=nf, 
            pedido_compra=pedido_compra, 
            quantidade_recebida=quantidade_recebida, 
            responsavel_recebimento=responsavel, 
            data_recebimento=data_recebimento, # Salva o objeto datetime completo
            total=total
        )
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
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        op = request.form.get("op")
        quantidade_saida = int(request.form.get("quantidade") or 0)
        responsavel = request.form.get("responsavel_saida")
        
        # Captura data e hora separadamente
        data_str = request.form.get("data_saida")
        hora_str = request.form.get("hora_saida")

        # Combina data e hora e converte para um objeto datetime
        if data_str and hora_str:
            data_saida = datetime.strptime(f"{data_str} {hora_str}", '%Y-%m-%d %H:%M')
        else:
            data_saida = datetime.now()

        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "danger")
            return redirect(url_for("main.saida"))

        nova_saida = SaidasEmbalagem(
            cod_produto_embalagem=cod_produto,
            op=op,
            quantidade_saida=quantidade_saida,
            responsavel_saida=responsavel,
            data_saida=data_saida # Salva o objeto datetime completo
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

# routes.py

# ===================================================================
# ROTA CORRIGIDA - Cadastro de Produto
# O nome da URL e o nome da função foram alterados para 'cadastro'
# ===================================================================
@bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro(): # <-- NOME DA FUNÇÃO ALTERADO
    if request.method == 'POST':
        # Pega os dados do formulário
        cod_produto = request.form.get('cod_produto_embalagem')
        nome_produto = request.form.get('nome_produto')
        unidade = request.form.get('unidade_medida')
        padrao = request.form.get('padrao_embalagem')
        estoque_min = request.form.get('estoque_min')
        estoque_max = request.form.get('estoque_max')

        # Validação simples
        if not all([cod_produto, nome_produto, unidade, padrao, estoque_min, estoque_max]):
            flash('Todos os campos são obrigatórios.', 'danger')
            return redirect(url_for('main.cadastro'))
        
        # Verifica se o produto já existe
        if EstoqueEmbalagem.query.get(cod_produto):
            flash(f'O código de produto {cod_produto} já existe.', 'danger')
            return redirect(url_for('main.cadastro'))

        try:
            # Cria o novo produto e salva no banco
            novo_produto = EstoqueEmbalagem(
                cod_produto_embalagem=cod_produto,
                nome_produto=nome_produto,
                unidade_medida=unidade,
                padrao_embalagem=padrao,
                estoque_min=int(estoque_min),
                estoque_max=int(estoque_max)
            )
            db.session.add(novo_produto)
            db.session.commit()
            flash('Produto cadastrado com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar produto: {str(e)}', 'danger')

        return redirect(url_for('main.cadastro'))

    # Se for um GET, apenas mostra a página
    # Flask irá procurar por um arquivo chamado 'cadastro.html'
    return render_template('cadastro.html') # <-- NOME DO TEMPLATE ALTERADO

# routes.py

# ... (seus outros imports)
from sqlalchemy import union_all, select, literal_column

# routes.py

# ... (seus outros imports)
from sqlalchemy import union_all, literal_column

# ===================================================================
# ROTA ATUALIZADA - Movimentação com labels corrigidos para o Kardex
# ===================================================================
# Mantenha todos os seus outros imports e rotas como estão.
# Apenas a rota @bp.route('/movimentacao') será alterada.

# ... (outras importações)
from sqlalchemy import union_all, literal_column

# ... (outras rotas)


@bp.route('/movimentacao')
def movimentacao():
    # 1. Obtenção dos filtros (permanece igual)
    filtro_codigo = request.args.get('filtro_codigo', '').strip()
    filtro_nf = request.args.get('filtro_nf', '').strip()
    filtro_op = request.args.get('filtro_op', '').strip()
    filtro_data = request.args.get('filtro_data', '').strip()

    # Query para Entradas - AGORA SELECIONA 'nf' E 'op'
    q_entradas = db.session.query(
        EntradasEmbalagens.data_recebimento.label('data_hora'),
        literal_column("'Entrada'").label('tipo'),
        EntradasEmbalagens.cod_produto_embalagem.label('codigo_produto'),
        EstoqueEmbalagem.nome_produto.label('descricao_produto'),
        EntradasEmbalagens.quantidade_recebida.label('quantidade'),
        EntradasEmbalagens.nf.label('nf'),  # <-- Coluna NF
        literal_column("''").label('op') # <-- Coluna OP vazia
    ).join(EstoqueEmbalagem, EntradasEmbalagens.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem)

    # Query para Saídas - AGORA SELECIONA 'nf' E 'op'
    q_saidas = db.session.query(
        SaidasEmbalagem.data_saida.label('data_hora'),
        literal_column("'Saída'").label('tipo'),
        SaidasEmbalagem.cod_produto_embalagem.label('codigo_produto'),
        EstoqueEmbalagem.nome_produto.label('descricao_produto'),
        (SaidasEmbalagem.quantidade_saida * -1).label('quantidade'),
        literal_column("''").label('nf'), # <-- Coluna NF vazia
        SaidasEmbalagem.op.label('op')     # <-- Coluna OP
    ).join(EstoqueEmbalagem, SaidasEmbalagem.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem)

    # 2. Aplicação dos filtros (permanece igual)
    if filtro_codigo:
        q_entradas = q_entradas.filter(EntradasEmbalagens.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))
        q_saidas = q_saidas.filter(SaidasEmbalagem.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))
    
    if filtro_nf:
        q_entradas = q_entradas.filter(EntradasEmbalagens.nf.ilike(f'%{filtro_nf}%'))
        q_saidas = q_saidas.filter(literal_column("1") == "2") 

    if filtro_op:
        q_saidas = q_saidas.filter(SaidasEmbalagem.op.ilike(f'%{filtro_op}%'))
        q_entradas = q_entradas.filter(literal_column("1") == "2")

    if filtro_data:
        q_entradas = q_entradas.filter(db.func.date(EntradasEmbalagens.data_recebimento) == filtro_data)
        q_saidas = q_saidas.filter(db.func.date(SaidasEmbalagem.data_saida) == filtro_data)

    # 3. União das queries (permanece igual)
    query_final = union_all(q_entradas, q_saidas).alias('movimentacoes')
    resultados_brutos = db.session.query(query_final).order_by(query_final.c.data_hora.desc()).all()

    # 4. Lógica do Kardex (permanece igual)
    kardex = []
    saldos = {} 
    for mov in reversed(resultados_brutos):
        codigo = mov.codigo_produto
        if codigo not in saldos:
            saldos[codigo] = 0
        saldos[codigo] += mov.quantidade
        mov_com_saldo = dict(mov._mapping)
        mov_com_saldo['saldo_calculado'] = saldos[codigo]
        kardex.append(mov_com_saldo)
    kardex.reverse()

    # Formatação final para o template - AGORA COM 'nf' E 'op'
    movimentacoes_finais = []
    for mov in kardex:
        mov_formatada = {
            'data': mov['data_hora'].strftime('%d/%m/%Y'),
            'hora': mov['data_hora'].strftime('%H:%M:%S'),
            'codigo': mov['codigo_produto'],
            'descricao': mov['descricao_produto'],
            'nf': mov['nf'],  # <-- Campo NF
            'op': mov['op'],  # <-- Campo OP
            'entrada': mov['quantidade'] if mov['tipo'] == 'Entrada' else 0,
            'saida': abs(mov['quantidade']) if mov['tipo'] == 'Saída' else 0,
            'saldo': mov['saldo_calculado']
        }
        movimentacoes_finais.append(mov_formatada)

    # 5. Renderização (permanece igual)
    return render_template(
        'movimentacao.html', 
        movimentacoes=movimentacoes_finais,
        filtro_codigo=filtro_codigo,
        filtro_nf=filtro_nf,
        filtro_op=filtro_op,
        filtro_data=filtro_data
    )