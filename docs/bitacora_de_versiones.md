# Bitácora de versiones: Sistema de Control de Gastos Personales

Para cada versión: qué incluye, qué le faltaba o falló al probarla (evidencia para las pruebas) y cómo se resolvió en la siguiente.
Las pruebas automáticas (en el entorno de desarrollo) son aparte de las pruebas manuales de quien lo usó en su computadora.

---------------------------------------------------------------------
## v1: Base (7 nov 2026)
**Incluye:** registro de usuario, inicio y cierre de sesión, registrar gasto (CU1) con validaciones, consultar gastos por día, semana o mes con total y desglose por categoría. Base de datos SQLite con las 8 tablas del diagrama de clases. Paleta azul. Puerto 5000.

**Lo que faltaba / se encontró al probarla:**
1. El puerto 5000 estaba bloqueado en Windows ("Intento de acceso a un socket no permitido"). Se cambió a 8080.
2. El formulario "Registrar gasto" no tenía botón para volver o cancelar; el usuario quedaba "atorado" y solo podía usar la barra de navegación o el botón de atrás del navegador. (Pendiente para la versión estética.)
3. No se podía modificar ni eliminar un gasto (RF6 y RF7 aún no implementados).
4. No existían deudas, ingresos ni metas de ahorro.
5. La barra de navegación y la paleta (azul, muy común) quedaron pendientes de rediseño.

---------------------------------------------------------------------
## v2: Deudas, ingresos y balance (7 nov 2026)
**Incluye:** registrar deuda (CU2), registrar pago, cuota por semana y por mes, orden por vencimiento o por monto, ingresos (salario o mesada) y balance mensual (ingresos − gastos − pagos de deudas = disponible). Porcentaje del ingreso que se destinaría a deudas. Nueva paleta Burnt Sienna (#A0522D). Puerto 8080. Botón "Cancelar" en formularios de deuda, pago e ingreso. (Se entregó en dos paquetes: primero deudas y después ingresos con balance.)

**Lo que faltaba / se encontró al probarla:**
1. Las cuotas de las deudas parecían "raras" (por ejemplo $5,000 que vence en 13 días mostraba $2,500 por semana y $5,000 por mes). El cálculo era correcto (redondeo hacia arriba de semanas), pero faltaba explicarlo. Se añadió una nota con la fórmula bajo la tabla.
2. No había forma de archivar, ocultar o eliminar una deuda pagada (idea opcional: historial).
3. Los ingresos se podían registrar, pero no corregir ni borrar. (Detectado en la v4; corregido en la v5.)
4. El sistema leía "15,000" como 15 pesos (la coma se tomaba como punto decimal), no como quince mil. (Detectado en la v4; corregido en la v5.)
5. El formulario "Registrar gasto" seguía sin botón para cancelar.

---------------------------------------------------------------------
## v3: Metas de ahorro (7 nov 2026)
**Incluye:** crear meta (CU3) con cálculo inmediato del ahorro por semana y mes, registrar aportaciones, barra de progreso con porcentaje, meta marcada como completada al alcanzar el precio. Botón "Cancelar" en sus formularios.

**Lo que faltaba / se encontró al probarla:**
1. Pruebas manuales del usuario sin errores (meta de $4,000 a 60 días, aportación parcial, aportación que completa la meta).
2. Aún sin editar ni eliminar gastos, ingresos, deudas ni metas.
3. Las aportaciones a metas no se restaban del "disponible" del balance (la definición del RF18 solo consideraba gastos y pagos de deudas). Se identificó después como un error de diseño; corregido en la v8.

---------------------------------------------------------------------
## v4: Modificar y eliminar gastos (8 nov 2026)
**Incluye:** enlaces "Editar" y "Eliminar" en la lista de gastos. Editar con las mismas validaciones que al registrar. Eliminar con pantalla de confirmación previa (RF6 y RF7).

**Lo que faltaba / se encontró al probarla:**
1. La lista de ingresos no tenía "Editar" ni "Eliminar": al registrar por error un ingreso no se podía corregir. (Corregido en la v5.)
2. Al escribir "15,000" en un monto, se guardaba $15.00. (Corregido en la v5.)

---------------------------------------------------------------------
## v5: Ingresos editables y montos con coma (8 nov 2026)
**Incluye:** "Editar" y "Eliminar" (con confirmación) en la lista de ingresos. Los montos aceptan coma como separador de miles, signo $ y espacios ("15,000", "$15,000.50", "1 200"), en todos los formularios.

**Lo que falta (pendiente):**
- Editar o eliminar deudas y metas (no requerido).
- Categorías propias (RF8, prioridad Baja).
- Botón para cancelar en el formulario "Registrar gasto".
- Rediseño de la barra de navegación y paleta final (versión estética).
- Historial o archivado de deudas (opcional).
- Compatibilidad con celular: se decidió quitarla del alcance y del documento (RNF5 ahora solo menciona navegadores).

---------------------------------------------------------------------
## v6: Cancelar en "Registrar gasto" y datos de ejemplo (8 nov 2026)
**Incluye:** botón "Cancelar" en el formulario de registrar gasto (era el único formulario sin salida; defecto 2 de la v1). Script `datos_demo.py` que carga un usuario de ejemplo (demo@uadec.edu.mx / demo123) con gastos, ingresos, deudas y metas de muestra, con fechas relativas a hoy para que los filtros de día, semana y mes siempre tengan datos. Sirve para demostraciones y capturas de las pruebas.

**Lo que falta (pendiente):**
- Estética final: paleta definitiva y rediseño de la barra de navegación.
- Categorías propias (RF8, prioridad Baja).
- Historial o archivado de deudas (opcional).
- Editar o eliminar deudas y metas (no requerido).

---------------------------------------------------------------------
## v7: Categorías propias y rediseño visual (10 nov 2026)
**Incluye:**
- **Categorías propias (RF8, última función pendiente).** Pantalla de categorías (predefinidas y propias), crear categoría con validaciones (nombre obligatorio, máximo 40 caracteres, sin repetir una existente sin importar mayúsculas). La categoría aparece al registrar o editar un gasto, con un enlace "Crea una nueva" en el formulario. Cada usuario solo ve y usa las suyas.
- **Rediseño visual.** Pantalla de inicio con un resumen del mes (ingresos, gastos, pagos de deudas, disponible) y seis recuadros con ícono: Registrar gasto, Mis gastos, Ingresos, Deudas, Metas de ahorro y Categorías, cada uno con un dato actualizado. Barra superior mínima (nombre del sistema, Inicio y Salir) y botón "← Volver al inicio" en todas las pantallas internas. Paleta Burnt Sienna con tokens de color, verde y rojo apagados para positivo y negativo.

**Lo que se corrigió respecto a versiones anteriores:** la navegación saturada de la v1 a la v6 (siete enlaces en la barra) y la falta de salida desde algunas pantallas.

**Lo que falta (pendiente):**
- Historial o archivado de deudas (opcional).
- Editar o eliminar deudas, metas y categorías (no requerido).
- Compatibilidad con celular: fuera del alcance (se adaptó el diseño a pantallas angostas de forma básica, pero no se prueba ni se documenta como requisito).

---------------------------------------------------------------------
## v8: Las aportaciones a metas descuentan el disponible (10 nov 2026)
**Incluye:** el balance del mes ahora es ingresos − gastos − pagos de deudas − **aportaciones a metas** = disponible. El resumen del inicio muestra una cifra nueva, "Aportes a metas". RF18, HU13 y la visión del proyecto se actualizaron con esa definición.

**Defecto corregido (error que no habíamos detectado):**
Al registrar una aportación a una meta, el "Disponible" no cambiaba, aunque ese dinero ya estaba apartado. Con la regla anterior el usuario podía creer que tenía libre un dinero que ya había destinado a su ahorro, y gastarlo. Los pagos de deudas sí se descontaban; el ahorro, por inconsistencia en la definición de RF18, no. Se presentó desde la v3 (cuando se agregaron las metas) hasta la v7. Lo detectó el equipo al revisar si el balance coincidía con el dinero realmente libre.

**Qué probar:** con un ingreso de $1,000, registra una aportación de $300 a una meta: el disponible debe pasar a $700. Registra después un gasto de $100: debe quedar en $600.

**Lo que falta (pendiente):**
- Editar o eliminar deudas, metas y categorías (no requerido).
- Historial de deudas y tipo de ingreso: descartados por alcance.
