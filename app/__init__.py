import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

from dotenv import load_dotenv 

#Cargar las variables de entorno
load_dotenv()

#crear instancia
app =  Flask(__name__)

# Configuración de la base de datos PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Necesaria para los mensajes flash (define SECRET_KEY en .env en producción)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-cambia-esta-clave')

db = SQLAlchemy(app)

# Registrar Blueprint del Home
from app.routes.home import home_bp
from app.routes.libros import libros_bp
from app.routes.lectores import lectores_bp
from app.routes.prestamos import prestamos_bp

app.register_blueprint(home_bp)
app.register_blueprint(libros_bp)
app.register_blueprint(lectores_bp)
app.register_blueprint(prestamos_bp)

with app.app_context():
    try:
      from app.models import libro, lector, prestamo  # noqa: F401
    except ImportError:
      pass

    db.create_all()