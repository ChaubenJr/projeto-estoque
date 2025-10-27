import sys
import os
from werkzeug.security import generate_password_hash

# --- INÍCIO DA CORREÇÃO PARA RESOLVER ModuleNotFoundError ---
# Esta lógica ajusta o sys.path para incluir o diretório que contém a pasta 'app'.
# Isso é necessário se 'run.py' estiver em um subdiretório (como 'backend/run.py').
try:
    # Calcula o caminho absoluto para o diretório raiz do projeto (o pai da subpasta 'backend')
    project_root = os.path.abspath(os.path.dirname(__file__))
    
    if project_root not in sys.path:
        sys.path.append(project_root)

    # Tenta importar o pacote principal 'app' após ajustar o sys.path
    from app import create_app
    from app.models import db, Usuario
    
except ImportError as e:
    # Se a importação falhar mesmo após o ajuste, exibe um erro útil
    print("-------------------------------------------------------------------------")
    print(f"ERRO CRÍTICO DE IMPORTAÇÃO: {e}")
    # CORREÇÃO AQUI: Referenciando o nome correto do pacote: 'app'
    print("Verifique se o seu diretório de aplicação principal está nomeado 'app' e contém o arquivo '__init__.py'.")
    print("-------------------------------------------------------------------------")
    sys.exit(1)
# --- FIM DA CORREÇÃO PARA RESOLVER ModuleNotFoundError ---


# Cria a instância do aplicativo chamando a função de fábrica
app = create_app()

# O bloco a seguir garante que o DB e um usuário 'admin' existam
with app.app_context():
    # Garante que todas as tabelas (incluindo 'usuario' para login) existam
    db.create_all() 

    # Cria um usuário administrador padrão se ele não existir
    if Usuario.query.filter_by(username='admin').first() is None:
        # A senha 'senha123' é hasheada antes de ser salva (essencial para segurança)
        admin_user = Usuario(
            username='admin', 
            password_hash=generate_password_hash('senha123', method='pbkdf2:sha256'),
            ativo=True  # CORREÇÃO: Usar o nome da coluna do DB ('ativo') em vez da propriedade ('is_active')
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Usuário 'admin' criado com senha 'senha123'. Faça login para testar o Flask-Login.")

if __name__ == '__main__':
    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=True)
