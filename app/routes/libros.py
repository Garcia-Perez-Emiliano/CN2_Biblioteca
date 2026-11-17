import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.libro import Libro

libros_bp = Blueprint("libros", __name__, url_prefix="/libros")

POR_PAGINA = 10
ANIO_MIN, ANIO_MAX = 1000, 2100


def _normalizar_isbn(valor):
    """Quita guiones y espacios: '978-0-262-04630-5' -> '9780262046305'."""
    return re.sub(r"[\s-]", "", valor).upper()


def _validar(form, libro=None):
    """Valida el formulario. Devuelve (datos, errores)."""
    datos = {
        "titulo": form.get("titulo", "").strip(),
        "autor": form.get("autor", "").strip(),
        "isbn": _normalizar_isbn(form.get("isbn", "")),
        "editorial": form.get("editorial", "").strip(),
        "categoria": form.get("categoria", "").strip(),
        "anio_publicacion": form.get("anio_publicacion", "").strip(),
        "ejemplares_totales": form.get("ejemplares_totales", "").strip(),
    }
    errores = []

    if not datos["titulo"]:
        errores.append("El título es obligatorio.")
    elif len(datos["titulo"]) > 200:
        errores.append("El título no puede pasar de 200 caracteres.")

    if not datos["autor"]:
        errores.append("El autor es obligatorio.")
    elif len(datos["autor"]) > 150:
        errores.append("El autor no puede pasar de 150 caracteres.")

    isbn = datos["isbn"]
    if not isbn:
        errores.append("El ISBN es obligatorio.")
    elif not re.fullmatch(r"\d{9}[\dX]|\d{13}", isbn):
        errores.append("El ISBN debe tener 10 o 13 dígitos (se permiten guiones).")
    else:
        existente = Libro.query.filter_by(isbn=isbn).first()
        if existente and (libro is None or existente.id != libro.id):
            errores.append(f"Ya existe un libro con el ISBN {isbn}: «{existente.titulo}».")

    if len(datos["editorial"]) > 100:
        errores.append("La editorial no puede pasar de 100 caracteres.")
    if len(datos["categoria"]) > 80:
        errores.append("La categoría no puede pasar de 80 caracteres.")

    if datos["anio_publicacion"]:
        if not datos["anio_publicacion"].isdigit() or not (
            ANIO_MIN <= int(datos["anio_publicacion"]) <= ANIO_MAX
        ):
            errores.append(f"El año debe estar entre {ANIO_MIN} y {ANIO_MAX}.")

    if not datos["ejemplares_totales"].isdigit():
        errores.append("Los ejemplares totales deben ser un número entero (0 o más).")
    elif libro is not None:
        prestados = libro.ejemplares_totales - libro.ejemplares_disponibles
        if int(datos["ejemplares_totales"]) < prestados:
            errores.append(
                f"Hay {prestados} ejemplar(es) prestado(s); el total no puede ser menor."
            )

    return datos, errores


def _aplicar(libro, datos):
    libro.titulo = datos["titulo"]
    libro.autor = datos["autor"]
    libro.isbn = datos["isbn"]
    libro.editorial = datos["editorial"] or None
    libro.categoria = datos["categoria"] or None
    libro.anio_publicacion = int(datos["anio_publicacion"]) if datos["anio_publicacion"] else None

    nuevo_total = int(datos["ejemplares_totales"])
    if libro.id is None:
        libro.ejemplares_totales = nuevo_total
        libro.ejemplares_disponibles = nuevo_total
    else:
        # Conserva los ejemplares que están prestados
        diferencia = nuevo_total - libro.ejemplares_totales
        libro.ejemplares_totales = nuevo_total
        libro.ejemplares_disponibles += diferencia


@libros_bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    pagina = request.args.get("page", 1, type=int)

    consulta = db.select(Libro)
    if q:
        patron = f"%{q}%"
        consulta = consulta.where(
            db.or_(
                Libro.titulo.ilike(patron),
                Libro.autor.ilike(patron),
                Libro.isbn.ilike(patron),
                Libro.categoria.ilike(patron),
            )
        )

    paginacion = db.paginate(
        consulta.order_by(Libro.titulo), page=pagina, per_page=POR_PAGINA, error_out=False
    )
    return render_template("libros/index.html", paginacion=paginacion, q=q)


@libros_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    if request.method == "POST":
        datos, errores = _validar(request.form)
        if not errores:
            libro = Libro()
            _aplicar(libro, datos)
            db.session.add(libro)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errores.append("No se pudo guardar: el ISBN ya existe.")
            else:
                flash(f"Libro «{libro.titulo}» registrado correctamente.", "success")
                return redirect(url_for("libros.index"))
        for e in errores:
            flash(e, "danger")
        return render_template("libros/form.html", libro=None, datos=datos)

    return render_template("libros/form.html", libro=None, datos={"ejemplares_totales": "1"})


@libros_bp.route("/<int:libro_id>/editar", methods=["GET", "POST"])
def editar(libro_id):
    libro = db.get_or_404(Libro, libro_id)

    if request.method == "POST":
        datos, errores = _validar(request.form, libro)
        if not errores:
            _aplicar(libro, datos)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                errores.append("No se pudo guardar: el ISBN ya existe.")
            else:
                flash(f"Libro «{libro.titulo}» actualizado.", "success")
                return redirect(url_for("libros.index"))
        db.session.rollback()
        for e in errores:
            flash(e, "danger")
        return render_template("libros/form.html", libro=libro, datos=datos)

    datos = {
        "titulo": libro.titulo,
        "autor": libro.autor,
        "isbn": libro.isbn,
        "editorial": libro.editorial or "",
        "categoria": libro.categoria or "",
        "anio_publicacion": libro.anio_publicacion or "",
        "ejemplares_totales": libro.ejemplares_totales,
    }
    return render_template("libros/form.html", libro=libro, datos=datos)


@libros_bp.route("/<int:libro_id>/eliminar", methods=["POST"])
def eliminar(libro_id):
    libro = db.get_or_404(Libro, libro_id)

    titulo = libro.titulo
    try:
        db.session.delete(libro)
        db.session.commit()
    except IntegrityError:
        # La llave foránea de prestamos (ON DELETE RESTRICT) impide borrar libros prestados
        db.session.rollback()
        flash(f"No se puede eliminar «{titulo}»: tiene préstamos registrados.", "warning")
    else:
        flash(f"Libro «{titulo}» eliminado.", "success")
    return redirect(url_for("libros.index"))