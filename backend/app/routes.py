from flask import render_template, Blueprint, request, redirect, url_for, send_file, flash, current_app
from .models import EstoqueEmbalagem, SaidasEmbalagem, EntradasEmbalagens, db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from flask_mail import Message
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
import pandas as pd

# É recomendado inicializar Mail e o Blueprint fora das rotas
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Rota da página inicial."""
    return render_template('entrada.html')

@bp.route('/entrada')
def entrada():
    """Rota para a página de entrada."""
    # Sua lógica para a rota entrada
    return render_template("entrada.html", produtos=[])

@bp.route('/saida')
def saida():
    """Rota para a página de saída."""
    # Sua lógica para a rota saida
    return render_template("saida.html", produtos=[])

@bp.route('/estoque')
def estoque():
    """Rota para a página de estoque."""
    estoque_total_embalagens = EstoqueEmbalagem.query.with_entities(
        EstoqueEmbalagem.cod_produto_embalagem,
        EstoqueEmbalagem.nome_produto,
        EstoqueEmbalagem.total_embalagens_estoque,
    ).all()
    data_local = datetime.now()
    return render_template(
        'estoque.html',
        estoque_total_embalagens=estoque_total_embalagens,
        data_local=data_local
    )

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
    except IntegrityError:
        db.session.rollback()
        return "Erro: O número da nota fiscal já existe. Por favor, insira um número único.", 409
    except Exception as e:
        db.session.rollback()
        return f"Ocorreu um erro inesperado: {str(e)}", 500

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
        if not all([cod_produto, op, quantidade, responsavel, data_saida_str]):
            return "Erro: Todos os campos são obrigatórios.", 400
        data_saida = datetime.strptime(data_saida_str, '%Y-%m-%d')
        nova_saida = SaidasEmbalagem(
            cod_produto_embalagem=cod_produto,
            op=op,
            quantidade_saida=int(quantidade),
            responsavel_saida=responsavel,
            data_saida=data_saida
        )
        db.session.add(nova_saida)
        db.session.commit()
        return redirect(url_for('main.saida'))
    except Exception as e:
        db.session.rollback()
        return f"Ocorreu um erro: {str(e)}", 500

### Rotas de Envio (PDF e Excel)
# No seu arquivo routes.py

from flask import flash, redirect, url_for, current_app
from flask_mail import Message
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import pandas as pd
from io import BytesIO
from datetime import datetime
# ... (outros imports)

@bp.route('/enviar_estoque_tudo', methods=['POST'])
def enviar_estoque_tudo():
    try:
        # 1. Obter os dados do banco de dados
        estoque_total_embalagens = EstoqueEmbalagem.query.with_entities(
            EstoqueEmbalagem.cod_produto_embalagem,
            EstoqueEmbalagem.nome_produto,
            EstoqueEmbalagem.total_embalagens_estoque
        ).all()

        # 2. Gerar o arquivo PDF
        buffer_pdf = BytesIO()
        doc = SimpleDocTemplate(buffer_pdf, pagesize=letter)
        data_pdf = [['Código', 'Descrição', 'Estoque Atual']]
        for item in estoque_total_embalagens:
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
        df = pd.DataFrame(estoque_total_embalagens, columns=['Código', 'Descrição', 'Estoque Atual'])
        buffer_excel = BytesIO()
        writer = pd.ExcelWriter(buffer_excel, engine='openpyxl')
        df.to_excel(writer, index=False, sheet_name='Estoque Embalagens')
        writer.close()
        buffer_excel.seek(0)

        # 4. Configurar e-mail e anexar os dois arquivos
        msg = Message(
            'Relatórios de Estoque (PDF e Excel)',
            sender='cdss.snf25@duea.edu.br',
            recipients=['clewertonsouza8@gmail.com']
        )
        msg.body = 'Prezado, em anexo os relatórios de estoque nos formatos PDF e Excel.'
        msg.attach('Relatorio_Estoque.pdf', 'application/pdf', buffer_pdf.getvalue())
        msg.attach('Relatorio_Estoque.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer_excel.getvalue())
        
        current_app.extensions['mail'].send(msg)
        
        flash('Relatórios (PDF e Excel) enviados com sucesso!', 'success')
        return redirect(url_for('main.estoque'))
    
    except Exception as e:
        flash(f"Erro ao enviar os relatórios: {str(e)}", 'danger')
        return redirect(url_for('main.estoque'))