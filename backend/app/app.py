# app.py (Este arquivo deve estar na raiz do seu projeto)

from estoque import create_app

# Cria a instância do aplicativo chamando a função de fábrica
app = create_app()

# Opcional: Adicionar um usuário administrador para testes
from estoque.models import db, Usuario
from werkzeug.security import generate_password_hash

# Contexto da aplicação para operações de DB fora das rotas
with app.app_context():
    db.create_all() # Garante que as tabelas (incluindo 'usuario') existam

    # Cria um usuário padrão se ele não existir
    if Usuario.query.filter_by(username='admin').first() is None:
        # Gerar hash para a senha 'senha123'
        admin_user = Usuario(
            username='admin', 
            password_hash=generate_password_hash('senha123', method='pbkdf2:sha256'),
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Usuário 'admin' criado com senha 'senha123'")

if __name__ == '__main__':
    # Define FLASK_APP=app.py e FLASK_ENV=development 
    app.run(debug=True)