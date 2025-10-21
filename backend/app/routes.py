# routes.py (reestruturado, comentado e com correções)
from flask import (
    Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
)
from datetime import date, datetime
from .models import db, EstoqueEmbalagem, EntradasEmbalagens, SaidasEmbalagem, Usuario
from sqlalchemy import func, union_all, literal_column
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from flask_mail import Message
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from io import BytesIO
import pandas as pd
import calendar
import os

bp = Blueprint("main", __name__)

# ---------------------------
# Constantes / Helpers
# ---------------------------
RED_SOFT = colors.HexColor("#FFA07A")
BLUE_SOFT = colors.HexColor("#ADD8E6")
GREEN_SOFT = colors.HexColor("#90EE90")
FATOR_PROXIMIDADE = 50


def get_cell_color(estoque_atual, estoque_min, estoque_max):
    """Determina a cor de alerta baseada no estoque atual e limites."""
    atual = int(estoque_atual) if estoque_atual is not None else 0
    min_val = int(estoque_min) if estoque_min is not None else -1
    max_val = int(estoque_max) if estoque_max is not None else float('inf')

    if min_val != -1 and atual <= min_val:
        return RED_SOFT
    if max_val != float('inf') and atual >= max_val:
        return GREEN_SOFT

    if min_val != -1:
        proximity_buffer = FATOR_PROXIMIDADE
        if max_val != float('inf'):
            if (max_val - min_val) < FATOR_PROXIMIDADE:
                proximity_buffer = (max_val - min_val) * 0.3
        proximity_limit = min_val + proximity_buffer
        if atual <= proximity_limit:
            return RED_SOFT

    return BLUE_SOFT


def obter_estoque_calculado():
    """Calcula o estoque atual de cada produto ativo (Entradas - Saídas)."""
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
    ).filter(EstoqueEmbalagem.ativo == True).outerjoin(
        sub_entradas, EstoqueEmbalagem.cod_produto_embalagem == sub_entradas.c.cod_produto_embalagem
    ).outerjoin(
        sub_saidas, EstoqueEmbalagem.cod_produto_embalagem == sub_saidas.c.cod_produto_embalagem
    ).order_by(EstoqueEmbalagem.cod_produto_embalagem).all()

    return estoque_total_query

def montar_movimentacoes_com_saldo(filtro_codigo=None, filtro_nf=None, filtro_op=None, filtro_data_str=None):
    """
    Retorna lista de dicts com as movimentações (com 'entrada' e 'saida' separados e 'saldo'),
    aplicando filtros opcionais e permitindo filtro por intervalo de datas (início, fim).
    """

    # ----- BUSCA DE ENTRADAS -----
    entradas = db.session.query(
        EntradasEmbalagens.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        db.literal('Entrada').label('tipo_movimentacao'),
        EntradasEmbalagens.quantidade_recebida.label('quantidade'),
        EntradasEmbalagens.data_recebimento.label('data'),
        EntradasEmbalagens.hora_recebimento.label('hora'),
        EntradasEmbalagens.nf.label('nf'),
        db.null().label('op')
    ).join(EstoqueEmbalagem, EstoqueEmbalagem.cod_produto_embalagem == EntradasEmbalagens.cod_produto_embalagem)

    # ----- BUSCA DE SAÍDAS -----
    saidas = db.session.query(
        SaidasEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        db.literal('Saída').label('tipo_movimentacao'),
        SaidasEmbalagem.quantidade_saida.label('quantidade'),
        SaidasEmbalagem.data_saida.label('data'),
        db.func.substr(SaidasEmbalagem.data_saida, 12, 8).label('hora'),
        db.null().label('nf'),
        SaidasEmbalagem.op.label('op')
    ).join(EstoqueEmbalagem, EstoqueEmbalagem.cod_produto_embalagem == SaidasEmbalagem.cod_produto_embalagem)

    todas_mov = entradas.union_all(saidas).order_by('data').all()

    # ----- CALCULA SALDO ACUMULADO -----
    saldo_por_produto = {}
    movimentacoes_com_saldo = []

    for mov in todas_mov:
        cod = mov.cod_produto_embalagem
        saldo_atual = saldo_por_produto.get(cod, 0)

        if mov.tipo_movimentacao == 'Entrada':
            saldo_atual += mov.quantidade
            entrada_val = mov.quantidade
            saida_val = 0.0
        else:
            saldo_atual -= mov.quantidade
            entrada_val = 0.0
            saida_val = mov.quantidade

        saldo_por_produto[cod] = saldo_atual

        movimentacoes_com_saldo.append({
            'cod_produto_embalagem': cod,
            'nome_produto': mov.nome_produto,
            'tipo_movimentacao': mov.tipo_movimentacao,
            'quantidade': mov.quantidade,
            'entrada': entrada_val,
            'saida': saida_val,
            'saldo': saldo_atual,
            'data': mov.data,
            'hora': getattr(mov, 'hora', ''),
            'nf': getattr(mov, 'nf', ''),
            'op': getattr(mov, 'op', '')
        })

    # ----- APLICA FILTROS -----
    if filtro_codigo:
        movimentacoes_com_saldo = [m for m in movimentacoes_com_saldo if filtro_codigo in (m['cod_produto_embalagem'] or '')]
    if filtro_nf:
        movimentacoes_com_saldo = [m for m in movimentacoes_com_saldo if filtro_nf in (m['nf'] or '')]
    if filtro_op:
        movimentacoes_com_saldo = [m for m in movimentacoes_com_saldo if filtro_op in (m['op'] or '')]

    # ----- FILTRO DE DATA (individual OU intervalo) -----
    if filtro_data_str:
        # 👉 Caso seja intervalo (tupla)
        if isinstance(filtro_data_str, tuple) and len(filtro_data_str) == 2:
            data_inicio = datetime.fromisoformat(filtro_data_str[0])
            data_fim = datetime.fromisoformat(filtro_data_str[1])
            movimentacoes_com_saldo = [
                m for m in movimentacoes_com_saldo
                if isinstance(m['data'], datetime)
                and data_inicio.date() <= m['data'].date() <= data_fim.date()
            ]
        else:
            # 👉 Caso seja uma única data (string)
            movimentacoes_com_saldo = [
                m for m in movimentacoes_com_saldo
                if isinstance(m['data'], datetime)
                and m['data'].date().isoformat() == filtro_data_str
            ]

    return movimentacoes_com_saldo



# ---------------------------
# AUTENTICAÇÃO
# ---------------------------
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            flash('Informe usuário e senha.', 'danger')
            return redirect(url_for('main.login'))

        # Busca usuário case-insensitive
        user = Usuario.query.filter(func.lower(Usuario.username) == func.lower(username)).first()

        if not user:
            flash('Usuário ou senha inválidos.', 'danger')
            return redirect(url_for('main.login'))

        # Verificação de senha
        password_ok = False

        # Método check_password
        if callable(getattr(user, 'check_password', None)):
            try:
                password_ok = user.check_password(password)
            except Exception:
                password_ok = False

        # Campos comuns de hash ou senha
        if not password_ok:
            for field in ['password_hash', 'senha_hash', 'password', 'senha']:
                stored = getattr(user, field, None)
                if stored:
                    try:
                        password_ok = check_password_hash(stored, password)
                    except Exception:
                        password_ok = (stored == password)
                    if password_ok:
                        break

        # Verifica se o Usuário está ativo
        if not password_ok or getattr(user, 'ativo', True) is False:
            flash('Usuário ou senha inválidos, ou usuário inativo.', 'danger')
            return redirect(url_for('main.login'))

        # Login Flask-Login
        login_user(user)
        flash(f'Bem-vindo(a), {user.username}!', 'success')
        return redirect(url_for('main.cadastro'))

    return render_template('login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('main.login'))


# ---------------------------
# PÁGINAS PRINCIPAIS
# ---------------------------
@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.entrada"))
    return redirect(url_for("main.login"))


@bp.route("/entrada")
def entrada():
    produtos_objetos = EstoqueEmbalagem.query.filter_by(ativo=True).all()
    produtos_para_template = [
        {
            "cod_produto_embalagem": p.cod_produto_embalagem,
            "nome_produto": p.nome_produto,
            "padrao_embalagem": p.padrao_embalagem,
            "unidade_medida": p.unidade_medida
        } for p in produtos_objetos
    ]
    return render_template("entrada.html", produtos_para_template=produtos_para_template)


@bp.route("/saida")
def saida():
    produtos_objetos = EstoqueEmbalagem.query.filter_by(ativo=True).all()
    produtos_para_template = [
        {
            "cod_produto_embalagem": p.cod_produto_embalagem,
            "nome_produto": p.nome_produto,
            "padrao_embalagem": p.padrao_embalagem,
            "unidade_medida": p.unidade_medida
        } for p in produtos_objetos
    ]
    return render_template("saida.html", produtos_para_template=produtos_para_template)


@bp.route("/estoque")
def estoque():
    estoque_total = obter_estoque_calculado()
    data_local = datetime.now()
    return render_template("estoque.html", estoque_total_embalagens=estoque_total, data_local=data_local)


# ---------------------------
# REGISTROS DIÁRIOS
# ---------------------------
@bp.route('/registro/entradas/diario')
def registro_diario_entradas():
    filtro_data_str = request.args.get('filtro_data')
    filtro_codigo = request.args.get('filtro_codigo', '').strip()
    filtro_nf = request.args.get('filtro_nf', '').strip()

    data_selecionada = None
    if filtro_data_str:
        try:
            data_selecionada = datetime.strptime(filtro_data_str, '%Y-%m-%d').date()
        except ValueError:
            data_selecionada = date.today()

    query = db.session.query(
        EntradasEmbalagens.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        EntradasEmbalagens.nf,
        EntradasEmbalagens.pedido_compra,
        EntradasEmbalagens.quantidade_recebida,
        EntradasEmbalagens.responsavel_recebimento,
        EntradasEmbalagens.total
    ).join(EstoqueEmbalagem, EntradasEmbalagens.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem)

    if data_selecionada:
        query = query.filter(db.func.date(EntradasEmbalagens.data_recebimento) == data_selecionada)
    if filtro_codigo:
        query = query.filter(EntradasEmbalagens.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))
    if filtro_nf:
        query = query.filter(EntradasEmbalagens.nf.ilike(f'%{filtro_nf}%'))

    registros_do_dia = query.order_by(EntradasEmbalagens.id.desc()).all()
    data_formatada = data_selecionada.strftime('%d/%m/%Y') if data_selecionada else "Todas as Datas"
    data_iso = data_selecionada.isoformat() if data_selecionada else ""

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
    filtro_data_str = request.args.get('filtro_data')
    filtro_codigo = request.args.get('filtro_codigo', '').strip()
    filtro_op = request.args.get('filtro_op', '').strip()

    data_selecionada = None
    if filtro_data_str:
        try:
            data_selecionada = datetime.strptime(filtro_data_str, '%Y-%m-%d').date()
        except ValueError:
            data_selecionada = date.today()

    query = db.session.query(
        SaidasEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        SaidasEmbalagem.op,
        SaidasEmbalagem.quantidade_saida,
        SaidasEmbalagem.responsavel_saida
    ).join(EstoqueEmbalagem, SaidasEmbalagem.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem)

    if data_selecionada:
        query = query.filter(db.func.date(SaidasEmbalagem.data_saida) == data_selecionada)
    if filtro_codigo:
        query = query.filter(SaidasEmbalagem.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))
    if filtro_op:
        query = query.filter(SaidasEmbalagem.op.ilike(f'%{filtro_op}%'))

    registros_do_dia = query.order_by(SaidasEmbalagem.id.desc()).all()
    data_formatada = data_selecionada.strftime('%d/%m/%Y') if data_selecionada else "Todas as Datas"
    data_iso = data_selecionada.isoformat() if data_selecionada else ""

    return render_template(
        'registro-diario-saida.html',
        registros=registros_do_dia,
        data_formatada=data_formatada,
        data_iso=data_iso,
        filtro_codigo=filtro_codigo,
        filtro_op=filtro_op
    )


# ---------------------------
# ENTRADA / SAÍDA FORM HANDLERS
# ---------------------------
@bp.route("/entrada_embalagem", methods=["POST"])
def entrada_embalagem():
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        nf = request.form.get("nf")
        pedido_compra = request.form.get("pedido_compra")
        quantidade_recebida = int(request.form.get("quantidade_recebida") or 0)
        responsavel = request.form.get("responsavel_recebimento")
        total = float(request.form.get("valor_total") or 0.0)

        data_str = request.form.get("data_recebimento")
        hora_str = request.form.get("hora_recebimento")
        
        # --- LÓGICA DE TRATAMENTO DE DATA E HORA MODIFICADA ---
        
        # 1. Trata a Data (para a coluna DATE)
        # Converte a string YYYY-MM-DD em um objeto date do Python
        if data_str:
            data_a_salvar = datetime.strptime(data_str, '%Y-%m-%d').date()
        else:
            data_a_salvar = None

        # 2. Trata a Hora (para a coluna TIME)
        # Converte a string HH:MM em um objeto time do Python
        if hora_str:
            # Assumindo que a hora no formulário está sempre no formato HH:MM
            hora_a_salvar = datetime.strptime(hora_str, '%H:%M').time()
        else:
            # Se a hora não vier, salva 00:00:00 (ou o valor padrão do seu BD)
            hora_a_salvar = time(0, 0) # Exemplo: Salva 00:00:00
        
        # --- FIM DA LÓGICA DE TRATAMENTO ---

        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto or not produto.ativo:
            flash("Erro: Código de produto não encontrado ou inativo.", "danger")
            return redirect(url_for("main.entrada"))

        nova_entrada = EntradasEmbalagens(
            cod_produto_embalagem=cod_produto,
            nf=nf,
            pedido_compra=pedido_compra,
            quantidade_recebida=quantidade_recebida,
            responsavel_recebimento=responsavel,
            
            # ATRIBUIÇÃO PARA COLUNAS SEPARADAS
            data_recebimento=data_a_salvar,   # Envia apenas a data (tipo DATE)
            hora_recebimento=hora_a_salvar,   # Envia apenas a hora (tipo TIME)
            
            total=total
        )
        db.session.add(nova_entrada)
        db.session.commit()
        
        flash("Entrada de embalagem registrada com sucesso!", "success")
        
    except Exception as e:
        db.session.rollback()
        # É útil saber o erro, mas em produção você pode querer um log mais genérico.
        flash(f"Ocorreu um erro ao registrar a entrada: {str(e)}", "danger") 
        
    return redirect(url_for("main.entrada"))


@bp.route("/saida_embalagem", methods=["POST"])
def saida_embalagem():
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        op = request.form.get("op")
        quantidade_saida = int(request.form.get("quantidade") or 0)
        responsavel = request.form.get("responsavel_saida")

        data_str = request.form.get("data_saida")
        hora_str = request.form.get("hora_saida")
        if data_str and hora_str:
            data_saida = datetime.strptime(f"{data_str} {hora_str}", '%Y-%m-%d %H:%M')
        else:
            data_saida = datetime.now()

        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto or not produto.ativo:
            flash("Erro: Código de produto não encontrado ou inativo.", "danger")
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


# ---------------------------
# ENVIO DE RELATÓRIO DE ESTOQUE
# ---------------------------
@bp.route('/enviar_estoque_tudo', methods=['POST'])
def enviar_estoque_tudo():
    try:
        estoque_total = obter_estoque_calculado()

        buffer_pdf = BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=letter)
        Story = []
        styles = getSampleStyleSheet()

        logo_path = os.path.join(current_app.root_path, 'static', 'img', 'Logo ITP.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=125, height=75)
            Story.append(logo)
            Story.append(Spacer(1, 12))

        titulo = Paragraph("<b>Relatório de Estoque de Embalagens</b>", styles['h1'])
        titulo.style.alignment = 1
        Story.append(titulo)
        Story.append(Spacer(1, 12))

        data_relatorio = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        data_p = Paragraph(f"Data de Geração: {data_relatorio}", styles['Normal'])
        data_p.style.alignment = 1
        Story.append(data_p)
        Story.append(Spacer(1, 24))

        data_pdf = [['Código', 'Descrição', 'Estoque Atual', 'Estoque Min', 'Estoque Max']]
        cell_styles = []

        for i, item in enumerate(estoque_total):
            cod, desc, atual, min_val, max_val = item
            cor = get_cell_color(atual, min_val, max_val)
            cell_styles.append(('BACKGROUND', (2, i + 1), (2, i + 1), cor))
            data_pdf.append([
                str(cod),
                str(desc),
                str(atual),
                str(min_val if min_val is not None else 'N/A'),
                str(max_val if max_val is not None else 'N/A')
            ])

        table = Table(data_pdf)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#010162")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])

        for i in range(1, len(data_pdf)):
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor("#EEEEEE") if i % 2 == 0 else colors.white)

        for style in cell_styles:
            table_style.add(*style)

        table.setStyle(table_style)
        Story.append(table)
        Story.append(Spacer(1, 24))

        legenda_titulo = Paragraph("<b>Guia de Alerta de Estoque:</b>", styles['h3'])
        Story.append(legenda_titulo)
        Story.append(Spacer(1, 6))

        legenda_data = [
            [
                Table([[' ']], colWidths=[20], style=TableStyle([('BACKGROUND', (0, 0), (0, 0), BLUE_SOFT), ('GRID', (0, 0), (0, 0), 0.5, colors.black)])),
                Paragraph("Estoque Normal (Azul): Estoque OK (Acima da Zona de Alerta e Abaixo de Máximo).", styles['Normal'])
            ],
            [
                Table([[' ']], colWidths=[20], style=TableStyle([('BACKGROUND', (0, 0), (0, 0), RED_SOFT), ('GRID', (0, 0), (0, 0), 0.5, colors.black)])),
                Paragraph(f"Alerta Mínimo (Vermelho): Estoque no Mínimo ou Abaixo, OU na Zona de Proximidade (até {FATOR_PROXIMIDADE} acima do Mínimo, ajustado pelo Máximo).", styles['Normal'])
            ],
            [
                Table([[' ']], colWidths=[20], style=TableStyle([('BACKGROUND', (0, 0), (0, 0), GREEN_SOFT), ('GRID', (0, 0), (0, 0), 0.5, colors.black)])),
                Paragraph("Alerta Máximo (Verde): Estoque no Máximo ou Acima.", styles['Normal'])
            ]
        ]

        legenda_table = Table(legenda_data, colWidths=[150, 400])
        legenda_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        Story.append(legenda_table)

        doc.build(Story)
        buffer_pdf.seek(0)

        # Excel
        df = pd.DataFrame(
            estoque_total,
            columns=['Código', 'Descrição', 'Estoque Atual', 'Estoque Mínimo', 'Estoque Máximo']
        )
        buffer_excel = BytesIO()
        writer = pd.ExcelWriter(buffer_excel, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Estoque Embalagens')
        writer.close()
        buffer_excel.seek(0)

        msg = Message(
            'Relatórios de Estoque (PDF e Excel) {data_realtório}'.format(data_realtório=datetime.now().strftime('%d/%m/%Y')),
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[current_app.config.get('MAIL_RECIPIENT', 'clewertonsouza8@gmail.com')]
        )
        msg.body = 'Prezado, em anexo os relatórios de estoque (PDF e Excel).'
        msg.attach('Relatorio_Estoque.pdf', 'application/pdf', buffer_pdf.getvalue())
        msg.attach('Relatorio_Estoque.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer_excel.getvalue())

        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            flash('Relatórios (PDF e Excel) enviados com sucesso!', 'success')
        else:
            flash('Erro: Flask-Mail não está configurado. Verifique a configuração.', 'danger')

    except FileNotFoundError:
        flash("Erro: o arquivo do logo não foi encontrado.", 'danger')
    except Exception as e:
        flash(f"Erro ao enviar os relatórios: {str(e)}", 'danger')

    return redirect(url_for('main.estoque'))


# ---------------------------
# CADASTRO / ALTERAÇÃO / INATIVAÇÃO (com reativação automática)
# ---------------------------
@bp.route('/cadastro', methods=['GET', 'POST'])
@login_required
def cadastro():
    """
    Gerencia cadastro, alteração e inativação.
    Se um produto inativo for alterado, ele será reativado (ativo=True).
    """
    if request.method == 'POST':
        action = request.form.get('action')
        cod_produto = (request.form.get('cod_produto_embalagem') or '').strip()

        if not cod_produto:
            flash('O código do produto é obrigatório.', 'danger')
            return redirect(url_for('main.cadastro'))

        # recupera o produto (ORM)
        produto = EstoqueEmbalagem.query.get(cod_produto)

        try:
            if action == 'cadastrar':
                if produto:
                    flash(f'O código de produto {cod_produto} já existe. Use Alterar.', 'warning')
                else:
                    novo_produto = EstoqueEmbalagem(
                        cod_produto_embalagem=cod_produto,
                        nome_produto=request.form.get('nome_produto') or '',
                        unidade_medida=request.form.get('unidade_medida') or '',
                        padrao_embalagem=request.form.get('padrao_embalagem') or '',
                        estoque_min=int(request.form.get('estoque_min') or 0),
                        estoque_max=int(request.form.get('estoque_max') or 0),
                        ativo=True
                    )
                    db.session.add(novo_produto)
                    db.session.commit()
                    flash(f'Produto {cod_produto} cadastrado com sucesso!', 'success')

            elif action == 'alterar':
                if not produto:
                    flash(f'Produto com código {cod_produto} não encontrado para alteração.', 'danger')
                else:
                    produto.nome_produto = request.form.get('nome_produto') or produto.nome_produto
                    produto.unidade_medida = request.form.get('unidade_medida') or produto.unidade_medida
                    produto.padrao_embalagem = request.form.get('padrao_embalagem') or produto.padrao_embalagem

                    # trata campos numéricos (permite vazio no front => manter valor atual ou zerar)
                    estoque_min_raw = request.form.get('estoque_min')
                    estoque_max_raw = request.form.get('estoque_max')
                    produto.estoque_min = int(estoque_min_raw) if estoque_min_raw not in (None, '') else produto.estoque_min
                    produto.estoque_max = int(estoque_max_raw) if estoque_max_raw not in (None, '') else produto.estoque_max

                    # REATIVA automatico caso estivesse inativo
                    if not produto.ativo:
                        produto.ativo = True

                    db.session.commit()
                    flash(f'Produto {cod_produto} alterado com sucesso e reativado (se estava inativo).', 'success')

            elif action == 'inativar':
                if not produto:
                    flash(f'Produto com código {cod_produto} não encontrado para inativação.', 'danger')
                elif not produto.ativo:
                    flash(f'Produto {cod_produto} já está inativo.', 'info')
                else:
                    produto.ativo = False
                    db.session.commit()
                    flash(f'Produto {cod_produto} inativado com sucesso!', 'warning')
            else:
                flash('Ação inválida de formulário.', 'danger')

        except IntegrityError:
            db.session.rollback()
            flash('Erro de integridade do banco de dados (chave duplicada, etc.).', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro inesperado ao processar: {str(e)}', 'danger')

        return redirect(url_for('main.cadastro'))

    # GET: mostra o template
    return render_template('cadastro_produto.html')


# ---------------------------
# Cadastro de usuário / alteração de senha
# ---------------------------
@bp.route('/cadastro_usuario', methods=['GET', 'POST'])
@login_required
def cadastro_usuario():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            flash('Informe usuário e senha.', 'danger')
            return redirect(url_for('main.cadastro_usuario'))

        existing_user = Usuario.query.filter(func.lower(Usuario.username) == func.lower(username)).first()
        if existing_user:
            flash('Usuário já existe.', 'warning')
            return redirect(url_for('main.cadastro_usuario'))

        senha_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

        user = Usuario(username=username, password_hash=senha_hash, ativo=True)
        db.session.add(user)
        db.session.commit()

        flash(f'Usuário {username} cadastrado com sucesso!', 'success')
        return redirect(url_for('main.login'))

    # CASO GET ou qualquer outro caminho que não seja POST
    return render_template('cadastro_usuario.html')

@bp.route('/alterar_senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha') or ''
        confirmacao_senha = request.form.get('confirmacao_senha') or ''

        if not nova_senha or not confirmacao_senha:
            flash("Ambos os campos de nova senha são obrigatórios.", 'danger')
            return redirect(url_for('main.alterar_senha'))

        if nova_senha != confirmacao_senha:
            flash("A nova senha e a confirmação não coincidem.", 'danger')
            return redirect(url_for('main.alterar_senha'))

        try:
            # Sempre usa pbkdf2:sha256 para manter consistência
            password_hash = generate_password_hash(
                nova_senha,
                method='pbkdf2:sha256',
                salt_length=16
            )

            if hasattr(current_user, 'password_hash'):
                current_user.password_hash = password_hash
            elif hasattr(current_user, 'senha_hash'):
                current_user.senha_hash = password_hash
            else:
                flash("Erro: o modelo de usuário não possui campo de senha reconhecido.", 'danger')
                return redirect(url_for('main.alterar_senha'))

            db.session.commit()
            flash('Senha alterada com sucesso! Faça login novamente.', 'success')
            return redirect(url_for('main.logout'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao alterar senha: {str(e)}', 'danger')
            return redirect(url_for('main.alterar_senha'))

    return render_template('alterar_senha.html')

# ---------------------------
# API de consulta de produto (usada pelo front-end)
# ---------------------------
@bp.route('/api/consulta_produto/<string:codigo>', methods=['GET'])
@login_required
def consulta_produto(codigo):
    try:
        produto = EstoqueEmbalagem.query.filter(func.lower(EstoqueEmbalagem.cod_produto_embalagem) == func.lower(codigo)).first()
        if not produto:
            return jsonify({"status": "not_found"}), 404

        return jsonify({
            "status": "success",
            "produto": {
                "cod_produto_embalagem": produto.cod_produto_embalagem,
                "nome_produto": produto.nome_produto,
                "unidade_medida": produto.unidade_medida,
                "padrao_embalagem": produto.padrao_embalagem,
                "estoque_min": produto.estoque_min,
                "estoque_max": produto.estoque_max,
                "ativo": produto.ativo
            }
        }), 200
    except Exception as e:
        current_app.logger.exception("Erro na consulta_produto")
        return jsonify({"status": "error", "message": "Erro interno do servidor."}), 500


# ---------------------------
# Movimentações (Kardex) - lógica centralizada e rota
# ---------------------------
def obter_movimentacoes_kardex_sql_alchemy(filtro_codigo, filtro_nf, filtro_op, filtro_data_str):
    """
    Centraliza a lógica de consulta UNION e o cálculo do Saldo.
    Retorna lista de dicts com campos: data, hora, codigo, descricao, nf, op, entrada, saida, saldo
    """
    data_selecionada = None
    if filtro_data_str:
        try:
            data_selecionada = datetime.strptime(filtro_data_str, '%Y-%m-%d').date()
        except ValueError:
            # ignora filtro de data inválido
            data_selecionada = None

    entradas_query = db.session.query(
        EntradasEmbalagens.data_recebimento.label('data_hora'),
        EntradasEmbalagens.cod_produto_embalagem.label('codigo'),
        EstoqueEmbalagem.nome_produto.label('descricao'),
        EntradasEmbalagens.nf.label('nf'),
        literal_column("NULL").label('op'),
        EntradasEmbalagens.quantidade_recebida.label('entrada'),
        literal_column("0").label('saida')
    ).join(EstoqueEmbalagem, EntradasEmbalagens.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem)

    saidas_query = db.session.query(
        SaidasEmbalagem.data_saida.label('data_hora'),
        SaidasEmbalagem.cod_produto_embalagem.label('codigo'),
        EstoqueEmbalagem.nome_produto.label('descricao'),
        literal_column("NULL").label('nf'),
        SaidasEmbalagem.op.label('op'),
        literal_column("0").label('entrada'),
        SaidasEmbalagem.quantidade_saida.label('saida')
    ).join(EstoqueEmbalagem, SaidasEmbalagem.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem)

    if filtro_codigo:
        entradas_query = entradas_query.filter(EntradasEmbalagens.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))
        saidas_query = saidas_query.filter(SaidasEmbalagem.cod_produto_embalagem.ilike(f'%{filtro_codigo}%'))
    if filtro_nf:
        entradas_query = entradas_query.filter(EntradasEmbalagens.nf.ilike(f'%{filtro_nf}%'))
    if filtro_op:
        saidas_query = saidas_query.filter(SaidasEmbalagem.op.ilike(f'%{filtro_op}%'))
    if data_selecionada:
        entradas_query = entradas_query.filter(db.func.date(EntradasEmbalagens.data_recebimento) <= data_selecionada)
        saidas_query = saidas_query.filter(db.func.date(SaidasEmbalagem.data_saida) <= data_selecionada)

    union_query = union_all(entradas_query, saidas_query).subquery()
    movimentacoes_brutas = db.session.query(union_query).order_by(union_query.c.data_hora.asc()).all()

    movimentacoes_com_saldo = []
    saldo_atual = 0
    for mov in movimentacoes_brutas:
        data_hora_mov = mov.data_hora
        saldo_atual += (mov.entrada - mov.saida)
        movimentacoes_com_saldo.append({
            'data': data_hora_mov.strftime('%d/%m/%Y'),
            'hora': data_hora_mov.strftime('%H:%M:%S'),
            'codigo': mov.codigo,
            'descricao': mov.descricao,
            'nf': mov.nf,
            'op': mov.op,
            'entrada': mov.entrada,
            'saida': mov.saida,
            'saldo': saldo_atual
        })

    return movimentacoes_com_saldo

@bp.route('/movimentacao', methods=['GET'])
def movimentacao():
    filtro_codigo = request.args.get('filtro_codigo', '').strip()
    filtro_nf = request.args.get('filtro_nf', '').strip()
    filtro_op = request.args.get('filtro_op', '').strip()
    filtro_data_inicio = request.args.get('filtro_data_inicio', '').strip()
    filtro_data_fim = request.args.get('filtro_data_fim', '').strip()

    # Valores internos para filtro de data
    if not filtro_data_inicio or not filtro_data_fim:
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        ultimo_dia = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
        data_inicio_interna = primeiro_dia.strftime('%Y-%m-%d')
        data_fim_interna = ultimo_dia.strftime('%Y-%m-%d')
    else:
        data_inicio_interna = filtro_data_inicio
        data_fim_interna = filtro_data_fim

    # Monta as movimentações filtradas
    movimentacoes_com_saldo = montar_movimentacoes_com_saldo(
        filtro_codigo or None,
        filtro_nf or None,
        filtro_op or None,
        (data_inicio_interna, data_fim_interna)
    )

    # Se for requisição AJAX, retorna apenas o partial da tabela
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('partials/tabela_movimentacoes.html', movimentacoes=movimentacoes_com_saldo)

    # Página completa: inputs de data permanecem vazios
    return render_template(
        'movimentacao.html',
        movimentacoes=movimentacoes_com_saldo,
        filtro_codigo=filtro_codigo,
        filtro_data_inicio='',  # input vazio
        filtro_data_fim='',     # input vazio
        filtro_nf=filtro_nf,
        filtro_op=filtro_op
    )


@bp.route('/movimentacao/enviar_relatorios', methods=['POST'])
def enviar_movimentacoes_tudo():
    try:
        filtro_codigo = request.form.get('filtro_codigo', '')
        filtro_data_str = request.form.get('filtro_data', '')
        filtro_nf = request.form.get('filtro_nf', '')
        filtro_op = request.form.get('filtro_op', '')

        movimentacoes = montar_movimentacoes_com_saldo(
        filtro_codigo.strip() or None,
        filtro_nf.strip() or None,
        filtro_op.strip() or None,
        filtro_data_str.strip() or None)

        if not movimentacoes:
            flash("Nenhuma movimentação encontrada com os filtros especificados. E-mail não enviado.", 'warning')
            return redirect(url_for('main.movimentacao',
                                     filtro_codigo=filtro_codigo,
                                     filtro_nf=filtro_nf,
                                     filtro_op=filtro_op,
                                     filtro_data=filtro_data_str))

        current_app.logger.info("Enviar Relatórios - filtros: %s %s %s %s", filtro_codigo, filtro_nf, filtro_op, filtro_data_str)
        current_app.logger.info("Movimentacoes para PDF (count=%d): %s", len(movimentacoes), movimentacoes[:5])


        # --- Geração do PDF em paisagem (Kardex) ---
        buffer_pdf = BytesIO()
        # Garante a orientação paisagem (landscape(letter)) e margens reduzidas
        doc = SimpleDocTemplate(
            buffer_pdf,
            pagesize=landscape(letter),
            leftMargin=10,
            rightMargin=10,
            topMargin=10,
            bottomMargin=10
        )
        Story = []
        styles = getSampleStyleSheet()

        # Título - Padrão limpo da imagem
        titulo = Paragraph("Relatório Kardex Movimentações", styles['Heading1'])
        titulo.style.alignment = 0 # 0 para esquerda (como na imagem)
        titulo.style.fontName = 'Helvetica-Bold'
        Story.append(titulo)
        Story.append(Spacer(1, 6)) # Espaçamento menor para visual mais compacto

        # Filtros (Mantidos)
        filtros_p = Paragraph(
            f"Filtros: Cód: {filtro_codigo or 'Todos'} | Data: {filtro_data_str or 'Todas'} | NF: {filtro_nf or 'Todas'} | OP: {filtro_op or 'Todas'}",
            styles['Normal']
        )
        filtros_p.style.fontSize = 8
        filtros_p.style.alignment = 0
        Story.append(filtros_p)
        Story.append(Spacer(1, 12))

        # Data de geração do relatório
        data_hora_geracao = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        data_geracao_p = Paragraph(f"Geração do relatório: {data_hora_geracao}", styles['Normal'])
        data_geracao_p.style.fontSize = 8
        data_geracao_p.style.alignment = 0
        Story.append(data_geracao_p)
        Story.append(Spacer(1, 12))

        # Dados da tabela
        # ORDEM ATUAL: Cód. Produto, Descrição, Data, S1 (NF), S2 (OP), Entrada, Saída, Saldo Atual
        data_pdf = [['Cód. Produto', 'Descrição', 'Data', 'S1 (NF)', 'S2 (OP)', 'Entrada', 'Saída', 'Saldo Atual']]
        
        for mov in movimentacoes:
            entrada = mov.get('entrada', 0.0)
            saida = mov.get('saida', 0.0)
            saldo = mov.get('saldo', 0.0)
        
            entrada_str = f"{entrada:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',') if entrada > 0 else ''
            saida_str = f"{saida:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',') if saida > 0 else ''
            saldo_str = f"{saldo:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',')
        
            row = [
                mov.get('cod_produto_embalagem') or mov.get('codigo', ''),
                mov.get('nome_produto') or mov.get('descricao', ''),
                mov.get('data').strftime('%d/%m/%Y') if mov.get('data') else '',
                mov.get('nf', ''),
                mov.get('op', ''),
                entrada_str,
                saida_str,
                saldo_str
            ]
            data_pdf.append(row)

        # Ajuste inteligente das larguras (NOVA IMPLEMENTAÇÃO)
        def calcular_larguras(data, col_desc_index=1):
            page_width = landscape(letter)[0] - 20 # Largura útil da página (792 - 10 - 10) = 772 pts
            col_count = len(data[0])
            
            # Larguras FIXAS para as colunas de Código, Data, S1, S2, Entrada, Saída, Saldo (em pontos)
            # Index: 0       1           2       3      4      5        6       7
            # Nome: Cód.   Descrição  Data    S1(NF) S2(OP) Entrada  Saída  Saldo Atual
            larguras = [
                80,        # [0] Cód. Produto
                0,         # [1] Descrição (Calculada depois)
                65,        # [2] Data
                75,        # [3] S1 (NF)
                75,        # [4] S2 (OP)
                70,        # [5] Entrada
                70,        # [6] Saída
                75         # [7] Saldo Atual
            ]
            
            # Calcula o espaço ocupado pelas colunas fixas
            largura_fixa_total = sum(larguras)
            
            # Aloca o espaço restante para a Descrição (índice 1)
            largura_descricao = max(100, page_width - largura_fixa_total) # Garante pelo menos 100pt ou o que sobrar
            
            # Define a largura da Descrição no array
            larguras[col_desc_index] = largura_descricao
            
            # Verifica se a soma final está ok (deve ser aproximadamente 772)
            # print(f"Largura Total Calculada: {sum(larguras)}")
            
            return larguras

        col_widths = calcular_larguras(data_pdf)

        # Criação da tabela
        table = Table(data_pdf, colWidths=col_widths)
        table_style = TableStyle([
            # Cabeçalho - Limpo, como na imagem
            ('ALIGN', (0, 0), (-1, 0), 'LEFT'), # Cabeçalho à esquerda (como na imagem)
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), 
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6), 
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black), # Linha divisória fina abaixo do cabeçalho
            
            # Corpo da Tabela
            ('ALIGN', (2, 1), (2, -1), 'CENTER'), # Data centralizada (Index 2)
            ('ALIGN', (3, 1), (4, -1), 'LEFT'),   # S1 (NF) e S2 (OP) à esquerda (Index 3 e 4)
            ('ALIGN', (5, 1), (-1, -1), 'RIGHT'), # Entrada, Saída, Saldo à direita (Index 5 em diante)
            
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'), # Fonte simples no corpo
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        table.setStyle(table_style)
        Story.append(table)

        doc.build(Story)
        buffer_pdf.seek(0)

        # --- Geração do Excel ---
        # Mantemos as colunas de dados reais para o Excel, com os títulos S1/S2
        df = pd.DataFrame([
            {
                'data': m['data'].strftime('%d/%m/%Y') if m['data'] else '',
                'hora': m.get('hora', ''),
                'codigo': m.get('cod_produto_embalagem') or m.get('codigo', ''),
                'descricao': m.get('nome_produto') or m.get('descricao', ''),
                'nf': m.get('nf', ''),
                'op': m.get('op', ''),
                'entrada': m.get('entrada', 0.0),
                'saida': m.get('saida', 0.0),
                'saldo': m.get('saldo', 0.0)
            }
            for m in movimentacoes
        ])

        df.rename(columns={'data': 'Data', 'hora': 'Hora', 'codigo': 'Código', 'descricao': 'Descrição',
                           'nf': 'S1 (NF)', 'op': 'S2 (OP)', 'entrada': 'Entrada', 'saida': 'Saída', 'saldo': 'Saldo'}, inplace=True)

        buffer_excel = BytesIO()
        writer = pd.ExcelWriter(buffer_excel, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Movimentacoes Kardex')
        writer.close()
        buffer_excel.seek(0)

        # --- Envio do e-mail ---
        data_envio = datetime.now().strftime('%d/%m/%Y %H:%M')
        # ... (código de envio de e-mail) ...
        msg = Message(
            f'Relatórios de Movimentações (Kardex) - {data_envio}',
            sender=current_app.config.get('MAIL_USERNAME'),
            recipients=[current_app.config.get('MAIL_RECIPIENT', 'clewertonsouza8@gmail.com')]
        )
        msg.body = f'Prezado, em anexo os relatórios de movimentações no formato Kardex (PDF e Excel).'
        filename_base = datetime.now().strftime('%Y%m%d_%H%M')
        msg.attach(f'Kardex_Movimentacoes_{filename_base}.pdf', 'application/pdf', buffer_pdf.getvalue())
        msg.attach(f'Kardex_Movimentacoes_{filename_base}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer_excel.getvalue())

        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            flash('Relatórios de Movimentações (Kardex: PDF e Excel) enviados por e-mail com sucesso! ✅', 'success')
        else:
            flash('Erro: Flask-Mail não está configurado. E-mail não enviado. ❌', 'danger')


    except Exception as e:
        current_app.logger.exception("Erro ao enviar relatórios de movimentações")
        flash(f"Erro ao enviar os relatórios de movimentações: {str(e)} ⚠️", 'danger')

    return redirect(request.referrer or url_for('main.movimentacao'))