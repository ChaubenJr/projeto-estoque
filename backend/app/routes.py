# Mantenha todas as suas importações originais
from flask import request, jsonify, Blueprint, render_template, redirect, url_for, flash, current_app, send_file
from datetime import datetime
from .models import db, EstoqueEmbalagem, EntradasEmbalagens, SaidasEmbalagem
from sqlalchemy.exc import IntegrityError
from flask_mail import Message
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
import pandas as pd

bp = Blueprint("main", __name__)

# --- Rotas Principais ---
@bp.route("/")
def index():
    """Redireciona para a página de entrada."""
    return redirect(url_for("main.entrada"))

@bp.route("/entrada")
def entrada():
    """Rota para a página de entrada de embalagens."""
    # 1. Busca os produtos do banco de dados (como objetos)
    produtos_objetos = EstoqueEmbalagem.query.all()
    
    # 2. Converte a lista de objetos em uma lista de dicionários
    #    Isso cria uma estrutura de dados limpa para o JavaScript
    produtos_para_template = [
        {
            "cod_produto_embalagem": p.cod_produto_embalagem,
            "nome_produto": p.nome_produto,
            "padrao_embalagem": p.padrao_embalagem,
            "unidade_medida": p.unidade_medida
        }
        for p in produtos_objetos
    ]
    
    # 3. Passa a lista de dicionários para o template
    return render_template("entrada.html", produtos_para_template=produtos_para_template)

@bp.route("/saida")
def saida():
    """Rota para a página de saída de embalagens."""
    # 1. Busca os produtos do banco de dados (como objetos)
    produtos_objetos = EstoqueEmbalagem.query.all()
    
    # 2. Converte a lista de objetos em uma lista de dicionários (mesma lógica da entrada)
    produtos_para_template = [
        {
            "cod_produto_embalagem": p.cod_produto_embalagem,
            "nome_produto": p.nome_produto,
            "padrao_embalagem": p.padrao_embalagem,
            "unidade_medida": p.unidade_medida
        }
        for p in produtos_objetos
    ]

    # 3. Passa a lista de dicionários para o template
    return render_template("saida.html", produtos_para_template=produtos_para_template)

@bp.route("/estoque")
def estoque():
    """Rota para a página de visualização do estoque."""
    # Sua lógica de consulta permanece a mesma
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
    
    data_local = datetime.now()
    return render_template(
        "estoque.html",
        estoque_total_embalagens=estoque_total,
        data_local=data_local
    )

# --- Rotas de Processamento de Formulário ---
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
        # Mensagem formatada para o JavaScript (NF já existente: {numero})
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

# --- Rotas de Envio de Relatórios ---
@bp.route('/enviar_estoque_tudo', methods=['POST'])
def enviar_estoque_tudo():
    """Gera e envia relatórios de estoque em PDF e Excel por e-mail."""
    try:
        # 1. Obter os dados do banco de dados
        # Usando a mesma consulta complexa do primeiro código para consistência
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

        # 2. Gerar o arquivo PDF
        buffer_pdf = BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=letter)
        data_pdf = [['Código', 'Descrição', 'Estoque Atual']]
        for item in estoque_total:
            data_pdf.append(list(item))
        table = Table(data_pdf)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(table_style)
        doc.build([table])
        buffer_pdf.seek(0)

        # 3. Gerar o arquivo Excel
        df = pd.DataFrame(estoque_total, columns=['Código', 'Descrição', 'Estoque Atual'])
        buffer_excel = BytesIO()
        writer = pd.ExcelWriter(buffer_excel, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Estoque Embalagens')
        writer.close()
        buffer_excel.seek(0)

        # 4. Configurar e-mail e anexar os dois arquivos
        msg = Message(
            'Relatórios de Estoque (PDF e Excel)',
            sender=current_app.config['MAIL_USERNAME'],
            recipients=['clewertonsouza8@gmail.com'] # Use uma lista de destinatários aqui
        )
        msg.body = 'Prezado, em anexo os relatórios de estoque nos formatos PDF e Excel.'
        msg.attach('Relatorio_Estoque.pdf', 'application/pdf', buffer_pdf.getvalue())
        msg.attach('Relatorio_Estoque.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer_excel.getvalue())
        
        # Envia a mensagem
        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            flash('Relatórios (PDF e Excel) enviados com sucesso!', 'success')
        else:
            flash('Erro: Flask-Mail não está configurado. Verifique o arquivo de configuração.', 'danger')
        
    except Exception as e:
        flash(f"Erro ao enviar os relatórios: {str(e)}", 'danger')
    
    return redirect(url_for('main.estoque'))