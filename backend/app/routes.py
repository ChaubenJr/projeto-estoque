# Mantenha todas as suas importações originais
from flask import request, jsonify, Blueprint, render_template, redirect, url_for, flash, current_app
from datetime import date, datetime # Adicionado 'date' para a busca diária
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
    ).order_by(EstoqueEmbalagem.cod_produto_embalagem).all() # Adicionado order_by para consistência
    
    data_local = datetime.now()
    return render_template(
        "estoque.html",
        estoque_total_embalagens=estoque_total,
        data_local=data_local
    )
    
# ===================================================================
# NOVO CÓDIGO - Rotas para os Registros Diários
# ===================================================================

@bp.route('/registro/entradas/diario')
def registro_diario_entradas():
    """Busca e exibe os registros de ENTRADA da data atual."""
    hoje = date.today()
    
    # Usando SQLAlchemy para buscar as entradas de hoje
    # A query junta (join) EntradasEmbalagens com EstoqueEmbalagem para pegar o nome do produto
    registros_de_hoje = db.session.query(
        EntradasEmbalagens.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        EntradasEmbalagens.nf,
        EntradasEmbalagens.pedido_compra, # Supondo que você adicionou este campo ao model
        EntradasEmbalagens.quantidade_recebida,
        EntradasEmbalagens.responsavel_recebimento,
        EntradasEmbalagens.total
    ).join(
        EstoqueEmbalagem, EntradasEmbalagens.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem
    ).filter(
        db.func.date(EntradasEmbalagens.data_recebimento) == hoje
    ).order_by(EntradasEmbalagens.id.desc()).all()

    return render_template('registro-diario.html', 
                           registros=registros_de_hoje, 
                           data_atual=hoje.strftime('%d/%m/%Y'))

@bp.route('/registro/saidas/diario')
def registro_diario_saidas():
    """Busca e exibe os registros de SAÍDA da data atual."""
    hoje = date.today()
    
    # Usando SQLAlchemy para buscar as saídas de hoje
    registros_de_hoje = db.session.query(
        SaidasEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        SaidasEmbalagem.op,
        SaidasEmbalagem.quantidade_saida,
        SaidasEmbalagem.responsavel_saida
    ).join(
        EstoqueEmbalagem, SaidasEmbalagem.cod_produto_embalagem == EstoqueEmbalagem.cod_produto_embalagem
    ).filter(
        db.func.date(SaidasEmbalagem.data_saida) == hoje
    ).order_by(SaidasEmbalagem.id.desc()).all()

    return render_template('registro-diario-saida.html', 
                           registros=registros_de_hoje, 
                           data_atual=hoje.strftime('%d/%m/%Y'))

# --- Rotas de Processamento de Formulário ---
@bp.route("/entrada_embalagem", methods=["POST"])
def entrada_embalagem():
    """Processa a entrada de embalagens e salva no banco de dados."""
    try:
        cod_produto = request.form.get("cod_produto_embalagem")
        nf = request.form.get("nf")
        pedido_compra = request.form.get("pedido_compra") # Captura o novo campo
        quantidade_recebida = int(request.form.get("quantidade_recebida") or 0)
        responsavel = request.form.get("responsavel_recebimento")
        data_recebimento_str = request.form.get("data_recebimento")
        total = float(request.form.get("valor_total") or 0.0) # Corrigido para 'valor_total'

        data_recebimento = datetime.strptime(data_recebimento_str, '%Y-%m-%d').date() if data_recebimento_str else date.today()
        
        produto = EstoqueEmbalagem.query.get(cod_produto)
        if not produto:
            flash("Erro: Código de produto não encontrado.", "danger")
            return redirect(url_for("main.entrada"))

        nova_entrada = EntradasEmbalagens(
            cod_produto_embalagem=cod_produto,
            nf=nf,
            pedido_compra=pedido_compra, # Salva o novo campo
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
        flash(f"Erro ao processar o formulário: {e}", "danger")
    except IntegrityError:
        db.session.rollback()
        flash(f"NF já existente: {nf}", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro inesperado: {str(e)}", "danger")
        
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

    except (ValueError, TypeError) as e:
        db.session.rollback()
        flash(f"Erro ao processar o formulário: {e}", "danger")
    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro inesperado: {str(e)}", "danger")

    return redirect(url_for("main.saida"))


# --- Rotas de Envio de Relatórios ---
@bp.route('/enviar_estoque_tudo', methods=['POST'])
def enviar_estoque_tudo():
    """Gera e envia relatórios de estoque em PDF e Excel por e-mail."""
    # (Seu código de envio de relatório permanece inalterado)
    try:
        estoque_total_query = db.session.query(
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
        )
        estoque_total = estoque_total_query.all()

        buffer_pdf = BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=letter)
        Story = []
        styles = getSampleStyleSheet()
        
        logo_path = os.path.join(current_app.root_path, 'static', 'img', 'Logo ITP.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=150, height=75) 
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
        
        data_pdf = [['Código', 'Descrição', 'Estoque Atual']]
        for item in estoque_total:
            data_pdf.append([str(item[0]), str(item[1]), str(item[2])])

        table = Table(data_pdf)
        
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#009764')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(table_style)
        Story.append(table)

        doc.build(Story)
        buffer_pdf.seek(0)

        df = pd.DataFrame(estoque_total, columns=['Código', 'Descrição', 'Estoque Atual'])
        buffer_excel = BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Estoque Embalagens')
        buffer_excel.seek(0)

        msg = Message(
            'Relatórios de Estoque (PDF e Excel)',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=['clewertonsouza8@gmail.com'] 
        )
        msg.body = 'Prezado, em anexo os relatórios de estoque nos formatos PDF e Excel.'
        msg.attach('Relatorio_Estoque.pdf', 'application/pdf', buffer_pdf.getvalue())
        msg.attach('Relatorio_Estoque.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer_excel.getvalue())
        
        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            flash('Relatórios (PDF e Excel) enviados com sucesso!', 'success')
        else:
            flash('Erro: Flask-Mail não está configurado.', 'danger')
        
    except FileNotFoundError:
        flash("Erro: O arquivo do logo não foi encontrado no caminho especificado.", 'danger')
    except Exception as e:
        flash(f"Erro ao enviar os relatórios: {str(e)}", 'danger')
    
    return redirect(url_for('main.estoque'))