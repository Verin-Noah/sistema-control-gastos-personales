"""Sistema de Control de Gastos Personales: prototipo.

Para ejecutarlo:  python app.py   y abrir  http://127.0.0.1:8080
"""

import os
import re
import math
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import db

app = Flask(__name__)
# Clave para firmar la sesión. En un sistema real iría en una variable de entorno.
app.secret_key = os.environ.get("SECRET_KEY", "clave-de-desarrollo-cambiar")
app.teardown_appcontext(db.cerrar_conexion)

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# ---------------------------------------------------------------- utilidades
@app.template_filter("dinero")
def formato_dinero(valor):
    return "${:,.2f}".format(float(valor or 0))


@app.template_filter("fecha_larga")
def formato_fecha(texto):
    a, m, d = texto.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def login_requerido(vista):
    """Protege las pantallas: si no hay sesión iniciada, manda al login."""
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "id_usuario" not in session:
            flash("Inicia sesión para continuar.", "error")
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


def leer_monto(texto):
    """Convierte el texto a número. Devuelve None si no es un número válido."""
    limpio = (texto or "").replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        valor = Decimal(limpio)
    except InvalidOperation:
        return None
    return valor if valor.is_finite() else None


def leer_fecha(texto):
    try:
        return date.fromisoformat((texto or "").strip())
    except ValueError:
        return None


def categorias_del_usuario():
    """Categorías predefinidas + las propias del usuario (RNF2: solo las suyas)."""
    return db.obtener_conexion().execute(
        "SELECT id_categoria, nombre FROM categoria "
        "WHERE es_predefinida = 1 OR id_usuario = ? "
        "ORDER BY es_predefinida DESC, nombre",
        (session["id_usuario"],),
    ).fetchall()


def rango_del_periodo(periodo, hoy):
    """Devuelve (inicio, fin, etiqueta) según el periodo elegido."""
    if periodo == "dia":
        return hoy, hoy, "Hoy"
    if periodo == "semana":
        inicio = hoy - timedelta(days=hoy.weekday())          # lunes
        return inicio, inicio + timedelta(days=6), "Esta semana"
    inicio = hoy.replace(day=1)
    siguiente = (inicio + timedelta(days=32)).replace(day=1)
    return inicio, siguiente - timedelta(days=1), "Este mes"


# -------------------------------------------------------------------- cuenta
@app.route("/")
def raiz():
    """Lleva al inicio si hay sesión iniciada, o al login si no."""
    return redirect(url_for("inicio" if "id_usuario" in session else "login"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    """HU1 / RF1: crear una cuenta con correo y contraseña."""
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        clave = request.form.get("contrasena", "")
        confirmacion = request.form.get("confirmacion", "")
        errores = []
        if not PATRON_CORREO.match(correo):
            errores.append("Escribe un correo con formato válido.")
        if len(clave) < 6:
            errores.append("La contraseña debe tener al menos 6 caracteres.")
        if clave != confirmacion:
            errores.append("Las contraseñas no coinciden.")
        conexion = db.obtener_conexion()
        if not errores and conexion.execute(
                "SELECT 1 FROM usuario WHERE correo = ?", (correo,)).fetchone():
            errores.append("Ya existe una cuenta con ese correo.")
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("registro.html", correo=correo)
        conexion.execute(
            "INSERT INTO usuario (correo, contrasena) VALUES (?, ?)",
            (correo, generate_password_hash(clave)),   # RNF1: contraseña cifrada
        )
        conexion.commit()
        flash("Cuenta creada. Ya puedes iniciar sesión.", "ok")
        return redirect(url_for("login"))
    return render_template("registro.html", correo="")


@app.route("/login", methods=["GET", "POST"])
def login():
    """HU2 / RF2: iniciar sesión."""
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        clave = request.form.get("contrasena", "")
        usuario = db.obtener_conexion().execute(
            "SELECT * FROM usuario WHERE correo = ?", (correo,)).fetchone()
        if usuario and check_password_hash(usuario["contrasena"], clave):
            session.clear()
            session["id_usuario"] = usuario["id_usuario"]
            session["correo"] = usuario["correo"]
            return redirect(url_for("inicio"))
        flash("Correo o contraseña incorrectos.", "error")
        return render_template("login.html", correo=correo)
    return render_template("login.html", correo="")


@app.route("/logout")
def logout():
    """RF3: cerrar sesión."""
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("login"))


# -------------------------------------------------------------------- inicio
def suma_del_mes(sql_total, id_usuario, desde, hasta):
    """Ejecuta una consulta SUM(...) con (usuario, desde, hasta) y devuelve el número."""
    return db.obtener_conexion().execute(
        sql_total, (id_usuario, desde.isoformat(), hasta.isoformat())).fetchone()[0]


def resumen_del_mes():
    """Balance del mes: ingresos - gastos - pagos de deudas - aportaciones a metas = disponible."""
    uid = session["id_usuario"]
    desde, hasta, _ = rango_del_periodo("mes", date.today())
    ingresos = suma_del_mes(
        "SELECT COALESCE(SUM(monto), 0) FROM ingreso "
        "WHERE id_usuario = ? AND fecha BETWEEN ? AND ?", uid, desde, hasta)
    gastos_mes = suma_del_mes(
        "SELECT COALESCE(SUM(monto), 0) FROM gasto "
        "WHERE id_usuario = ? AND fecha BETWEEN ? AND ?", uid, desde, hasta)
    pagos = suma_del_mes(
        "SELECT COALESCE(SUM(p.monto), 0) FROM pago_deuda p "
        "JOIN deuda d ON d.id_deuda = p.id_deuda "
        "WHERE d.id_usuario = ? AND p.fecha BETWEEN ? AND ?", uid, desde, hasta)
    aportes = suma_del_mes(
        "SELECT COALESCE(SUM(a.monto), 0) FROM aportacion a "
        "JOIN meta_ahorro m ON m.id_meta = a.id_meta "
        "WHERE m.id_usuario = ? AND a.fecha BETWEEN ? AND ?", uid, desde, hasta)
    return {"ingresos": ingresos, "gastos": gastos_mes, "pagos": pagos, "aportes": aportes,
            "disponible": ingresos - gastos_mes - pagos - aportes}


@app.route("/inicio")
@login_requerido
def inicio():
    """Pantalla principal: balance del mes y un recuadro por módulo con un dato vivo."""
    uid = session["id_usuario"]
    conexion = db.obtener_conexion()
    deudas_pendientes = conexion.execute(
        "SELECT COUNT(*), COALESCE(SUM(saldo), 0) FROM deuda WHERE id_usuario = ? AND saldo > 0",
        (uid,)).fetchone()
    metas_activas = conexion.execute(
        "SELECT COUNT(*) FROM meta_ahorro WHERE id_usuario = ? AND completada = 0",
        (uid,)).fetchone()[0]
    categorias_propias = conexion.execute(
        "SELECT COUNT(*) FROM categoria WHERE id_usuario = ?", (uid,)).fetchone()[0]
    return render_template("inicio.html", resumen=resumen_del_mes(),
                           mes=MESES[date.today().month - 1],
                           n_deudas=deudas_pendientes[0], saldo_deudas=deudas_pendientes[1],
                           n_metas=metas_activas, n_categorias=categorias_propias)


# ----------------------------------------------------------------- categorías
def validar_categoria(nombre):
    """RF8: el nombre es obligatorio, razonable y no puede repetirse (sin importar mayúsculas)."""
    if not nombre:
        return "Falta el nombre de la categoría."
    if len(nombre) > 40:
        return "El nombre no puede pasar de 40 caracteres."
    existentes = [c["nombre"].casefold() for c in categorias_del_usuario()]
    if nombre.casefold() in existentes:
        return "Ya existe una categoría con ese nombre."
    return None


@app.route("/categorias")
@login_requerido
def categorias():
    """Lista de categorías: las predefinidas y las propias del usuario."""
    return render_template("categorias.html", lista=db.obtener_conexion().execute(
        "SELECT nombre, es_predefinida FROM categoria "
        "WHERE es_predefinida = 1 OR id_usuario = ? ORDER BY es_predefinida DESC, nombre",
        (session["id_usuario"],)).fetchall())


@app.route("/categorias/nueva", methods=["GET", "POST"])
@login_requerido
def categoria_nueva():
    """HU6 / RF8: crear una categoría propia."""
    if request.method == "POST":
        nombre = " ".join(request.form.get("nombre", "").split())   # quita espacios de sobra
        error = validar_categoria(nombre)
        if error:
            flash(error, "error")
            return render_template("categoria_nueva.html", nombre=nombre)
        conexion = db.obtener_conexion()
        conexion.execute(
            "INSERT INTO categoria (nombre, es_predefinida, id_usuario) VALUES (?, 0, ?)",
            (nombre, session["id_usuario"]))
        conexion.commit()
        flash("Categoría creada. Ya puedes usarla al registrar un gasto.", "ok")
        return redirect(url_for("categorias"))
    return render_template("categoria_nueva.html", nombre="")


# -------------------------------------------------------------------- gastos
def validar_gasto(form):
    """Reglas de negocio del CU1. Devuelve (errores, datos_limpios)."""
    errores = []
    monto = leer_monto(form.get("monto"))
    fecha = leer_fecha(form.get("fecha"))
    id_categoria = form.get("id_categoria", "").strip()

    if not form.get("monto", "").strip():
        errores.append("Falta el monto.")          # flujo alterno 2a
    elif monto is None or monto <= 0:
        errores.append("El monto debe ser mayor a cero.")   # flujo alterno 2b
    if not id_categoria:
        errores.append("Falta la categoría.")      # flujo alterno 2a
    if not form.get("fecha", "").strip():
        errores.append("Falta la fecha.")          # flujo alterno 2a
    elif fecha is None:
        errores.append("La fecha no es válida.")
    elif fecha > date.today():
        errores.append("La fecha no puede ser futura.")      # flujo alterno 2c

    if id_categoria and not any(str(c["id_categoria"]) == id_categoria
                                for c in categorias_del_usuario()):
        errores.append("La categoría elegida no existe.")
    datos = {
        "monto": round(float(monto), 2) if monto is not None and monto > 0 else None,
        "fecha": fecha.isoformat() if fecha else None,
        "id_categoria": id_categoria,
        "descripcion": form.get("descripcion", "").strip(),
    }
    return errores, datos


@app.route("/gastos/nuevo", methods=["GET", "POST"])
@login_requerido
def gasto_nuevo():
    """CU1 Registrar gasto (HU3 / RF4)."""
    if request.method == "POST":
        errores, datos = validar_gasto(request.form)
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            # Se vuelve a mostrar el formulario con lo que el usuario ya escribió
            return render_template("gasto_nuevo.html", categorias=categorias_del_usuario(),
                                   datos=request.form, hoy=date.today().isoformat())
        conexion = db.obtener_conexion()
        conexion.execute(
            "INSERT INTO gasto (id_usuario, id_categoria, monto, fecha, descripcion) "
            "VALUES (?, ?, ?, ?, ?)",
            (session["id_usuario"], datos["id_categoria"], datos["monto"],
             datos["fecha"], datos["descripcion"]),
        )
        conexion.commit()
        flash("Gasto registrado.", "ok")
        return redirect(url_for("gastos"))
    return render_template("gasto_nuevo.html", categorias=categorias_del_usuario(),
                           datos={}, hoy=date.today().isoformat())


def obtener_gasto_del_usuario(id_gasto):
    """Busca el gasto solo si pertenece al usuario con sesión (RNF2)."""
    return db.obtener_conexion().execute(
        "SELECT g.*, c.nombre AS categoria FROM gasto g "
        "JOIN categoria c ON c.id_categoria = g.id_categoria "
        "WHERE g.id_gasto = ? AND g.id_usuario = ?",
        (id_gasto, session["id_usuario"])).fetchone()


@app.route("/gastos/<int:id_gasto>/editar", methods=["GET", "POST"])
@login_requerido
def gasto_editar(id_gasto):
    """HU5 / RF6: modificar un gasto (mismas validaciones que al registrarlo)."""
    gasto = obtener_gasto_del_usuario(id_gasto)
    if gasto is None:
        flash("Ese gasto no existe.", "error")
        return redirect(url_for("gastos"))
    hoy = date.today().isoformat()
    if request.method == "POST":
        errores, datos = validar_gasto(request.form)
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("gasto_editar.html", gasto=gasto, datos=request.form,
                                   categorias=categorias_del_usuario(), hoy=hoy)
        conexion = db.obtener_conexion()
        conexion.execute(
            "UPDATE gasto SET id_categoria = ?, monto = ?, fecha = ?, descripcion = ? "
            "WHERE id_gasto = ? AND id_usuario = ?",
            (datos["id_categoria"], datos["monto"], datos["fecha"], datos["descripcion"],
             id_gasto, session["id_usuario"]))
        conexion.commit()
        flash("Gasto actualizado.", "ok")
        return redirect(url_for("gastos"))
    datos = {"monto": gasto["monto"], "id_categoria": str(gasto["id_categoria"]),
             "fecha": gasto["fecha"], "descripcion": gasto["descripcion"] or ""}
    return render_template("gasto_editar.html", gasto=gasto, datos=datos,
                           categorias=categorias_del_usuario(), hoy=hoy)


@app.route("/gastos/<int:id_gasto>/eliminar", methods=["GET", "POST"])
@login_requerido
def gasto_eliminar(id_gasto):
    """HU5 / RF7: eliminar un gasto, pidiendo confirmación antes."""
    gasto = obtener_gasto_del_usuario(id_gasto)
    if gasto is None:
        flash("Ese gasto no existe.", "error")
        return redirect(url_for("gastos"))
    if request.method == "POST":          # el usuario confirmó
        conexion = db.obtener_conexion()
        conexion.execute("DELETE FROM gasto WHERE id_gasto = ? AND id_usuario = ?",
                         (id_gasto, session["id_usuario"]))
        conexion.commit()
        flash("Gasto eliminado.", "ok")
        return redirect(url_for("gastos"))
    return render_template("gasto_eliminar.html", gasto=gasto)


@app.route("/gastos")
@login_requerido
def gastos():
    """HU4 / RF5: consultar gastos por día, semana o mes, con su total."""
    periodo = request.args.get("periodo", "mes")
    if periodo not in ("dia", "semana", "mes"):
        periodo = "mes"
    desde, hasta, etiqueta = rango_del_periodo(periodo, date.today())
    conexion = db.obtener_conexion()
    parametros = (session["id_usuario"], desde.isoformat(), hasta.isoformat())
    lista = conexion.execute(
        "SELECT g.id_gasto, g.monto, g.fecha, g.descripcion, c.nombre AS categoria "
        "FROM gasto g JOIN categoria c ON c.id_categoria = g.id_categoria "
        "WHERE g.id_usuario = ? AND g.fecha BETWEEN ? AND ? "
        "ORDER BY g.fecha DESC, g.id_gasto DESC", parametros).fetchall()
    por_categoria = conexion.execute(
        "SELECT c.nombre AS categoria, SUM(g.monto) AS total "
        "FROM gasto g JOIN categoria c ON c.id_categoria = g.id_categoria "
        "WHERE g.id_usuario = ? AND g.fecha BETWEEN ? AND ? "
        "GROUP BY c.nombre ORDER BY total DESC", parametros).fetchall()
    total = sum(fila["monto"] for fila in lista)
    return render_template("gastos.html", lista=lista, por_categoria=por_categoria,
                           total=total, periodo=periodo, etiqueta=etiqueta,
                           desde=desde.isoformat(), hasta=hasta.isoformat())


# ------------------------------------------------------------------- ingresos
def validar_ingreso(form):
    """Reglas del ingreso. Devuelve (errores, monto, fecha)."""
    monto = leer_monto(form.get("monto"))
    fecha = leer_fecha(form.get("fecha"))
    errores = []
    if not form.get("monto", "").strip():
        errores.append("Falta el monto.")
    elif monto is None or monto <= 0:
        errores.append("El monto debe ser mayor a cero.")
    if not form.get("fecha", "").strip():
        errores.append("Falta la fecha.")
    elif fecha is None:
        errores.append("La fecha no es válida.")
    elif fecha > date.today():
        errores.append("La fecha no puede ser futura.")
    return errores, monto, fecha


def obtener_ingreso_del_usuario(id_ingreso):
    return db.obtener_conexion().execute(
        "SELECT * FROM ingreso WHERE id_ingreso = ? AND id_usuario = ?",
        (id_ingreso, session["id_usuario"])).fetchone()


@app.route("/ingresos/nuevo", methods=["GET", "POST"])
@login_requerido
def ingreso_nuevo():
    """HU12 / RF17: registrar un ingreso (salario, mesada...)."""
    hoy = date.today().isoformat()
    if request.method == "POST":
        errores, monto, fecha = validar_ingreso(request.form)
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("ingreso_nuevo.html", datos=request.form, hoy=hoy)
        conexion = db.obtener_conexion()
        conexion.execute(
            "INSERT INTO ingreso (id_usuario, monto, fecha, descripcion) VALUES (?, ?, ?, ?)",
            (session["id_usuario"], round(float(monto), 2), fecha.isoformat(),
             request.form.get("descripcion", "").strip()))
        conexion.commit()
        flash("Ingreso registrado.", "ok")
        return redirect(url_for("ingresos"))
    return render_template("ingreso_nuevo.html", datos={}, hoy=hoy)


@app.route("/ingresos/<int:id_ingreso>/editar", methods=["GET", "POST"])
@login_requerido
def ingreso_editar(id_ingreso):
    """Modificar un ingreso registrado."""
    ingreso = obtener_ingreso_del_usuario(id_ingreso)
    if ingreso is None:
        flash("Ese ingreso no existe.", "error")
        return redirect(url_for("ingresos"))
    hoy = date.today().isoformat()
    if request.method == "POST":
        errores, monto, fecha = validar_ingreso(request.form)
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("ingreso_editar.html", datos=request.form, hoy=hoy)
        conexion = db.obtener_conexion()
        conexion.execute(
            "UPDATE ingreso SET monto = ?, fecha = ?, descripcion = ? "
            "WHERE id_ingreso = ? AND id_usuario = ?",
            (round(float(monto), 2), fecha.isoformat(),
             request.form.get("descripcion", "").strip(), id_ingreso, session["id_usuario"]))
        conexion.commit()
        flash("Ingreso actualizado.", "ok")
        return redirect(url_for("ingresos"))
    datos = {"monto": ingreso["monto"], "fecha": ingreso["fecha"],
             "descripcion": ingreso["descripcion"] or ""}
    return render_template("ingreso_editar.html", datos=datos, hoy=hoy)


@app.route("/ingresos/<int:id_ingreso>/eliminar", methods=["GET", "POST"])
@login_requerido
def ingreso_eliminar(id_ingreso):
    """Eliminar un ingreso, pidiendo confirmación antes."""
    ingreso = obtener_ingreso_del_usuario(id_ingreso)
    if ingreso is None:
        flash("Ese ingreso no existe.", "error")
        return redirect(url_for("ingresos"))
    if request.method == "POST":
        conexion = db.obtener_conexion()
        conexion.execute("DELETE FROM ingreso WHERE id_ingreso = ? AND id_usuario = ?",
                         (id_ingreso, session["id_usuario"]))
        conexion.commit()
        flash("Ingreso eliminado.", "ok")
        return redirect(url_for("ingresos"))
    return render_template("ingreso_eliminar.html", ingreso=ingreso)


@app.route("/ingresos")
@login_requerido
def ingresos():
    """Lista de ingresos del mes con su total."""
    desde, hasta, _ = rango_del_periodo("mes", date.today())
    lista = db.obtener_conexion().execute(
        "SELECT id_ingreso, monto, fecha, descripcion FROM ingreso "
        "WHERE id_usuario = ? AND fecha BETWEEN ? AND ? ORDER BY fecha DESC, id_ingreso DESC",
        (session["id_usuario"], desde.isoformat(), hasta.isoformat())).fetchall()
    return render_template("ingresos.html", lista=lista,
                           total=sum(f["monto"] for f in lista),
                           mes=MESES[date.today().month - 1])


# --------------------------------------------------------------------- metas
def obtener_meta_del_usuario(id_meta):
    """Busca la meta solo si pertenece al usuario con sesión (RNF2)."""
    return db.obtener_conexion().execute(
        "SELECT * FROM meta_ahorro WHERE id_meta = ? AND id_usuario = ?",
        (id_meta, session["id_usuario"])).fetchone()


@app.route("/metas")
@login_requerido
def metas():
    """HU10-HU11 / RF14, RF16: ver metas con su progreso y cuánto ahorrar por periodo."""
    filas = db.obtener_conexion().execute(
        "SELECT * FROM meta_ahorro WHERE id_usuario = ? ORDER BY completada, fecha_limite",
        (session["id_usuario"],)).fetchall()
    hoy = date.today()
    lista = []
    for m in filas:
        falta = round(m["monto_objetivo"] - m["monto_ahorrado"], 2)
        limite = date.fromisoformat(m["fecha_limite"])
        semanal, mensual = (calcular_cuotas(falta, limite, hoy)
                            if not m["completada"] else (0, 0))
        lista.append({"id": m["id_meta"], "nombre": m["nombre"],
                      "objetivo": m["monto_objetivo"], "ahorrado": m["monto_ahorrado"],
                      "falta": falta, "fecha_limite": m["fecha_limite"],
                      "completada": bool(m["completada"]),
                      "vencida": not m["completada"] and limite < hoy,
                      "porcentaje": min(100, int(m["monto_ahorrado"] / m["monto_objetivo"] * 100)),
                      "semanal": semanal, "mensual": mensual})
    return render_template("metas.html", lista=lista)


@app.route("/metas/nueva", methods=["GET", "POST"])
@login_requerido
def meta_nueva():
    """CU3 Crear meta de ahorro (HU10 / RF13)."""
    manana = (date.today() + timedelta(days=1)).isoformat()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        monto = leer_monto(request.form.get("monto_objetivo"))
        limite = leer_fecha(request.form.get("fecha_limite"))
        errores = []
        if not nombre:
            errores.append("Falta el nombre del artículo o meta.")     
        if not request.form.get("monto_objetivo", "").strip():
            errores.append("Falta el precio.")                           
        elif monto is None or monto <= 0:
            errores.append("El precio debe ser mayor a cero.")           
        if not request.form.get("fecha_limite", "").strip():
            errores.append("Falta el tiempo para alcanzar la meta.")     
        elif limite is None:
            errores.append("La fecha no es válida.")
        elif limite <= date.today():
            errores.append("La fecha para alcanzar la meta debe ser posterior a hoy.")
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("meta_nueva.html", datos=request.form, manana=manana)
        monto = round(float(monto), 2)
        conexion = db.obtener_conexion()
        conexion.execute(
            "INSERT INTO meta_ahorro (id_usuario, nombre, monto_objetivo, fecha_limite) "
            "VALUES (?, ?, ?, ?)", (session["id_usuario"], nombre, monto, limite.isoformat()))
        conexion.commit()
        semanal, mensual = calcular_cuotas(monto, limite, date.today())
        # El cálculo se muestra de inmediato (requisito especial 1 del CU3)
        flash(f"Meta guardada. Para lograrla debes ahorrar {formato_dinero(semanal)} "
              f"por semana o {formato_dinero(mensual)} por mes.", "ok")
        return redirect(url_for("metas"))
    return render_template("meta_nueva.html", datos={}, manana=manana)


@app.route("/metas/<int:id_meta>/aportacion", methods=["GET", "POST"])
@login_requerido
def meta_aportacion(id_meta):
    """HU11 / RF15: registrar una aportación; marca la meta como completada si llega al objetivo."""
    meta = obtener_meta_del_usuario(id_meta)
    if meta is None or meta["completada"]:
        flash("Esa meta no existe o ya fue completada.", "error")
        return redirect(url_for("metas"))
    falta = round(meta["monto_objetivo"] - meta["monto_ahorrado"], 2)
    hoy = date.today().isoformat()
    if request.method == "POST":
        monto = leer_monto(request.form.get("monto"))
        fecha = leer_fecha(request.form.get("fecha"))
        errores = []
        if not request.form.get("monto", "").strip():
            errores.append("Falta el monto de la aportación.")
        elif monto is None or monto <= 0:
            errores.append("El monto debe ser mayor a cero.")
        elif float(monto) > falta + 1e-9:
            errores.append("La aportación no puede ser mayor a lo que falta para la meta.")
        if fecha is None:
            errores.append("La fecha no es válida.")
        elif fecha > date.today():
            errores.append("La fecha no puede ser futura.")
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("meta_aportacion.html", meta=meta, falta=falta,
                                   datos=request.form, hoy=hoy)
        monto = round(float(monto), 2)
        conexion = db.obtener_conexion()
        conexion.execute("INSERT INTO aportacion (id_meta, monto, fecha) VALUES (?, ?, ?)",
                         (id_meta, monto, fecha.isoformat()))
        conexion.execute(
            "UPDATE meta_ahorro SET monto_ahorrado = ROUND(monto_ahorrado + ?, 2), "
            "completada = CASE WHEN ROUND(monto_ahorrado + ?, 2) >= monto_objetivo THEN 1 ELSE 0 END "
            "WHERE id_meta = ?", (monto, monto, id_meta))
        conexion.commit()
        flash("Aportación registrada.", "ok")
        if round(meta["monto_ahorrado"] + monto, 2) >= meta["monto_objetivo"]:
            flash("¡Meta completada!", "ok")
        return redirect(url_for("metas"))
    return render_template("meta_aportacion.html", meta=meta, falta=falta, datos={}, hoy=hoy)


# -------------------------------------------------------------------- deudas
def calcular_cuotas(saldo, fecha_limite, hoy):
    """RF10: cuánto pagar por semana y por mes para liquidar la deuda a tiempo.

    Se reparte el saldo pendiente entre las semanas (o meses de 30 días) que
    faltan. Si ya venció, toda la deuda es lo que falta por pagar.
    """
    dias = (fecha_limite - hoy).days
    if dias <= 0:
        return saldo, saldo
    semanas = max(1, math.ceil(dias / 7))
    meses = max(1, math.ceil(dias / 30))
    return round(saldo / semanas, 2), round(saldo / meses, 2)


def obtener_deuda_del_usuario(id_deuda):
    """Busca la deuda solo si pertenece al usuario con sesión (RNF2)."""
    return db.obtener_conexion().execute(
        "SELECT * FROM deuda WHERE id_deuda = ? AND id_usuario = ?",
        (id_deuda, session["id_usuario"])).fetchone()


@app.route("/deudas")
@login_requerido
def deudas():
    """HU8 / RF10-RF11: ver deudas con su saldo, cuotas y orden de prioridad."""
    orden = request.args.get("orden", "vencimiento")
    if orden not in ("vencimiento", "monto"):
        orden = "vencimiento"
    criterio = "fecha_limite ASC" if orden == "vencimiento" else "saldo DESC"
    filas = db.obtener_conexion().execute(
        f"SELECT * FROM deuda WHERE id_usuario = ? ORDER BY (saldo <= 0), {criterio}",
        (session["id_usuario"],)).fetchall()
    hoy = date.today()
    lista, total_pendiente, total_semanal, total_mensual = [], 0, 0, 0
    for d in filas:
        limite = date.fromisoformat(d["fecha_limite"])
        pendiente = d["saldo"] > 0
        semanal, mensual = calcular_cuotas(d["saldo"], limite, hoy) if pendiente else (0, 0)
        lista.append({"id": d["id_deuda"], "nombre": d["nombre"],
                      "monto_total": d["monto_total"], "saldo": d["saldo"],
                      "fecha_limite": d["fecha_limite"], "pendiente": pendiente,
                      "vencida": pendiente and limite < hoy,
                      "semanal": semanal, "mensual": mensual})
        if pendiente:
            total_pendiente += d["saldo"]
            total_semanal += semanal
            total_mensual += mensual
    ingresos_mes = resumen_del_mes()["ingresos"]
    return render_template("deudas.html", lista=lista, orden=orden,
                           ingresos_mes=ingresos_mes,
                           total_pendiente=total_pendiente,
                           total_semanal=total_semanal, total_mensual=total_mensual)


@app.route("/deudas/nueva", methods=["GET", "POST"])
@login_requerido
def deuda_nueva():
    """CU2 Registrar deuda (HU7 / RF9)."""
    manana = (date.today() + timedelta(days=1)).isoformat()
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        monto = leer_monto(request.form.get("monto_total"))
        limite = leer_fecha(request.form.get("fecha_limite"))
        errores = []
        if not nombre:
            errores.append("Falta el nombre de la deuda.")
        if not request.form.get("monto_total", "").strip():
            errores.append("Falta el monto total.")
        elif monto is None or monto <= 0:
            errores.append("El monto total debe ser mayor a cero.")
        if not request.form.get("fecha_limite", "").strip():
            errores.append("Falta la fecha límite.")
        elif limite is None:
            errores.append("La fecha límite no es válida.")
        elif limite <= date.today():
            errores.append("La fecha límite debe ser posterior a hoy.")
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("deuda_nueva.html", datos=request.form, manana=manana)
        monto = round(float(monto), 2)
        conexion = db.obtener_conexion()
        conexion.execute(
            "INSERT INTO deuda (id_usuario, nombre, monto_total, saldo, fecha_limite) "
            "VALUES (?, ?, ?, ?, ?)",       # al inicio, el saldo es todo el monto
            (session["id_usuario"], nombre, monto, monto, limite.isoformat()))
        conexion.commit()
        flash("Deuda registrada.", "ok")
        return redirect(url_for("deudas"))
    return render_template("deuda_nueva.html", datos={}, manana=manana)


@app.route("/deudas/<int:id_deuda>/pago", methods=["GET", "POST"])
@login_requerido
def deuda_pago(id_deuda):
    """HU9 / RF12: registrar un pago y actualizar el saldo."""
    deuda = obtener_deuda_del_usuario(id_deuda)
    if deuda is None:
        flash("Esa deuda no existe.", "error")
        return redirect(url_for("deudas"))
    hoy = date.today().isoformat()
    if request.method == "POST":
        monto = leer_monto(request.form.get("monto"))
        fecha = leer_fecha(request.form.get("fecha"))
        errores = []
        if not request.form.get("monto", "").strip():
            errores.append("Falta el monto del pago.")
        elif monto is None or monto <= 0:
            errores.append("El monto debe ser mayor a cero.")
        elif float(monto) > deuda["saldo"] + 1e-9:
            errores.append("El pago no puede ser mayor al saldo pendiente.")
        if fecha is None:
            errores.append("La fecha no es válida.")
        elif fecha > date.today():
            errores.append("La fecha no puede ser futura.")
        if errores:
            for mensaje in errores:
                flash(mensaje, "error")
            return render_template("deuda_pago.html", deuda=deuda, datos=request.form, hoy=hoy)
        monto = round(float(monto), 2)
        conexion = db.obtener_conexion()
        conexion.execute("INSERT INTO pago_deuda (id_deuda, monto, fecha) VALUES (?, ?, ?)",
                         (id_deuda, monto, fecha.isoformat()))
        conexion.execute("UPDATE deuda SET saldo = ROUND(saldo - ?, 2) WHERE id_deuda = ?",
                         (monto, id_deuda))
        conexion.commit()       # pago y nuevo saldo se guardan juntos o no se guarda nada
        flash("Pago registrado.", "ok")
        return redirect(url_for("deudas"))
    return render_template("deuda_pago.html", deuda=deuda, datos={}, hoy=hoy)


if __name__ == "__main__":
    db.inicializar_bd()
    app.run(debug=True, port=8080)
