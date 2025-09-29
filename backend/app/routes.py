# Mantenha todas as suas importações originais
from flask import request, jsonify, Blueprint, render_template, redirect, url_for, flash, current_app, send_file
from datetime import datetime
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

bp = Blueprint("main", __name__)

# --- Constantes para Alerta de Estoque ---
# Vermelho Suave (Próximo ao Mínimo ou Mínimo)
RED_SOFT = colors.HexColor("#FFA07A") 
# Azul Suave (Estoque Normal/Médio)
BLUE_SOFT = colors.HexColor("#ADD8E6") 
# Verde Suave (Próximo ao Máximo ou Máximo)
GREEN_SOFT = colors.HexColor("#90EE90")
# Fator de proximidade: Faltando 50 para chegar ao estoque mínimo
FATOR_PROXIMIDADE = 50

# -------------------------------------------------------------------------------------
# --- FUNÇÃO AUXILIAR DE ALERTA (CORREÇÃO FINAL DA LÓGICA DE CORES) ---
# -------------------------------------------------------------------------------------
def get_cell_color(estoque_atual, estoque_min, estoque_max):
    """
    Determina a cor de alerta para a célula de estoque, ajustando o limite de 
    proximidade para evitar que o alerta vermelho engula o estoque normal/médio.
    """
    # Conversão segura
    atual = int(estoque_atual) if estoque_atual is not None else 0
    min_val = int(estoque_min) if estoque_min is not None else -1
    max_val = int(estoque_max) if estoque_max is not None else float('inf')

    # 1. CRITICAL RED (Abaixo ou no Mínimo)
    if min_val != -1 and atual <= min_val:
        return RED_SOFT
    
    # 2. EXCESS GREEN (Acima ou no Máximo)
    if max_val != float('inf') and atual >= max_val:
        return GREEN_SOFT

    # --- 3. PROXIMIDADE vs. NORMAL (Estoque agora é: Min < atual < Max ou Min < atual) ---
    if min_val != -1:
        # Inicializa o buffer de proximidade com o valor fixo
        proximity_buffer = FATOR_PROXIMIDADE

        if max_val != float('inf'):
            # Se a faixa (Max - Min) for menor que FATOR_PROXIMIDADE (o caso do I001630: 36-12=24 < 50),
            # usamos um buffer proporcional para manter a área AZUL.
            if (max_val - min_val) < FATOR_PROXIMIDADE:
                # Usa-se 30% da faixa como buffer de proximidade (ex: 24 * 0.3 = 7.2)
                proximity_buffer = (max_val - min_val) * 0.3
        
        proximity_limit = min_val + proximity_buffer

        # 3a. PROXIMIDADE RED (Entre Min e o limite ajustado)
        if atual <= proximity_limit:
            return RED_SOFT
        
    # 4. NORMAL BLUE (O restante: estoque seguro, acima do Mínimo e do limite de Proximidade)
    return BLUE_SOFT


# -------------------------------------------------------------------------------------
# --- FUNÇÃO AUXILIAR DE CÁLCULO DE ESTOQUE (CORRIGIDA COM SUBQUERIES) ---
# -------------------------------------------------------------------------------------
def obter_estoque_calculado():
    """
    Gera a consulta de estoque atual usando subconsultas para evitar
    o erro de cálculo de estoque (Entradas - Saídas).
    """
    
    # 1. Subconsulta para somar APENAS Entradas
    sub_entradas = db.session.query(
        EntradasEmbalagens.cod_produto_embalagem,
        db.func.sum(EntradasEmbalagens.quantidade_recebida).label('total_entrada')
    ).group_by(
        EntradasEmbalagens.cod_produto_embalagem
    ).subquery('entradas')

    # 2. Subconsulta para somar APENAS Saídas
    sub_saidas = db.session.query(
        SaidasEmbalagem.cod_produto_embalagem,
        db.func.sum(SaidasEmbalagem.quantidade_saida).label('total_saida')
    ).group_by(
        SaidasEmbalagem.cod_produto_embalagem
    ).subquery('saidas')

    # 3. Query Principal: Junção da Tabela Estoque com as somas calculadas
    estoque_total_query = db.session.query(
        EstoqueEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        # Estoque Atual = Total Entradas (coalesce para 0) - Total Saídas (coalesce para 0)
        (db.func.coalesce(sub_entradas.c.total_entrada, 0) -
         db.func.coalesce(sub_saidas.c.total_saida, 0)).label('estoque_atual'),
        EstoqueEmbalagem.estoque_min,
        EstoqueEmbalagem.estoque_max
    ).outerjoin(
        sub_entradas,
        EstoqueEmbalagem.cod_produto_embalagem == sub_entradas.c.cod_produto_embalagem
    ).outerjoin(
        sub_saidas,
        EstoqueEmbalagem.cod_produto_embalagem == sub_saidas.c.cod_produto_embalagem
    ).order_by(
        EstoqueEmbalagem.cod_produto_embalagem
    ).all()
    
    return estoque_total_query

# --- Rotas Principais ---
@bp.route("/")
def index():
    """Redireciona para a página de entrada."""
    return redirect(url_for("main.entrada"))

@bp.route("/entrada")
def entrada():
    """Rota para a página de entrada de embalagens."""
    produtos_objetos = EstoqueEmbalagem.query.all()
    produtos_para_template = [
        {
            "cod_produto_embalagem": p.cod_produto_embalagem,
            "nome_produto": p.nome_produto,
            "padrao_embalagem": p.padrao_embalagem,
            "unidade_medida": p.unidade_medida
        }
        for p in produtos_objetos
    ]
    return render_template("entrada.html", produtos_para_template=produtos_para_template)

@bp.route("/saida")
def saida():
    """Rota para a página de saída de embalagens."""
    produtos_objetos = EstoqueEmbalagem.query.all()
    produtos_para_template = [
        {
            "cod_produto_embalagem": p.cod_produto_embalagem,
            "nome_produto": p.nome_produto,
            "padrao_embalagem": p.padrao_embalagem,
            "unidade_medida": p.unidade_medida
        }
        for p in produtos_objetos
    ]
    return render_template("saida.html", produtos_para_template=produtos_para_template)

@bp.route("/estoque")
def estoque():
    """Rota para a página de visualização do estoque."""
    
    # Busca o estoque usando a função CORRIGIDA
    estoque_total_com_min_max = obter_estoque_calculado()
    
    # Formata para o template antigo (cod, nome, estoque_atual)
    estoque_total_embalagens = [(item[0], item[1], item[2]) for item in estoque_total_com_min_max]
    
    data_local = datetime.now()
    return render_template(
        "estoque.html",
        estoque_total_embalagens=estoque_total_embalagens,
        data_local=data_local
    )

# --- Rotas de Processamento de Formulário (Inalteradas) ---
@bp.route("/entrada_embalagem", methods=["POST"])
def entrada_embalagem():
    """Processa a entrada de embalagens e salva no banco de dados."""
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        nf = request.form.get("nf")
        quantidade_recebida = int(request.form.get("quantidade_recebida") or 0)
        responsavel = request.form.get("responsavel_recebimento")
        data_recebimento_str = request.form.get("data_recebimento")
        total = float(request.form.get("total") or 0.0)

        data_recebimento = datetime.strptime(data_recebimento_str, '%Y-%m-%d') if data_recebimento_str else datetime.now()
        
        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "error")
            return redirect(url_for("main.entrada"))

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
        db.session.rollback()
        flash(f"Erro ao processar o formulário: {e}", "error")
    except IntegrityError:
        db.session.rollback()
        flash(f"NF já existente: {nf}", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro inesperado: {str(e)}", "error")
        
    return redirect(url_for("main.entrada"))

@bp.route("/saida_embalagem", methods=["POST"])
def saida_embalagem():
    """Processa a saída de embalagens e salva no banco de dados."""
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        op = request.form.get("op")
        quantidade_saida = int(request.form.get("quantidade_saida") or 0)
        responsavel = request.form.get("responsavel_saida")
        data_saida_str = request.form.get("data_saida")

        data_saida = datetime.strptime(data_saida_str, '%Y-%m-%d') if data_saida_str else datetime.now()

        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "error")
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

    except (ValueError, TypeError) as e:
        db.session.rollback()
        flash(f"Erro ao processar o formulário: {e}", "error")
    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro inesperado: {str(e)}", "error")

    return redirect(url_for("main.saida"))

# --- Rotas de Envio de Relatórios (USA FUNÇÃO CORRIGIDA) ---
@bp.route('/enviar_estoque_tudo', methods=['POST'])
def enviar_estoque_tudo():
    """Gera e envia relatórios de estoque em PDF e Excel por e-mail, estilizados com alertas."""

    try:
        # 1. Obter os dados do banco de dados (USANDO A FUNÇÃO CORRIGIDA)
        estoque_total = obter_estoque_calculado()
        
        # 2. Gerar o arquivo PDF Personalizado
        buffer_pdf = BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=letter)
        Story = [] # Lista de elementos para o PDF
        styles = getSampleStyleSheet()
        
        # --- Configuração do Logo e Título ---
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
        
        # --- Dados da Tabela ---
        data_pdf = [['Código', 'Descrição', 'Estoque Atual', 'Estoque Min', 'Estoque Max']]
        
        cell_styles = [] 
        
        # Percorre os dados e aplica a lógica de cores
        for i, item in enumerate(estoque_total):
            cod, desc, atual, min_val, max_val = item
            
            # 1. Determina a cor com base no estoque_atual, estoque_min e estoque_max
            cor = get_cell_color(atual, min_val, max_val)
            
            # 2. Adiciona o estilo de cor para a célula do Estoque Atual (coluna 2, linha i+1, pois a linha 0 é o cabeçalho)
            cell_styles.append(('BACKGROUND', (2, i + 1), (2, i + 1), cor))

            # 3. Adiciona a linha de dados (Convertendo tudo para string, incluindo min/max para exibir)
            data_pdf.append([
                str(cod), 
                str(desc), 
                str(atual), 
                str(min_val if min_val is not None else 'N/A'),
                str(max_val if max_val is not None else 'N/A')
            ])

        table = Table(data_pdf)
        
        # --- Estilização da Tabela (APLICAÇÃO DOS ESTILOS DE COR) ---
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#010162")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        
        # 1. Aplicar Fundo Alternado em TODAS as colunas (para toda a linha)
        for i in range(1, len(data_pdf)):
             table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor("#EEEEEE") if i % 2 == 0 else colors.white)
        
        # 2. Aplicar Alertas de Cor SOMENTE na Coluna 'Estoque Atual' (sobrescrevendo o fundo alternado)
        for style in cell_styles:
             table_style.add(*style)
        
        table.setStyle(table_style)
        Story.append(table)
        
        # --- Adiciona a Legenda de Cores ---
        Story.append(Spacer(1, 24))
        
        legenda_titulo = Paragraph("<b>Guia de Alerta de Estoque:</b>", styles['h3'])
        Story.append(legenda_titulo)
        Story.append(Spacer(1, 6))

        # Dados da Tabela de Legenda
        legenda_data = [
            [
                Table([[' ']], colWidths=[20], style=TableStyle([('BACKGROUND', (0,0), (0,0), BLUE_SOFT), ('GRID', (0,0), (0,0), 0.5, colors.black)])),
                Paragraph("Estoque Normal (Azul): Estoque OK (Acima da Zona de Alerta e Abaixo de Máximo).", styles['Normal'])
            ],
            [
                Table([[' ']], colWidths=[20], style=TableStyle([('BACKGROUND', (0,0), (0,0), RED_SOFT), ('GRID', (0,0), (0,0), 0.5, colors.black)])),
                Paragraph(f"Alerta Mínimo (Vermelho): Estoque no Mínimo ou Abaixo, OU na Zona de Proximidade (até {FATOR_PROXIMIDADE} acima do Mínimo, ajustado pelo Máximo).", styles['Normal'])
            ],
            [
                Table([[' ']], colWidths=[20], style=TableStyle([('BACKGROUND', (0,0), (0,0), GREEN_SOFT), ('GRID', (0,0), (0,0), 0.5, colors.black)])),
                Paragraph("Alerta Máximo (Verde): Estoque no Máximo ou Acima.", styles['Normal'])
            ]
        ]
        
        # Cria a tabela de legenda
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

        # 3. Gerar o arquivo Excel
        df = pd.DataFrame(
            estoque_total, 
            columns=['Código', 'Descrição', 'Estoque Atual', 'Estoque Mínimo', 'Estoque Máximo']
        )
        buffer_excel = BytesIO()
        writer = pd.ExcelWriter(buffer_excel, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Estoque Embalagens')
        writer.close()
        buffer_excel.seek(0)

        # 4. Configurar e-mail e anexar os dois arquivos
        msg = Message(
            'Relatórios de Estoque (PDF e Excel) {data_realtório}'.format(data_realtório=datetime.now().strftime('%d/%m/%Y')),
            sender=current_app.config['MAIL_USERNAME'],
            recipients=['clewertonsouza8@gmail.com'] 
        )
        msg.body = 'Prezado, em anexo os relatórios de estoque nos formatos PDF e Excel. O PDF contém alertas de cor para estoque mínimo e máximo.'
        msg.attach('Relatorio_Estoque.pdf', 'application/pdf', buffer_pdf.getvalue())
        msg.attach('Relatorio_Estoque.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer_excel.getvalue())
        
        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            flash('Relatórios (PDF e Excel) enviados com sucesso!', 'success')
        else:
            flash('Erro: Flask-Mail não está configurado. Verifique o arquivo de configuração.', 'danger')
        
    except FileNotFoundError:
        flash("Erro: O arquivo do logo não foi encontrado no caminho especificado.", 'danger')
    except Exception as e:
        flash(f"Erro ao enviar os relatórios: {str(e)}", 'danger')
        
    return redirect(url_for('main.estoque'))