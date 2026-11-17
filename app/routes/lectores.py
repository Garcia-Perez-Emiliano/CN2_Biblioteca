from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)

from sqlalchemy.exc import IntegrityError

from app import db
from app.models.lector import Lector


lectores_bp = Blueprint(
    "lectores",
    __name__,
    url_prefix="/lectores"
)

POR_PAGINA = 10


def _validar(form, lector=None):

    datos = {
        "nombre": form.get("nombre", "").strip(),
        "apellidos": form.get("apellidos", "").strip(),
        "correo": form.get("correo", "").strip(),
        "telefono": form.get("telefono", "").strip(),
        "matricula": form.get("matricula", "").strip(),
        "activo": "activo" in form,
    }

    errores = []

    if not datos["nombre"]:
        errores.append("El nombre es obligatorio.")

    if len(datos["nombre"]) > 100:
        errores.append("El nombre no puede exceder 100 caracteres.")

    if not datos["apellidos"]:
        errores.append("Los apellidos son obligatorios.")

    if len(datos["apellidos"]) > 100:
        errores.append("Los apellidos no pueden exceder 100 caracteres.")

    if not datos["correo"]:
        errores.append("El correo es obligatorio.")

    if len(datos["correo"]) > 120:
        errores.append("El correo no puede exceder 120 caracteres.")

    if len(datos["telefono"]) > 20:
        errores.append("El teléfono no puede exceder 20 caracteres.")

    if not datos["matricula"]:
        errores.append("La matrícula es obligatoria.")

    if len(datos["matricula"]) > 30:
        errores.append("La matrícula no puede exceder 30 caracteres.")

    existente_correo = Lector.query.filter_by(
        correo=datos["correo"]
    ).first()

    if existente_correo and (
        lector is None or existente_correo.id != lector.id
    ):
        errores.append(
            "Ya existe un lector registrado con ese correo."
        )

    existente_matricula = Lector.query.filter_by(
        matricula=datos["matricula"]
    ).first()

    if existente_matricula and (
        lector is None or existente_matricula.id != lector.id
    ):
        errores.append(
            "Ya existe un lector registrado con esa matrícula."
        )

    return datos, errores


def _aplicar(lector, datos):

    lector.nombre = datos["nombre"]
    lector.apellidos = datos["apellidos"]
    lector.correo = datos["correo"]
    lector.telefono = datos["telefono"] or None
    lector.matricula = datos["matricula"]
    lector.activo = datos["activo"]


@lectores_bp.route("/")
def index():

    q = request.args.get("q", "").strip()

    consulta = db.select(Lector)

    if q:

        patron = f"%{q}%"

        consulta = consulta.where(
            db.or_(
                Lector.nombre.ilike(patron),
                Lector.apellidos.ilike(patron),
                Lector.correo.ilike(patron),
                Lector.matricula.ilike(patron),
            )
        )

    pagina = request.args.get("page", 1, type=int)

    paginacion = db.paginate(
        consulta.order_by(Lector.nombre),
        page=pagina,
        per_page=POR_PAGINA,
        error_out=False,
    )

    return render_template(
        "lectores/index.html",
        paginacion=paginacion,
        q=q,
    )


@lectores_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():

    if request.method == "POST":

        datos, errores = _validar(request.form)

        if not errores:

            lector = Lector()

            _aplicar(lector, datos)

            db.session.add(lector)

            try:

                db.session.commit()

            except IntegrityError:

                db.session.rollback()

                errores.append(
                    "No se pudo guardar el lector."
                )

            else:

                flash(
                    f"Lector «{lector.nombre} {lector.apellidos}» registrado correctamente.",
                    "success",
                )

                return redirect(
                    url_for("lectores.index")
                )

        for e in errores:
            flash(e, "danger")

        return render_template(
            "lectores/form.html",
            lector=None,
            datos=datos,
        )

    return render_template(
        "lectores/form.html",
        lector=None,
        datos={
            "activo": True
        },
    )


@lectores_bp.route("/<int:lector_id>/editar", methods=["GET", "POST"])
def editar(lector_id):

    lector = db.get_or_404(
        Lector,
        lector_id
    )

    if request.method == "POST":

        datos, errores = _validar(
            request.form,
            lector
        )

        if not errores:

            _aplicar(
                lector,
                datos
            )

            try:

                db.session.commit()

            except IntegrityError:

                db.session.rollback()

                errores.append(
                    "No se pudo actualizar el lector."
                )

            else:

                flash(
                    f"Lector «{lector.nombre} {lector.apellidos}» actualizado.",
                    "success"
                )

                return redirect(
                    url_for("lectores.index")
                )

        db.session.rollback()

        for e in errores:
            flash(e, "danger")

        return render_template(
            "lectores/form.html",
            lector=lector,
            datos=datos
        )

    datos = {
        "nombre": lector.nombre,
        "apellidos": lector.apellidos,
        "correo": lector.correo,
        "telefono": lector.telefono or "",
        "matricula": lector.matricula,
        "activo": lector.activo,
    }

    return render_template(
        "lectores/form.html",
        lector=lector,
        datos=datos
    )

@lectores_bp.route("/<int:lector_id>/eliminar", methods=["POST"])
def eliminar(lector_id):

    lector = db.get_or_404(
        Lector,
        lector_id
    )

    nombre_completo = (
        f"{lector.nombre} {lector.apellidos}"
    )

    try:

        db.session.delete(lector)

        db.session.commit()

    except IntegrityError:

        db.session.rollback()

        flash(
            f"No se puede eliminar al lector «{nombre_completo}».",
            "warning"
        )

    else:

        flash(
            f"Lector «{nombre_completo}» eliminado.",
            "success"
        )

    return redirect(
        url_for("lectores.index")
    )