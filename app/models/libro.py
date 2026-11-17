from datetime import datetime
from app import db


class Libro(db.Model):
    __tablename__ = "libros"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False, index=True)
    autor = db.Column(db.String(150), nullable=False, index=True)
    isbn = db.Column(db.String(20), nullable=False, unique=True)
    editorial = db.Column(db.String(100))
    anio_publicacion = db.Column(db.SmallInteger)
    categoria = db.Column(db.String(80))
    ejemplares_totales = db.Column(db.Integer, nullable=False, default=1)
    ejemplares_disponibles = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("ejemplares_totales >= 0", name="ck_libros_totales"),
        db.CheckConstraint(
            "ejemplares_disponibles >= 0 AND ejemplares_disponibles <= ejemplares_totales",
            name="ck_libros_disponibles",
        ),
    )

    def __repr__(self):
        return f"<Libro {self.titulo}>"