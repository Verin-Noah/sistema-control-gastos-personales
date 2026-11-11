# Arquitectura y documentación del código

Documento técnico del código fuente del *Sistema de control de gastos personales*.

## 1. Visión general

La aplicación es web y se ejecuta de forma local. El navegador pide páginas a un servidor escrito en Python con Flask. El servidor valida los datos, consulta o guarda información en una base de datos SQLite y devuelve la página resultante.

```
Navegador (HTML + CSS)  ──HTTP──►  Servidor Flask (app.py)  ──SQL──►  SQLite (gestor.db)
                                          │
                                   Acceso a datos (db.py)
```

Esto corresponde al diagrama de componentes (`5_diagrama_de_componentes.png`).

## 2. Archivos y carpetas

| Elemento | Responsabilidad | Componente del diagrama |
|---|---|---|
| `app.py` | Rutas, validaciones y reglas de negocio de todos los módulos | Gestores (cuentas, ingresos, gastos, deudas, metas) |
| `db.py` | Abre la conexión, crea las tablas la primera vez y carga las categorías predefinidas | Acceso a datos |
| `schema.sql` | Instrucciones `CREATE TABLE` de las 8 tablas | Base de datos |
| `templates/` | Páginas HTML (plantillas Jinja2) | Interfaz web |
| `static/estilo.css` | Estilos (colores, recuadros, tablas) | Interfaz web |
| `datos_demo.py` | Carga un usuario de ejemplo con datos de muestra | Apoyo para demostraciones |
| `tests/test_prototipo.py` | Pruebas automáticas sobre las rutas, con base de datos temporal | Pruebas |
| `docs/` | Esta documentación, los diagramas UML y la bitácora de versiones | Documentación |

## 3. Base de datos

El esquema sale del diagrama de clases (`4_diagrama_de_clases.png`): cada clase es una tabla, cada atributo una columna y cada relación una llave foránea.

| Tabla | Contenido | Relación principal |
|---|---|---|
| `usuario` | Correo y contraseña cifrada | — |
| `categoria` | Categorías predefinidas (`id_usuario` vacío) y propias | Pertenece a un usuario o es del sistema |
| `gasto` | Monto, fecha, descripción | Usuario y categoría |
| `ingreso` | Monto, fecha, descripción | Usuario |
| `deuda` | Nombre, monto total, saldo, fecha límite | Usuario |
| `pago_deuda` | Monto y fecha de cada pago | Deuda (composición) |
| `meta_ahorro` | Nombre, monto objetivo, fecha límite, monto ahorrado, completada | Usuario |
| `aportacion` | Monto y fecha de cada aportación | Meta (composición) |

Las restricciones `CHECK (monto > 0)` protegen los montos a nivel de base de datos, además de las validaciones de la aplicación.

## 4. Rutas

| Ruta | Métodos | Función | Requerimiento | Qué hace |
|---|---|---|---|---|
| `/` | GET | `raiz` | — | Lleva al inicio si hay sesión iniciada, o al login si no. |
| `/categorias` | GET | `categorias` | RF8 | Lista de categorías: las predefinidas y las propias del usuario. |
| `/categorias/nueva` | GET, POST | `categoria_nueva` | RF8 | HU6 / RF8: crear una categoría propia. |
| `/deudas` | GET | `deudas` | RF10, RF11 | HU8 / RF10-RF11: ver deudas con su saldo, cuotas y orden de prioridad. |
| `/deudas/<int:id_deuda>/pago` | GET, POST | `deuda_pago` | RF12 | HU9 / RF12: registrar un pago y actualizar el saldo. |
| `/deudas/nueva` | GET, POST | `deuda_nueva` | RF9 (CU2) | CU2 Registrar deuda (HU7 / RF9). |
| `/gastos` | GET | `gastos` | RF5 | HU4 / RF5: consultar gastos por día, semana o mes, con su total. |
| `/gastos/<int:id_gasto>/editar` | GET, POST | `gasto_editar` | RF6 | HU5 / RF6: modificar un gasto (mismas validaciones que al registrarlo). |
| `/gastos/<int:id_gasto>/eliminar` | GET, POST | `gasto_eliminar` | RF7 | HU5 / RF7: eliminar un gasto, pidiendo confirmación antes. |
| `/gastos/nuevo` | GET, POST | `gasto_nuevo` | RF4 (CU1) | CU1 Registrar gasto (HU3 / RF4). |
| `/ingresos` | GET | `ingresos` | RF17 | Lista de ingresos del mes con su total. |
| `/ingresos/<int:id_ingreso>/editar` | GET, POST | `ingreso_editar` | extra | Modificar un ingreso registrado. |
| `/ingresos/<int:id_ingreso>/eliminar` | GET, POST | `ingreso_eliminar` | extra | Eliminar un ingreso, pidiendo confirmación antes. |
| `/ingresos/nuevo` | GET, POST | `ingreso_nuevo` | RF17 | HU12 / RF17: registrar un ingreso (salario, mesada...). |
| `/inicio` | GET | `inicio` | RF18 | Pantalla principal: balance del mes y un recuadro por módulo con un dato vivo. |
| `/login` | GET, POST | `login` | RF2 | HU2 / RF2: iniciar sesión. |
| `/logout` | GET | `logout` | RF3 | RF3: cerrar sesión. |
| `/metas` | GET | `metas` | RF14, RF16 | HU10-HU11 / RF14, RF16: ver metas con su progreso y cuánto ahorrar por periodo. |
| `/metas/<int:id_meta>/aportacion` | GET, POST | `meta_aportacion` | RF15 | HU11 / RF15: registrar una aportación; marca la meta como completada si llega al objetivo. |
| `/metas/nueva` | GET, POST | `meta_nueva` | RF13, RF14 (CU3) | CU3 Crear meta de ahorro (HU10 / RF13). |
| `/registro` | GET, POST | `registro` | RF1 | HU1 / RF1: crear una cuenta con correo y contraseña. |

## 5. Reglas de negocio y decisiones de diseño

- **Contraseñas cifradas (RNF1):** se guardan con `werkzeug.security.generate_password_hash`; nunca en texto plano.
- **Privacidad (RNF2):** todas las consultas filtran por `id_usuario` de la sesión; si un registro no pertenece al usuario, se responde como si no existiera.
- **Validaciones (CU1, CU2, CU3):** monto mayor a cero, datos obligatorios, fechas no futuras en registros y posteriores a hoy en plazos. Los mensajes salen de los flujos alternos de los casos de uso.
- **Montos:** se aceptan con coma como separador de miles, signo `$` y espacios (`15,000` es quince mil).
- **Cuotas por periodo (RF10 y RF14):** el saldo pendiente se divide entre las semanas (días ÷ 7) o meses (días ÷ 30) que faltan hasta la fecha límite, redondeando hacia arriba. Si ya venció, se muestra el saldo completo.
- **Balance del mes (RF18):** disponible = ingresos − gastos − pagos de deudas − aportaciones a metas.
- **Pago y saldo en una sola transacción:** al registrar un pago o una aportación, el movimiento y el nuevo saldo se guardan juntos o no se guarda nada.
- **Confirmación al eliminar (RF7):** el borrado se hace por POST, tras una pantalla de confirmación.

## 6. Pruebas

`python tests/test_prototipo.py` ejecuta 94 pruebas de caja negra sobre las rutas con una base de datos temporal. Cubren cuenta, gastos, ingresos, deudas, metas, categorías y privacidad entre usuarios.

## 7. Historial de versiones

Ver `docs/bitacora_de_versiones.md`: qué incluyó cada versión y qué defectos se encontraron al probarla.
