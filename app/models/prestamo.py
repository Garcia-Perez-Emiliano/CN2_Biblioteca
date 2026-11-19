from datetime import date
from app import db


class Prestamo(db.Model):
    __tablename__ = "prestamos"

    id = db.Column(db.Integer, primary_key=True)

    libro_id = db.Column(
        db.Integer,
        db.ForeignKey("libros.id"),
        nullable=False,
        index=True
    )

    lector_id = db.Column(
        db.Integer,
        db.ForeignKey("lectores.id"),
        nullable=False,
        index=True
    )

    fecha_prestamo = db.Column(
        db.Date,
        nullable=False,
        default=date.today
    )

    fecha_devolucion_esperada = db.Column(
        db.Date,
        nullable=False
    )

    fecha_devolucion_real = db.Column(db.Date)

    estado = db.Column(
        db.String(10),
        nullable=False,
        default="vigente",
        index=True
    )

    observaciones = db.Column(db.Text)

    # Relaciones
    libro = db.relationship(
        "Libro",
        backref=db.backref("prestamos", lazy=True)
    )

    lector = db.relationship(
        "Lector",
        backref=db.backref("prestamos", lazy=True)
    )

    # Restricciones
    __table_args__ = (
        db.CheckConstraint(
            "estado IN ('vigente', 'devuelto', 'vencido')",
            name="ck_prestamos_estado",
        ),
        db.CheckConstraint(
            """
            fecha_devolucion_esperada >= fecha_prestamo
            AND (
                fecha_devolucion_real IS NULL
                OR fecha_devolucion_real >= fecha_prestamo
            )
            """,
            name="ck_prestamos_fechas",
        ),
    )

    @property
    def esta_vencido(self):
        return (
            self.estado == "vigente"
            and self.fecha_devolucion_esperada < date.today()
        )

    def __repr__(self):
        return (
            f"<Prestamo #{self.id} - "
            f"Libro {self.libro_id} -> Lector {self.lector_id}>"
        )