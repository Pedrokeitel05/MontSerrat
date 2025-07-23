from gevent import monkey
monkey.patch_all()

from psycogreen.gevent import patch_psycopg
patch_psycopg()

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from config import setup_cloudinary
# Configura o sistema de logging
logging.basicConfig(level=logging.DEBUG)


# Classe base para os modelos do SQLAlchemy
class Base(DeclarativeBase):
    pass


# Inicializa a extensão SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Cria a aplicação Flask
app = Flask(__name__)

# Configura o Cloudinary logo no início, após a criação da app
setup_cloudinary()

# Configura a chave secreta para a sessão
app.secret_key = os.environ.get("SESSION_SECRET",
                                "dev-secret-key-change-in-production")

# Corrige os cabeçalhos de proxy (importante para o Replit)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configura a base de dados
# Lê a variável de ambiente 'DATABASE_URL' (dos Secrets)
# Se não encontrar, usa o ficheiro local 'sqlite:///montserrat.db' como alternativa
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///montserrat.db")

# Opções para otimizar a performance da conexão com a base de dados
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Associa a extensão SQLAlchemy à aplicação Flask
db.init_app(app)

# Importa os modelos e as rotas para que a aplicação os "conheça"
import models
import routes


# Comando personalizado para criar as tabelas na base de dados
@app.cli.command("create-tables")
def create_tables_command():
    """Cria as tabelas da base de dados."""
    # O contexto da aplicação é necessário para que o comando funcione
    with app.app_context():
        db.create_all()
    print("Tabelas criadas com sucesso na base de dados conectada!")


# ... (no final do ficheiro, depois de 'import routes')

from datetime import timedelta


# --- FILTRO DE TEMPLATE PARA FUSO HORÁRIO ---
@app.template_filter('localtime')
def localtime_filter(utc_dt):
    """Converte uma data UTC para o fuso horário local (UTC-3)."""
    if utc_dt is None:
        return ""
    # Ajusta para o fuso de Brasília (UTC-3)
    local_dt = utc_dt - timedelta(hours=3)
    return local_dt.strftime('%d/%m/%Y %H:%M')
