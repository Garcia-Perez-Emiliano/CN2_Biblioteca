from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.prestamo import Prestamo
from app.models.libro import Libro
from app.models.lector import Lector

prestamos_bp = Blueprint("prestamos", __name__, url_prefix="/prestamos")

POR_PAGINA = 10
DIAS_PRESTAMO_DEFAULT = 7


def _parsear_fecha(valor):
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def _validar(form):
    """Valida el formulario de nuevo préstamo. Devuelve (datos, errores)."""
    datos = {
        "libro_id": form.get("libro_id", "").strip(),
        "lector_id": form.get("lector_id", "").strip(),
        "fecha_prestamo": form.get("fecha_prestamo", "").strip(),
        "fecha_devolucion_esperada": form.get("fecha_devolucion_esperada", "").strip(),
        "observaciones": form.get("observaciones", "").strip(),
    }
    errores = []

    libro = None
    if not datos["libro_id"].isdigit():
        errores.append("Debes seleccionar un libro válido.")
    else:
        libro = db.session.get(Libro, int(datos["libro_id"]))
        if not libro:
            errores.append("El libro seleccionado no existe.")
        elif libro.ejemplares_disponibles <= 0:
            errores.append(f"No hay ejemplares disponibles de «{libro.titulo}».")

    lector = None
    if not datos["lector_id"].isdigit():
        errores.append("Debes seleccionar un lector válido.")
    else:
        lector = db.session.get(Lector, int(datos["lector_id"]))
        if not lector:
            errores.append("El lector seleccionado no existe.")
        elif hasattr(lector, "activo") and not lector.activo:
            errores.append(f"El lector {lector.nombre} {lector.apellidos} está inactivo.")

    f_prestamo = _parsear_fecha(datos["fecha_prestamo"])
    f_esperada = _parsear_fecha(datos["fecha_devolucion_esperada"])

    if not f_prestamo:
        errores.append("La fecha de préstamo es obligatoria y debe ser válida.")
    if not f_esperada:
        errores.append("La fecha de devolución esperada es obligatoria y debe ser válida.")
    if f_prestamo and f_esperada and f_esperada < f_prestamo:
        errores.append("La fecha de devolución esperada no puede ser anterior al préstamo.")

    datos_limpios = {
        **datos,
        "_libro": libro,
        "_lector": lector,
        "_f_prestamo": f_prestamo,
        "_f_esperada": f_esperada,
    }
    return datos_limpios, errores


@prestamos_bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "").strip().upper()
    pagina = request.args.get("page", 1, type=int)

    consulta = (
        db.select(Prestamo)
        .join(Prestamo.libro)
        .join(Prestamo.lector)
    )

    if estado in ("ACTIVO", "DEVUELTO"):
        consulta = consulta.where(Prestamo.estado == estado)
    elif estado == "VENCIDO":
        consulta = consulta.where(
            Prestamo.estado == "ACTIVO",
            Prestamo.fecha_devolucion_esperada < date.today(),
        )

    if q:
        patron = f"%{q}%"
        consulta = consulta.where(
            db.or_(
                Libro.titulo.ilike(patron),
                Libro.isbn.ilike(patron),
                Lector.nombre.ilike(patron),
                Lector.apellidos.ilike(patron),
                Lector.matricula.ilike(patron),
            )
        )

    paginacion = db.paginate(
        consulta.order_by(Prestamo.estado.asc(), Prestamo.fecha_devolucion_esperada.asc()),
        page=pagina,
        per_page=POR_PAGINA,
        error_out=False,
    )
    return render_template(
        "prestamos/index.html",
        paginacion=paginacion,
        q=q,
        estado=estado,
        hoy=date.today(),
    )


@prestamos_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    libros = db.session.scalars(
        db.select(Libro).where(Libro.ejemplares_disponibles > 0).order_by(Libro.titulo)
    ).all()
    lectores = db.session.scalars(
        db.select(Lector).where(Lector.activo == True).order_by(Lector.apellidos, Lector.nombre)
    ).all()

    if request.method == "POST":
        datos, errores = _validar(request.form)
        if not errores:
            libro = datos["_libro"]
            prestamo = Prestamo(
                libro_id=libro.id,
                lector_id=datos["_lector"].id,
                fecha_prestamo=datos["_f_prestamo"],
                fecha_devolucion_esperada=datos["_f_esperada"],
                estado="ACTIVO",
                observaciones=datos["observaciones"] or None,
            )
            # Descontar ejemplar disponible
            libro.ejemplares_disponibles -= 1

            db.session.add(prestamo)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Error de integridad al registrar el préstamo.", "danger")
            else:
                flash(f"Préstamo de «{libro.titulo}» registrado correctamente.", "success")
                return redirect(url_for("prestamos.index"))

        for e in errores:
            flash(e, "danger")
        return render_template(
            "prestamos/form.html", libros=libros, lectores=lectores, datos=datos
        )

    hoy = date.today()
    datos_iniciales = {
        "fecha_prestamo": hoy.isoformat(),
        "fecha_devolucion_esperada": (hoy + timedelta(days=DIAS_PRESTAMO_DEFAULT)).isoformat(),
    }
    return render_template(
        "prestamos/form.html", libros=libros, lectores=lectores, datos=datos_iniciales
    )


@prestamos_bp.route("/<int:prestamo_id>/devolver", methods=["POST"])
def devolver(prestamo_id):
    prestamo = db.get_or_404(Prestamo, prestamo_id)

    if prestamo.estado == "DEVUELTO":
        flash("Este préstamo ya fue marcado como devuelto anteriormente.", "warning")
        return redirect(url_for("prestamos.index"))

    prestamo.estado = "DEVUELTO"
    prestamo.fecha_devolucion_real = date.today()

    # Devolver el ejemplar al inventario disponible
    if prestamo.libro.ejemplares_disponibles < prestamo.libro.ejemplares_totales:
        prestamo.libro.ejemplares_disponibles += 1

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("No se pudo registrar la devolución por un error en la base de datos.", "danger")
    else:
        flash(f"Devolución de «{prestamo.libro.titulo}» registrada.", "success")

    return redirect(url_for("prestamos.index"))