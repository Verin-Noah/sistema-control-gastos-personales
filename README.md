# Sistema de control de gastos personales

Aplicación web para llevar el control de gastos, ingresos, deudas y metas de ahorro de una persona. Prototipo desarrollado para la materia de Ingeniería de Software (Facultad de Sistemas, UAdeC).

## ¿Qué permite hacer?

- **Cuenta:** registrarse, iniciar y cerrar sesión (contraseñas cifradas).
- **Gastos:** registrar, consultar por día, semana o mes con total y desglose por categoría, modificar y eliminar.
- **Categorías:** usar las predefinidas o crear las propias.
- **Ingresos:** registrar sueldo o mesada.
- **Deudas:** registrar deudas, ver cuánto pagar por semana o mes, ordenarlas por prioridad y registrar pagos.
- **Metas de ahorro:** crear metas, ver cuánto ahorrar por periodo y registrar aportaciones con su progreso.
- **Balance del mes:** ingresos − gastos − pagos de deudas − aportaciones a metas = disponible.

## Requisitos

- Python 3.10 o superior.
- Un navegador web (Chrome, Edge o Firefox).

## Instalación y uso

1. Descarga o clona este repositorio.
2. Abre una terminal en la carpeta del proyecto.
3. Instala la dependencia (solo la primera vez):
   ```
   pip install -r requirements.txt
   ```
4. Inicia la aplicación:
   ```
   python app.py
   ```
5. Abre en el navegador: http://127.0.0.1:8080

La base de datos (`gestor.db`, SQLite) se crea sola la primera vez. Para detener la aplicación, presiona `Ctrl + C` en la terminal.

### Datos de ejemplo (opcional)

```
python datos_demo.py
```

Crea el usuario `demo@uadec.edu.mx` (contraseña `demo123`) con gastos, ingresos, deudas y metas de muestra. Para empezar de cero, borra `gestor.db`.

### Pruebas automáticas

```
python tests/test_prototipo.py
```

Usan una base de datos temporal y no modifican `gestor.db`.

## Estructura del proyecto

```
app.py            Rutas, validaciones y reglas de negocio
db.py             Conexión a la base de datos
schema.sql        Tablas de la base de datos
datos_demo.py     Datos de ejemplo
templates/        Páginas HTML
static/           Estilos (CSS)
tests/            Pruebas automáticas
docs/             Arquitectura, diagramas UML y bitácora de versiones
```

## Documentación

- [Arquitectura y documentación del código](docs/arquitectura.md)
- [Bitácora de versiones](docs/bitacora_de_versiones.md)
- Diagramas UML en [`docs/diagramas/`](docs/diagramas/)

## Alcance

Es un prototipo académico que se ejecuta de forma local. No incluye conexión con bancos, pagos reales ni aplicación móvil.

## Tecnologías

Python, Flask, SQLite, HTML y CSS.
