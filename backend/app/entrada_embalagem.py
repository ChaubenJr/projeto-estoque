from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="estoque"
    )

@app.route('/entrada_embalagem', methods=['POST'])
def entrada_embalagem():
    data = request.form
    cod_produto_embalagem = int(data['cod_produto_embalagem'])
    nf = data['nf']
    unidade_medida = data['unidade_medida']
    quantidade_recebida = int(data['quantidade_recebida'])
    responsavel_recebimento = data['responsavel_recebimento']
    data_recebimento = data['data_recebimento']
    total = float(data['total'])

    conexao = get_db_connection()
    cursor = conexao.cursor()

    # Inserindo na tabela entrada_embalagem
    sql_entrada = """
    INSERT INTO entrada_embalagem (
        cod_produto_embalagem, nf, unidade_medida, quantidade_recebida,
        responsavel_recebimento, data_recebimento, total
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    valores_entrada = (
        cod_produto_embalagem, nf, unidade_medida, quantidade_recebida,
        responsavel_recebimento, data_recebimento, total
    )
    cursor.execute(sql_entrada, valores_entrada)

    # Atualizando quantidade_total em produtos_embalagem
    sql_update = """
    UPDATE produtos_embalagem
    SET quantidade_total = quantidade_total + %s
    WHERE cod_produto = %s
    """
    cursor.execute(sql_update, (quantidade_recebida, cod_produto_embalagem))

    conexao.commit()
    cursor.close()
    conexao.close()

    return jsonify({"mensagem": "Entrada registrada e estoque atualizado!"})

if __name__ == '__main__':
    app.run(debug=True)