from datetime import datetime
from app import db


class Lector(db.Model):
    __tablename__ = "lectores"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(
        db.String(100),
        nullable=False,
        index=True
    )

    apellidos = db.Column(
        db.String(100),
        nullable=False,
        index=True
    )

    correo = db.Column(
        db.String(120),
        nullable=False,
        unique=True,
        index=True
    )

    telefono = db.Column(
        db.String(20)
    )

    matricula = db.Column(
        db.String(30),
        nullable=False,
        unique=True,
        index=True
    )

    activo = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    fecha_registro = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    def __repr__(self):
        return f"<Lector {self.nombre} {self.apellidos}>"