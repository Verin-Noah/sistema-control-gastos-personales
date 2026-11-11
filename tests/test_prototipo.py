"""Pruebas automáticas del prototipo (caja negra sobre las rutas de la aplicación).

Se ejecutan desde la carpeta raíz del proyecto:   python tests/test_prototipo.py
Usan una base de datos temporal, así que no tocan tu gestor.db.
"""
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import db  # noqa: E402

_carpeta_temporal = tempfile.mkdtemp()
db.RUTA_BD = os.path.join(_carpeta_temporal, "pruebas.db")   # base de datos solo para las pruebas

from datetime import date, timedelta
import app as m, db
db.inicializar_bd()
c = m.app.test_client()
RESULTADOS = []
def t(name, cond):
    RESULTADOS.append(bool(cond))
    print(("OK  " if cond else "FAIL"), name)
r=c.get('/gastos'); t('protegido redirige', r.status_code==302 and '/login' in r.headers['Location'])
r=c.post('/registro',data=dict(correo='a@uadec.edu.mx',contrasena='abc123',confirmacion='abc123')); t('registro', r.status_code==302)
r=c.post('/registro',data=dict(correo='a@uadec.edu.mx',contrasena='abc123',confirmacion='abc123')); t('correo duplicado rechazado', r.status_code==200 and 'Ya existe' in r.get_data(as_text=True))
r=c.post('/registro',data=dict(correo='x',contrasena='1',confirmacion='2')); t('registro inválido', r.status_code==200)
r=c.post('/login',data=dict(correo='a@uadec.edu.mx',contrasena='mala')); t('login malo', 'incorrectos' in r.get_data(as_text=True))
r=c.post('/login',data=dict(correo='a@uadec.edu.mx',contrasena='abc123')); t('login bueno', r.status_code==302)
t('inicio', c.get('/inicio').status_code==200)
h=date.today().isoformat()
def g(**k): return c.post('/gastos/nuevo',data=k)
r=g(monto='',id_categoria='1',fecha=h); t('falta monto', 'Falta el monto' in r.get_data(as_text=True))
r=g(monto='-5',id_categoria='1',fecha=h); t('monto negativo', 'mayor a cero' in r.get_data(as_text=True))
r=g(monto='abc',id_categoria='1',fecha=h); t('monto no numérico', 'mayor a cero' in r.get_data(as_text=True))
r=g(monto='10',id_categoria='1',fecha=(date.today()+timedelta(1)).isoformat()); t('fecha futura', 'futura' in r.get_data(as_text=True))
r=g(monto='10',id_categoria='999',fecha=h); t('categoría inexistente', 'no existe' in r.get_data(as_text=True))
r=g(monto='nan',id_categoria='1',fecha=h); t('nan rechazado', 'mayor a cero' in r.get_data(as_text=True))
r=g(monto='50.5',id_categoria='1',fecha=h,descripcion='camión'); t('gasto válido', r.status_code==302)
g(monto='100',id_categoria='2',fecha=h)
txt=c.get('/gastos?periodo=dia').get_data(as_text=True); t('total día 150.50', '$150.50' in txt)
for p in ('semana','mes','zzz'): t('periodo '+p, c.get('/gastos?periodo='+p).status_code==200)
# aislamiento entre usuarios
c2=m.app.test_client()
c2.post('/registro',data=dict(correo='b@uadec.edu.mx',contrasena='abc123',confirmacion='abc123'))
c2.post('/login',data=dict(correo='b@uadec.edu.mx',contrasena='abc123'))
t('otro usuario no ve gastos', '$0.00' in c2.get('/gastos').get_data(as_text=True))
c.get('/logout'); t('logout', c.get('/inicio').status_code==302)
# ---- deudas
c.post('/login',data=dict(correo='a@uadec.edu.mx',contrasena='abc123'))
fut=(date.today()+timedelta(days=60)).isoformat()
def d(**k): return c.post('/deudas/nueva',data=k)
t('deuda sin nombre', 'Falta el nombre' in d(nombre='',monto_total='100',fecha_limite=fut).get_data(as_text=True))
t('deuda monto 0', 'mayor a cero' in d(nombre='x',monto_total='0',fecha_limite=fut).get_data(as_text=True))
t('deuda fecha pasada', 'posterior' in d(nombre='x',monto_total='100',fecha_limite=h).get_data(as_text=True))
t('deuda válida', d(nombre='Laptop',monto_total='1200',fecha_limite=fut).status_code==302)
txt=c.get('/deudas').get_data(as_text=True)
t('lista deudas', 'Laptop' in txt and '$1,200.00' in txt)
t('cuota semanal 1200/9', '$133.33' in txt)
def p(**k): return c.post('/deudas/1/pago',data=k)
t('pago mayor al saldo', 'mayor al saldo' in p(monto='5000',fecha=h).get_data(as_text=True))
t('pago negativo', 'mayor a cero' in p(monto='-1',fecha=h).get_data(as_text=True))
t('pago válido', p(monto='200',fecha=h).status_code==302)
t('saldo actualizado', '$1,000.00' in c.get('/deudas').get_data(as_text=True))
t('pago liquida', p(monto='1000',fecha=h).status_code==302 and 'Pagada' in c.get('/deudas').get_data(as_text=True))
t('orden monto', c.get('/deudas?orden=monto').status_code==200)
c2.post('/login',data=dict(correo='b@uadec.edu.mx',contrasena='abc123'))
t('otro usuario no paga mi deuda', c2.post('/deudas/1/pago',data=dict(monto='1',fecha=h)).status_code==302 and c.get('/deudas').get_data(as_text=True).count('Pagada')==1)
t('deuda ajena no visible', 'Laptop' not in c2.get('/deudas').get_data(as_text=True))
# ---- ingresos
def i(**k): return c.post('/ingresos/nuevo',data=k)
t('ingreso sin monto', 'Falta el monto' in i(monto='',fecha=h).get_data(as_text=True))
t('ingreso negativo', 'mayor a cero' in i(monto='-3',fecha=h).get_data(as_text=True))
t('ingreso fecha futura', 'futura' in i(monto='5',fecha=(date.today()+timedelta(1)).isoformat()).get_data(as_text=True))
t('ingreso válido', i(monto='8000',fecha=h,descripcion='Sueldo').status_code==302)
t('lista ingresos', '$8,000.00' in c.get('/ingresos').get_data(as_text=True))
inicio=c.get('/inicio').get_data(as_text=True)
# gastos del día 150.50, pagos 1200 (200+1000), ingreso 8000 -> disponible 6649.50
t('balance disponible 6,649.50', '$6,649.50' in inicio)
d(nombre='Otra',monto_total='3000',fecha_limite=fut)
t('deudas vs ingreso', '% de ese ingreso' in c.get('/deudas').get_data(as_text=True) or '%</strong>' in c.get('/deudas').get_data(as_text=True))
t('ingreso no visible a otro', '$0.00' in c2.get('/ingresos').get_data(as_text=True))
# ---- metas
fut2=(date.today()+timedelta(days=60)).isoformat()
def mt(**k): return c.post('/metas/nueva',data=k)
t('meta sin nombre', 'Falta el nombre' in mt(nombre='',monto_objetivo='900',fecha_limite=fut2).get_data(as_text=True))
t('meta sin precio', 'Falta el precio' in mt(nombre='x',monto_objetivo='',fecha_limite=fut2).get_data(as_text=True))
t('meta precio 0', 'mayor a cero' in mt(nombre='x',monto_objetivo='0',fecha_limite=fut2).get_data(as_text=True))
t('meta sin fecha', 'Falta el tiempo' in mt(nombre='x',monto_objetivo='900',fecha_limite='').get_data(as_text=True))
t('meta fecha pasada', 'posterior' in mt(nombre='x',monto_objetivo='900',fecha_limite=h).get_data(as_text=True))
r=mt(nombre='Celular',monto_objetivo='4000',fecha_limite=fut2)
t('meta válida', r.status_code==302)
txt=c.get('/metas').get_data(as_text=True)
t('ahorro por periodo (4000/9sem=444.44)', '$444.44' in txt and '$2,000.00' in txt)
def ap(**k): return c.post('/metas/1/aportacion',data=k)
t('aportación mayor a falta', 'mayor a lo que falta' in ap(monto='5000',fecha=h).get_data(as_text=True))
t('aportación negativa', 'mayor a cero' in ap(monto='-1',fecha=h).get_data(as_text=True))
t('aportación válida', ap(monto='1000',fecha=h).status_code==302)
txt=c.get('/metas').get_data(as_text=True); t('progreso 25%', '25%' in txt and '$3,000.00' in txt)
t('aportación completa meta', ap(monto='3000',fecha=h).status_code==302 and 'Completada' in c.get('/metas').get_data(as_text=True))
t('no aportar a meta completada', 'ya fue completada' in c.get('/metas/1/aportacion',follow_redirects=True).get_data(as_text=True))
t('meta ajena no visible', 'Celular' not in c2.get('/metas').get_data(as_text=True))
t('meta ajena no aportable', 'no existe' in c2.post('/metas/1/aportacion',data=dict(monto='1',fecha=h),follow_redirects=True).get_data(as_text=True))
# ---- editar / eliminar gasto
c.post('/login',data=dict(correo='a@uadec.edu.mx',contrasena='abc123'))
t('formulario editar carga', 'value="50.5"' in c.get('/gastos/1/editar').get_data(as_text=True))
t('editar monto inválido', 'mayor a cero' in c.post('/gastos/1/editar',data=dict(monto='0',id_categoria='1',fecha=h)).get_data(as_text=True))
t('editar fecha futura', 'futura' in c.post('/gastos/1/editar',data=dict(monto='5',id_categoria='1',fecha=(date.today()+timedelta(1)).isoformat())).get_data(as_text=True))
t('editar válido', c.post('/gastos/1/editar',data=dict(monto='75',id_categoria='2',fecha=h,descripcion='nuevo')).status_code==302)
txt=c.get('/gastos?periodo=dia').get_data(as_text=True); t('gasto modificado visible', '$75.00' in txt and 'nuevo' in txt and '$175.00' in txt)
t('otro usuario no edita mi gasto', 'no existe' in c2.post('/gastos/1/editar',data=dict(monto='1',id_categoria='1',fecha=h),follow_redirects=True).get_data(as_text=True))
t('otro usuario no elimina mi gasto', 'no existe' in c2.post('/gastos/1/eliminar',follow_redirects=True).get_data(as_text=True) and '$75.00' in c.get('/gastos?periodo=dia').get_data(as_text=True))
t('pide confirmación', 'Sí, eliminar' in c.get('/gastos/1/eliminar').get_data(as_text=True) and '$75.00' in c.get('/gastos?periodo=dia').get_data(as_text=True))
t('eliminar confirmado', c.post('/gastos/1/eliminar').status_code==302 and '$100.00' in c.get('/gastos?periodo=dia').get_data(as_text=True))
t('eliminar inexistente', 'no existe' in c.get('/gastos/999/eliminar',follow_redirects=True).get_data(as_text=True))
# ---- separador de miles / editar-eliminar ingresos
c.post('/login',data=dict(correo='a@uadec.edu.mx',contrasena='abc123'))
t('15,000 = quince mil', m.leer_monto('15,000')==15000 and m.leer_monto('$15,000.50')==m.leer_monto('15000.50') and m.leer_monto('1 200')==1200)
t('texto sigue inválido', m.leer_monto('abc') is None and m.leer_monto('')is None)
i(monto='15,000',fecha=h,descripcion='Sueldo2')
txt=c.get('/ingresos').get_data(as_text=True); t('15,000 guardado como 15000', '$15,000.00' in txt)
from db import _conectar
idi=_conectar().execute("select id_ingreso from ingreso where descripcion='Sueldo2'").fetchone()[0]
t('editar ingreso carga', 'value="15000' in c.get(f'/ingresos/{idi}/editar').get_data(as_text=True))
t('editar ingreso inválido', 'mayor a cero' in c.post(f'/ingresos/{idi}/editar',data=dict(monto='0',fecha=h)).get_data(as_text=True))
t('editar ingreso válido', c.post(f'/ingresos/{idi}/editar',data=dict(monto='9000',fecha=h,descripcion='Sueldo2')).status_code==302 and '$9,000.00' in c.get('/ingresos').get_data(as_text=True))
t('otro no edita ingreso', 'no existe' in c2.post(f'/ingresos/{idi}/editar',data=dict(monto='1',fecha=h),follow_redirects=True).get_data(as_text=True))
t('otro no elimina ingreso', 'no existe' in c2.post(f'/ingresos/{idi}/eliminar',follow_redirects=True).get_data(as_text=True))
t('ingreso pide confirmación', 'Sí, eliminar' in c.get(f'/ingresos/{idi}/eliminar').get_data(as_text=True) and '$9,000.00' in c.get('/ingresos').get_data(as_text=True))
t('ingreso eliminado', c.post(f'/ingresos/{idi}/eliminar').status_code==302 and '$9,000.00' not in c.get('/ingresos').get_data(as_text=True))
# ---- datos demo + cancelar
import subprocess
t('gasto_nuevo tiene Cancelar', 'Cancelar' in c.get('/gastos/nuevo').get_data(as_text=True))
# ---- v7: categorías propias + inicio con recuadros
c.post('/login',data=dict(correo='a@uadec.edu.mx',contrasena='abc123'))
def cn(**k): return c.post('/categorias/nueva',data=k)
t('categoría sin nombre', 'Falta el nombre' in cn(nombre='   ').get_data(as_text=True))
t('categoría muy larga', 'pasar de 40' in cn(nombre='x'*41).get_data(as_text=True))
t('categoría repetida predefinida', 'Ya existe' in cn(nombre='comida').get_data(as_text=True))
t('categoría válida', cn(nombre='  Mascotas  ').status_code==302)
t('categoría repetida propia (otras mayúsculas)', 'Ya existe' in cn(nombre='MASCOTAS').get_data(as_text=True))
lst=c.get('/categorias').get_data(as_text=True); t('lista categorías', 'Mascotas' in lst and 'Predefinida' in lst and 'Propia' in lst)
t('categoría disponible al registrar gasto', 'Mascotas' in c.get('/gastos/nuevo').get_data(as_text=True))
idc=_conectar().execute("select id_categoria from categoria where nombre='Mascotas'").fetchone()[0]
t('gasto con categoría propia', c.post('/gastos/nuevo',data=dict(monto='99',id_categoria=str(idc),fecha=h)).status_code==302 and 'Mascotas' in c.get('/gastos?periodo=dia').get_data(as_text=True))
t('otro usuario no ve mi categoría', 'Mascotas' not in c2.get('/categorias').get_data(as_text=True) and 'Mascotas' not in c2.get('/gastos/nuevo').get_data(as_text=True))
t('otro usuario no puede usar mi categoría', 'no existe' in c2.post('/gastos/nuevo',data=dict(monto='5',id_categoria=str(idc),fecha=h)).get_data(as_text=True))
ini=c.get('/inicio').get_data(as_text=True)
t('inicio: 6 recuadros', ini.count('class="recuadro"')==6)
t('inicio: sin botón volver', 'Volver al inicio' not in ini)
t('pantallas internas: botón volver', all('Volver al inicio' in c.get(u).get_data(as_text=True) for u in ['/gastos','/gastos/nuevo','/ingresos','/deudas','/metas','/categorias']))
# ---- v8: las aportaciones a metas descuentan el disponible
c3=m.app.test_client()
c3.post('/registro',data=dict(correo='d@uadec.edu.mx',contrasena='abc123',confirmacion='abc123'))
c3.post('/login',data=dict(correo='d@uadec.edu.mx',contrasena='abc123'))
c3.post('/ingresos/nuevo',data=dict(monto='1000',fecha=h))
t('disponible inicial 1,000', '$1,000.00' in c3.get('/inicio').get_data(as_text=True))
c3.post('/metas/nueva',data=dict(nombre='Bici',monto_objetivo='2000',fecha_limite=fut2))
idm=_conectar().execute("select id_meta from meta_ahorro where nombre='Bici'").fetchone()[0]
c3.post(f'/metas/{idm}/aportacion',data=dict(monto='300',fecha=h))
ini3=c3.get('/inicio').get_data(as_text=True)
t('aportación resta del disponible (700)', '$700.00' in ini3 and 'Aportes a metas' in ini3)
c3.post('/gastos/nuevo',data=dict(monto='100',id_categoria='1',fecha=h))
t('gasto + aportación (600)', '$600.00' in c3.get('/inicio').get_data(as_text=True))

print()
print(f"{sum(RESULTADOS)} de {len(RESULTADOS)} pruebas pasaron")
sys.exit(0 if all(RESULTADOS) else 1)
