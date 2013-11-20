
import sys, os, json
abspath = os.path.dirname(__file__)
sys.path.append(abspath)
if abspath!='':
	os.chdir(abspath)

from boe.db import DBConnector, Usuario, PalagraClave, Regla, Alertas
from boe.utils import cargar_conf, cifrar_id, descifrar_id, FICHERO_CONFIGURACION
import logging

CONF = cargar_conf(FICHERO_CONFIGURACION)
DB = DBConnector(CONF)

import web
if CONF.has_option("web", "cookie_name"):
	web.config.session_parameters['cookie_name'] = CONF.get("web", "cookie_name")
if CONF.has_option("web", "cookie_domain"):
	web.config.session_parameters['cookie_domain'] = CONF.get("web", "cookie_domain")
if CONF.has_option("web", "cookie_salt"):
	web.config.session_parameters['secret_key'] = CONF.get("web", "cookie_salt")
web.config.debug = CONF.getboolean("web", "debug")
web.config.session_parameters['timeout'] = 24 * 60 * 60 # 24 hours in seconds
web.config.session_parameters['ignore_expiry'] = False
web.config.session_parameters['ignore_change_ip'] = False
web.config.session_parameters['expired_message'] = 'Session expired'
web.config.session_parameters['httponly'] = False

URLS = (
	'/(acerca)?', 'Estatico',
	'/usuario', 'DatosUsuario',
	'/reglas', 'AdminReglas',
	'/alertas', 'AvisoAlertas',
	'/reglas/S', 'BOE_S',#Interfaz Json
	'/reglas/A', 'BOE_A',#Interfaz Json
	'/reglas/B', 'BOE_B',#Interfaz Json
)
APP = web.application(URLS, globals())

GLOBALS = {}
RENDER = web.template.render(CONF.get('web','tema'),globals=GLOBALS)
RENDER_BASE = web.template.render(CONF.get('web','tema'), base='base',globals=GLOBALS)

application = APP.wsgifunc()

class DefaultWeb:
	DEF__NUM_PAG = 10
	'''
		:keyword user: Listado de usuario y clave
		:type user: dict
		politica: Ver mas informacion en https://www.owasp.org/index.php/Content_Security_Policy
	'''
	def __init__(self, auth=None, politica="default-src 'self'"):
		self.politica = politica
	'''
		Aplicacion de policas de seguridad en las cabezeras.
		Mas infromacion en https://www.owasp.org/index.php/List_of_useful_HTTP_headers
	'''
	def securizar_cabezera(self):
		'''
		web.header('Strict-Transport-Security', 'max-age=60')
		web.header('X-Content-Type-Options', 'nosniff')
		web.header('X-Frame-Options', 'deny')#sameorigin
		web.header('X-XSS-Protection', '1; mode=block')

		if self.politica is not None:
			web.header('X-WebKit-CSP', self.politica)
			web.header('X-Content-Security-Policy', self.politica)
			web.header('Content-Security-Policy', self.politica)
		#'''

	def HEAD(self, *extras):
		raise web.Forbidden()
	def GET(self, *extras):
		self.securizar_cabezera()
	def POST(self, *extras):
		self.securizar_cabezera()
	def PUT(self, *extras):
		raise web.Forbidden()
	def DELETE(self, *extras):
		raise web.Forbidden()
	def TRACE(self, *extras):
		raise web.Forbidden()
	def CONNECT(self, *extras):
		raise web.Forbidden()
	def OPTIONS(self, *extras):
		raise web.Forbidden()

class Estatico(DefaultWeb):
	def GET(self, path=None):
		DefaultWeb.GET(self)
		web.header('Content-Type', 'text/html')
		return RENDER_BASE.acerca()

class DatosUsuario(DefaultWeb):
	@staticmethod
	def get_usuario():
		usuario = Usuario(DB)
		res = usuario.list()
		if res['total'] > 0:
			return res['data'][0]
		else:
			usuario['alert_web']=True
			usuario['alert_email']=False
			usuario['email']=""
			usuario['alert_twitter']=False
			usuario['twitter']=""
			usuario['alert_sms']=False
			usuario['sms']=""
			usuario.save()
		return usuario
	def GET(self, errores=None):
		DefaultWeb.GET(self)
		web.header('Content-Type', 'text/html')
		usuario = DatosUsuario.get_usuario()
		return RENDER_BASE.usuario(usuario, errores)
	def POST(self):
		DefaultWeb.POST(self)
		i = web.input()
		usuario = DatosUsuario.get_usuario()
		if i.get('alert_web'):
			usuario['alert_web']=True
		else:
			usuario['alert_web']=False
		'''
			#TODO validar los datos
			if i.get('alert_email'):
				usuario['alert_email']=True
			else:
				usuario['alert_email']=False
			if i.get('email'):
				usuario['email']=i.get('email')
			if i.get('alert_twitter'):
				usuario['alert_twitter']=True
			else:
				usuario['alert_twitter']=False
			if i.get('twitter'):
				usuario['twitter']=i.get('twitter')
			if i.get('alert_sms'):
				usuario['alert_sms']=True
			else:
				usuario['alert_sms']=False
			if i.get('sms'):
				usuario['sms']=i.get('sms')
		#'''
		return self.GET([])

class AdminReglas(DefaultWeb):
	def GET(self):
		DefaultWeb.GET(self)
		web.header('Content-Type', 'text/html')
		boes = BOE_S()
		boea = BOE_A()
		boeb = BOE_B()
		return RENDER_BASE.reglas(None, boes.GET(), boea.GET(), boeb.GET())
	def POST(self):
		DefaultWeb.GET(self)
		i = web.input()
		if i.has_key('listado'):
			lista = i.get('listado')
			if lista not in ["seccion","departamento","epigrafe","origen_legislativo","materia","alerta"]:
				web.header('Content-Type', 'application/json')
				raise web.NotFound(json.dumps({"error":"listado %s no valido"%i.get('listado')}))
			pc = PalagraClave(DB)
			ret = pc.list(0,{lista:{'$exists': True}},[(lista,1)],200)
			web.header('Content-Type', 'application/json')
			return json.dumps(ret['data'], cls=ComplexEncoder)

from pymongo import ASCENDING, DESCENDING
import re
from datetime import datetime
class ComplexEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, datetime):
			return obj.strftime("%Y/%m/%d")
		elif isinstance(obj, Regla):
			return str(obj)
		elif isinstance(obj, PalagraClave):
			return str(obj)
		elif isinstance(obj, Alertas):
			return [obj['boe'], obj['fecha'], obj['alias']]
		return json.JSONEncoder.default(self, obj)

class TablaBase(DefaultWeb):
	COLUMNAS = [
		#{ 'title':'Texto',		'width':'10%',	'input':'texto',	'type':'text'},
		#{ 'title':'Listado',	'width':'10%',	'select':'lista'}
		#{ 'title':'Columna simple',	'width':'10%' }
	]
	def __init__(self):
		self.json_encoder = ComplexEncoder
	def toDataTables(self, lista, total_filtrado=None):
		if total_filtrado is None:
			total_filtrado = lista['total']
		ret = {
			"sEcho": web.input().get('sEcho'),
			"iTotalRecords": lista['total'],
			"iTotalDisplayRecords": lista['total'],
			"aaData":[]
		}
		ret["aaData"] = lista['data']
		return ret
	def get_list_params(self):
		i = web.input()
		COLUMNAS = []
		for item in self.__class__.COLUMNAS:
			COLUMNAS.append(item['title'])
		tamXpag = 10
		try:
			tamXpag = int(i.get('iDisplayLength'))
		except TypeError:
			pass
		pag = 0
		try:
			pag = int(i.get('iDisplayStart')) / tamXpag
		except TypeError:
			pass
		busqueda = i.get('sSearch')
		sort = []
		if i.get('iSortCol_0'):
			try:
				for j in range( int( i.get('iSortingCols') )):
					try:
						col_pos = int(i.get('iSortCol_%s'%j))
						ord = i.get( 'bSortable_%s'%col_pos )
						if ord == 'true' and col_pos < len(COLUMNAS):
							sentido = DESCENDING
							if i.get('sSortDir_%s'%j)=='asc':
								sentido = ASCENDING
							sort += [ (COLUMNAS[ col_pos ], sentido) ]
					except TypeError:
						continue
			except TypeError:
				pass
		busquedas = {}
		for j in range( len(COLUMNAS) ):
			try:
				buscar = i.get('bSearchable_%s'%j)
				termino = re.escape( i.get('sSearch_%s'%j) )
				if buscar == "true" and termino != '':
					regx = re.compile('.*%s.*'%termino ,re.IGNORECASE)
					busquedas[ COLUMNAS[j] ] = regx
			except:
				pass
		return (pag, busquedas, sort, tamXpag)

class AvisoAlertas(TablaBase):
	COLUMNAS = [
		{ 'title':'boe',	'width':'30%'},
		{ 'title':'fecha',	'width':'20%'},
		{ 'title':'alias',	'width':'40%'}
	]
	def GET(self):
		TablaBase.GET(self)
		return RENDER_BASE.alertas(self.__class__.COLUMNAS)
	def POST(self):
		TablaBase.POST(self)
		i = web.input()
		borrar = i.get('borrar')
		db_obj = Alertas(DB)
		usuario = DatosUsuario.get_usuario()
		web.header('Content-Type', 'application/json')

		if i.get('total'):
			elements = db_obj.list(0, {'usuario':usuario.id}, [], 1)
			return json.dumps({'total':elements['total']})

		borrar = i.get('borrar')
		if borrar is not None:
			elements = db_obj.list(0, {'boe':borrar,'usuario':usuario.id}, [], 1)
			if len(elements['data'])>0:
				elements['data'][0].remove()
				return json.dumps({"ok":"Aviso borrado"})
			raise web.NotFound(json.dumps({"error":"Aviso no encontrado"}))

		(pag, busquedas, sort, tamXpag) = self.get_list_params()
		i = web.input()
		if i.has_key('sSearch'):
			termino = re.escape( i.get('sSearch').strip() )
			if termino != '':
				regx = re.compile('.*%s.*'%termino ,re.IGNORECASE)
				busquedas['$or'] = [{'boe':regx},{'alias':regx}]
		busquedas['usuario'] = usuario.id
		elements = db_obj.list(pag, busquedas, sort, tamXpag)
		return json.dumps(self.toDataTables(elements), cls=self.json_encoder)

class TablaReglasBase(TablaBase):
	def __init__(self, tipo):
		TablaBase.__init__(self)
		self.tipo = tipo
	def valida_datos(self):
		i = web.input()
		post_valido = False
		query = {}
		for fila in self.__class__.COLUMNAS:
			clave = None
			if 'input' in fila:
				clave = fila['input']
			elif 'select' in fila:
				clave = fila['select']
			if clave is not None:
				query[clave] = None
				if clave == "malformado":
					query[clave] = False
				if i.has_key(clave):
					if clave == "malformado":
						query[clave] = True
						continue
					candidata = i.get(clave)
					if candidata is None or len(candidata.strip())==0:
						post_valido = True
					elif clave in ["seccion","departamento","epigrafe","origen_legislativo","materia","alerta"]:
						pc = PalagraClave(DB)
						elements = pc.list(0, {clave:candidata}, [], 1)
						if elements['total'] > 0 and len(elements['data'])>0:
							query[clave] = elements['data'][0]
							post_valido = True
						else:
							raise ValueError('No existe el termino "%s" para el apartado "%s"'%(candidata, clave))
					elif clave.startswith('re_'):
						re.compile(candidata, re.DOTALL|re.IGNORECASE)
						query[clave] = candidata
						post_valido = True
		if post_valido:
			for clave in query:
				if query[clave] != None:
					return query

	def GET(self, titulo, tabla_id):
		TablaBase.GET(self)
		web.header('Content-Type', 'text/html')
		return RENDER.tabla_reglas(titulo, self.__class__.COLUMNAS, tabla_id)
	def POST(self):
		TablaBase.POST(self)
		usuario = DatosUsuario.get_usuario()
		db_obj = Regla(DB)
		borrar = web.input().get('borrar')
		web.header('Content-Type', 'application/json')
		if borrar is not None:
			bid = descifrar_id(borrar, usuario)
			elements = db_obj.list(0, {'_id':bid,'usuario':usuario.id}, [], 1)
			if len(elements['data'])>0:
				if elements['data'][0].id == bid:
					elements['data'][0].remove()
					return json.dumps({"ok":"Elemento borrado"})
			raise web.NotFound(json.dumps({"error":"Regla no encontrada"}))

		(pag, busquedas, sort, tamXpag) = self.get_list_params()
		busquedas['tipo'] = self.tipo
		busquedas['usuario'] = usuario.id
		elements = db_obj.list(pag, busquedas, sort, tamXpag)

		return json.dumps(self.toDataTables(elements), cls=self.json_encoder)

class SEncoder(ComplexEncoder):
	def default(self, obj):
		if isinstance(obj, Regla):
			ret = []
			for fila in BOE_S.COLUMNAS:
				clave = None
				if 'input' in fila:
					clave = fila['input']
				elif 'select' in fila:
					clave = fila['select']
				if clave:
					if clave in ["seccion","departamento","epigrafe","origen_legislativo","materia","alerta"]:
						pc = PalagraClave(DB)
						pc.id = obj[clave]
						ret.append(str(pc))
					else:
						ret.append(obj[clave])
			ret.append(cifrar_id(obj.id, DatosUsuario.get_usuario()))
			return ret
		return ComplexEncoder.default(self, obj)
class BOE_S(TablaReglasBase):
	COLUMNAS = [
		{ 'title':'alias',	'width':'10%',	'input':'alias', 'type':'text'},
		{ 'title':'seccion', 'width':'10%', 'select':'seccion'},
		{ 'title':'departamento', 'width':'10%', 'select':'departamento'},
		{ 'title':'epigrafe', 'width':'10%', 'select':'epigrafe'},
		{ 'title':'titulo', 'width':'10%', 'input':'re_titulo', 'type':'text'}
	]
	def __init__(self):
		TablaReglasBase.__init__(self, 'S')
		self.json_encoder = SEncoder
	def GET(self):
		return TablaReglasBase.GET(self, "Reglas para BOE-S","boe_s")
	def POST(self):
		alias = web.input().get('alias')
		if alias is not None:
			query = self.valida_datos()
			error = False
			if len(alias.strip())==0:
				error = json.dumps({"error":"Debe insertar un alias"})
			elif query:
				db_obj = Regla(DB)
				ret = db_obj.add_rule_S(DatosUsuario.get_usuario(), alias, query['seccion'], query['departamento'], query['epigrafe'], query['re_titulo'])
				self.securizar_cabezera()
				return json.dumps({"ok":"Regla insertada"})
			else:
				error = json.dumps({"error":"Debe insertar mas datos ademas del alias"})
			if error:
				self.securizar_cabezera()
				web.header('Content-Type', 'application/json')
				raise web.NotFound(error)
				return error
		return TablaReglasBase.POST(self)

class AEncoder(ComplexEncoder):
	def default(self, obj):
		if isinstance(obj, Regla):
			ret = []
			for fila in BOE_A.COLUMNAS:
				clave = None
				if 'input' in fila:
					clave = fila['input']
				elif 'select' in fila:
					clave = fila['select']
				if clave:
					if clave in ["seccion","departamento","epigrafe","origen_legislativo","materia","alerta"]:
						pc = PalagraClave(DB)
						pc.id = obj[clave]
						ret.append(str(pc))
					else:
						ret.append(obj[clave])
			ret.append(cifrar_id(obj.id, DatosUsuario.get_usuario()))
			return ret
		return ComplexEncoder.default(self, obj)
class BOE_A(TablaReglasBase):
	COLUMNAS = [
		{ 'title':'alias',	'width':'10%',	'input':'alias', 'type':'text'},
		{ 'title':'malformado',	'width':'10%',	'input':'malformado', 'type':'checkbox'},
		{ 'title':'titulo',	'width':'10%',	'input':'re_titulo', 'type':'text'},
		{ 'title':'departamento',	'width':'10%',	'select':'departamento'},
		{ 'title':'origen_legislativo',	'width':'10%',	'select':'origen_legislativo'},
		{ 'title':'materias',	'width':'10%',	'select':'materia'},
		{ 'title':'alertas',	'width':'10%',	'select':'alerta'},
		{ 'title':'texto',	'width':'10%',	'input':'re_texto', 'type':'text'}
	]
	def __init__(self):
		TablaReglasBase.__init__(self, 'A')
		self.json_encoder = AEncoder
	def GET(self):
		return TablaReglasBase.GET(self, "Reglas para BOE-A","boe_a")
	def POST(self):
		alias = web.input().get('alias')
		if alias is not None:
			query = self.valida_datos()
			error = False
			if len(alias.strip())==0:
				error = json.dumps({"error":"Debe insertar un alias"})
			elif query:
				db_obj = Regla(DB)
				ret = db_obj.add_rule_A(DatosUsuario.get_usuario(), alias, query['malformado'], query['re_titulo'], query['departamento'], query['origen_legislativo'], query['materia'], query['alerta'], query['re_texto'])
				self.securizar_cabezera()
				return json.dumps({"ok":"Regla insertada"})
			else:
				error = json.dumps({"error":"Debe insertar mas datos ademas del alias"})
			if error:
				web.header('Content-Type', 'application/json')
				self.securizar_cabezera()
				raise web.NotFound(error)
				return error
		return TablaReglasBase.POST(self)

class BEncoder(ComplexEncoder):
	def default(self, obj):
		if isinstance(obj, Regla):
			ret = []
			for fila in BOE_B.COLUMNAS:
				clave = None
				if 'input' in fila:
					clave = fila['input']
				elif 'select' in fila:
					clave = fila['select']
				if clave:
					if clave in ["seccion","departamento","epigrafe","origen_legislativo","materia","alerta"]:
						pc = PalagraClave(DB)
						pc.id = obj[clave]
						ret.append(str(pc))
					else:
						ret.append(obj[clave])
			ret.append(cifrar_id(obj.id, DatosUsuario.get_usuario()))
			return ret
		return ComplexEncoder.default(self, obj)
class BOE_B(TablaReglasBase):
	COLUMNAS = [
		{ 'title':'alias',	'width':'10%',	'input':'alias', 'type':'text'},
		{ 'title':'malformado',	'width':'10%',	'input':'malformado', 'type':'checkbox'},
		{ 'title':'titulo',	'width':'10%',	'input':'re_titulo', 'type':'text'},
		{ 'title':'departamento',	'width':'10%',	'select':'departamento'},
		{ 'title':'texto',	'width':'10%',	'input':'re_texto', 'type':'text'}
	]
	def __init__(self):
		TablaReglasBase.__init__(self, 'B')
		self.json_encoder = BEncoder
	def GET(self):
		return TablaReglasBase.GET(self, "Reglas para BOE-B","boe_b")
	def POST(self):
		alias = web.input().get('alias')
		if alias is not None:
			query = self.valida_datos()
			error = False
			if len(alias.strip())==0:
				error = json.dumps({"error":"Debe insertar un alias"})
			elif query:
				db_obj = Regla(DB)
				ret = db_obj.add_rule_B(DatosUsuario.get_usuario(), alias, query['malformado'], query['re_titulo'], query['departamento'], query['re_texto'])

				self.securizar_cabezera()
				return json.dumps({"ok":"Regla insertada"})
			else:
				error = json.dumps({"error":"Debe insertar mas datos ademas del alias"})
			if error:
				web.header('Content-Type', 'application/json')

				self.securizar_cabezera()
				raise web.NotFound(error)
				return error
		return TablaReglasBase.POST(self)


if __name__ == "__main__":
	APP.run()
