"""Carga datos de ejemplo para la demostración y las pruebas.

Uso:   python datos_demo.py
Crea el usuario  demo@uadec.edu.mx  (contraseña: demo123) con gastos, ingresos,
deudas y metas de ejemplo. Las fechas son relativas a HOY, así que siempre hay
datos en los filtros de día, semana y mes. Si el usuario ya existe, no hace nada.
Para empezar de cero, borra el archivo gestor.db y vuelve a ejecutar la app.
"""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

import db

CORREO, CLAVE = "demo@uadec.edu.mx", "demo123"


def f(dias):
    """Fecha de hace `dias` días (negativo = en el futuro), en formato AAAA-MM-DD."""
    return (date.today() - timedelta(days=dias)).isoformat()


def main():
    db.inicializar_bd()
    con = db._conectar()
    if con.execute("SELECT 1 FROM usuario WHERE correo = ?", (CORREO,)).fetchone():
        print("El usuario demo ya existe; no se cargó nada.")
        return
    uid = con.execute("INSERT INTO usuario (correo, contrasena) VALUES (?, ?)",
                      (CORREO, generate_password_hash(CLAVE))).lastrowid
    cat = {r["nombre"]: r["id_categoria"] for r in
           con.execute("SELECT id_categoria, nombre FROM categoria WHERE es_predefinida = 1")}

    gastos = [  # (categoría, monto, hace_n_días, descripción)
        ("Comida", 85.50, 0, "Comida en la cafetería"),
        ("Transporte", 30, 0, "Camión"),
        ("Materiales escolares", 120, 1, "Copias y cuaderno"),
        ("Comida", 210, 2, "Super de la semana"),
        ("Gastos personales", 350, 3, "Corte de cabello"),
        ("Transporte", 60, 4, "Uber"),
        ("Comida", 95, 6, "Cena"),
    ]
    for categoria, monto, dias, desc in gastos:
        con.execute("INSERT INTO gasto (id_usuario, id_categoria, monto, fecha, descripcion) "
                    "VALUES (?, ?, ?, ?, ?)", (uid, cat[categoria], monto, f(dias), desc))

    for monto, dias, desc in [(6000, 5, "Mesada"), (2500, 1, "Trabajo de medio tiempo")]:
        con.execute("INSERT INTO ingreso (id_usuario, monto, fecha, descripcion) VALUES (?, ?, ?, ?)",
                    (uid, monto, f(dias), desc))

    # Deudas: (nombre, total, vence en n días, pagos [(monto, hace n días)])
    deudas = [("Pago de tarjeta", 3000, 12, [(500, 3)]),
              ("Préstamo a un amigo", 800, 30, []),
              ("Laptop a plazos", 9000, 90, [(1500, 10)])]
    for nombre, total, vence, pagos in deudas:
        saldo = total - sum(p[0] for p in pagos)
        id_d = con.execute("INSERT INTO deuda (id_usuario, nombre, monto_total, saldo, fecha_limite) "
                           "VALUES (?, ?, ?, ?, ?)", (uid, nombre, total, saldo, f(-vence))).lastrowid
        for monto, dias in pagos:
            con.execute("INSERT INTO pago_deuda (id_deuda, monto, fecha) VALUES (?, ?, ?)",
                        (id_d, monto, f(dias)))

    # Metas: (nombre, objetivo, plazo en días, aportaciones [(monto, hace n días)])
    metas = [("Celular nuevo", 8000, 120, [(1000, 8), (500, 2)]),
             ("Viaje de fin de semestre", 3000, 45, [(3000, 1)])]
    for nombre, objetivo, plazo, aportes in metas:
        ahorrado = sum(a[0] for a in aportes)
        id_m = con.execute("INSERT INTO meta_ahorro (id_usuario, nombre, monto_objetivo, fecha_limite, "
                           "monto_ahorrado, completada) VALUES (?, ?, ?, ?, ?, ?)",
                           (uid, nombre, objetivo, f(-plazo), ahorrado, int(ahorrado >= objetivo))).lastrowid
        for monto, dias in aportes:
            con.execute("INSERT INTO aportacion (id_meta, monto, fecha) VALUES (?, ?, ?)",
                        (id_m, monto, f(dias)))
    con.commit()
    con.close()
    print(f"Listo. Entra con  {CORREO}  /  {CLAVE}")


if __name__ == "__main__":
    main()
