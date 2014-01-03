'''
-Si se cambia el mail validar el correo anterior y la clave
-Si se cambia el mail validar que no existe para otro usuario
-Borrar email no validado en una semana

'''
import sys, os, json
abspath = os.path.dirname(__file__)
sys.path.append(abspath)
if abspath!='':
	os.chdir(abspath)

from boe.db import DBConnector, Usuario, PalagraClave, Regla, Alertas
from boe.utils import cargar_conf, FICHERO_CONFIGURACION, gen_random, cifrar_clave, cifrar_id, descifrar_id, valid_email, html2plain
from boe.processing import envia_email
import logging

CONF = cargar_conf(FICHERO_CONFIGURACION)
DB = DBConnector(CONF)

import web
from twython import Twython

def twitter_url():
	if CONF.has_section("twitter"):
		twitter = Twython(CONF.get("twitter", "consumer_key"), CONF.get("twitter", "consumer_secret"))
		auth = twitter.get_authentication_tokens(callback_url="http://%s/usuario"%(web.ctx.host))
		SESSION.twitter_token = auth['oauth_token']
		SESSION.twitter_token_secret = auth['oauth_token_secret']
		return auth['auth_url']
	return ""

if CONF.has_option("web", "cookie_name"):
	web.config.session_parameters['cookie_name'] = CONF.get("web", "cookie_name")
if CONF.has_option("web", "cookie_domain"):
	web.config.session_parameters['cookie_domain'] = CONF.get("web", "cookie_domain")
if CONF.has_option("web", "cookie_salt"):
	web.config.session_parameters['secret_key'] = CONF.get("web", "cookie_salt")
web.config.session_parameters['timeout'] = 24 * 60 * 60 # 24 hours in seconds
web.config.session_parameters['ignore_expiry'] = False
web.config.session_parameters['ignore_change_ip'] = False
web.config.session_parameters['httponly'] = False
web.config.session_parameters['expired_message'] = 'Sesion expirada'

web.config.debug = CONF.getboolean("web", "debug")

URLS = (
	'/(acerca)?', 'Estatico',
	'/usuario', 'DatosUsuario',
	'/reglas', 'AdminReglas',
	'/alertas', 'AvisoAlertas',
	'/reglas/rapidas', 'ReglasRapidas',#Interfaz Json
	'/reglas/S', 'BOE_S',#Interfaz Json
	'/reglas/A', 'BOE_A',#Interfaz Json
	'/reglas/B', 'BOE_B',#Interfaz Json
)

APP = web.application(URLS, globals())

SESSION = web.session.Session(APP, web.session.DiskStore(CONF.get("web", "cookie_dir")), initializer={'login': None, 'cifrado':None})

def genClave(forcegen=False):
	clave = gen_random()
	if forcegen or not 'cifrado' in SESSION or SESSION.cifrado is None:
		SESSION.cifrado = clave
	else:
		clave = SESSION.cifrado
		SESSION.cifrado = None
	return clave

GLOBALS = {'clave_cifrado':genClave, 'twitter_url':twitter_url}
RENDER = web.template.render(CONF.get('web','tema'),globals=GLOBALS)
RENDER_BASE = web.template.render(CONF.get('web','tema'), base='base',globals=GLOBALS)

application = APP.wsgifunc()

def get_usuario():
	usuario = Usuario(DB)
	usuario.id = SESSION.login
	return usuario

class DefaultWeb:
	DEF__NUM_PAG = 10
	'''
		:keyword user: Listado de usuario y clave
		:type user: dict
		politica: Ver mas informacion en https://www.owasp.org/index.php/Content_Security_Policy
	'''
	def __init__(self, auth=None, politica="default-src 'self'"):
		self.politica = politica
		self.usuario = None
		self.auth = auth
	'''
		Aplicacion de policas de seguridad en las cabezeras.
		Mas infromacion en https://www.owasp.org/index.php/List_of_useful_HTTP_headers
	'''
	def securizar_cabezera(self):
		if self.auth:
			self.check_auth()
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
	def check_auth(self):
		if not CONF.getboolean('web','multilogin'):
			res = Usuario(DB).list(0,{},[],1)
			if res['total'] > 0:
				self.usuario = res['data'][0]
				SESSION.login = self.usuario.id
			else:
				self.usuario = Usuario(DB)
				self.usuario['alert_web']=True
				self.usuario['cifrado'] = gen_random()
				self.usuario.save()

		if not 'login' in SESSION or SESSION.login is None:
			raise web.seeother('/usuario?login')
		res = Usuario(DB).list(0,{'_id':SESSION.login},[],1)
		if res['total'] > 0:
			self.usuario = res['data'][0]
		else:
			SESSION.login = None
	def do_auth(self):
		i = web.input()
		email = i.get('email')
		if not valid_email(email):
			return False
		clave = cifrar_clave(i.get('clave'), email)
		SESSION.login = None
		usuario = Usuario(DB)
		res = usuario.list(0,{'email':email},[],1)
		if res['total'] > 0:
			usuario = res['data'][0]
			if usuario['clave'] == clave:
				SESSION.login = usuario.id
		elif False:#TODO Auto registro
			usuario['email'] = email
			usuario['clave'] = clave
			usuario['email_valido'] = False
			usuario['cifrado'] = gen_random()
			usuario.save()
			SESSION.login = usuario.id
		return usuario.id is not None

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
		return RENDER_BASE.acerca( open('README.md','r').read() )

class DatosUsuario(DefaultWeb):
	def GET(self, errores=None):
		DefaultWeb.GET(self)
		web.header('Content-Type', 'text/html')
		i = web.input()
		usuario = Usuario(DB)
		if i.has_key('logout'):
			SESSION.login = None
			try:
				SESSION.kill()
			except:
				pass
		elif i.has_key('login'):
			return RENDER_BASE.login(None)
		elif i.has_key('oauth_verifier'):
			if CONF.has_section("twitter") and 'twitter_token' in SESSION and 'twitter_token_secret' in SESSION:
				twitter = Twython(CONF.get("twitter", "consumer_key"), CONF.get("twitter", "consumer_secret"), SESSION.twitter_token, SESSION.twitter_token_secret)
				final_step = twitter.get_authorized_tokens(i.get('oauth_verifier'))
				if 'oauth_token_secret' in final_step and 'oauth_token' in final_step:
					SESSION.twitter_token = final_step['oauth_token']
					SESSION.twitter_token_secret = final_step['oauth_token_secret']

					twitter = Twython(CONF.get("twitter", "consumer_key"), CONF.get("twitter", "consumer_secret"), SESSION.twitter_token, SESSION.twitter_token_secret)
					response = twitter.verify_credentials()
					if 'id' in response and 'screen_name' in response:
						res = usuario.list(0,{'$or':[{'twitter_id':response["id"]},{'twitter':response["screen_name"]}]},[],1)
						if res['total'] > 0:
							usuario = res['data'][0]
						elif 'login' in SESSION and SESSION.loggin:
							res = usuario.list(0,{'_id':SESSION.loggin},[],1)
							if res['total'] > 0:
								usuario = res['data'][0]
								usuario['twitter'] = response["screen_name"]
								usuario['twitter_id'] = response["id"]
						else:
							usuario['twitter'] = response["screen_name"]
							usuario['twitter_id'] = response["id"]
							usuario['cifrado'] = gen_random()
							usuario.save()
							SESSION.login = usuario.id
						raise web.seeother('/usuario')
		elif i.has_key('validar'):
			email_key = i.get('key')
			lista = usuario.list(0,{'email':i.get('validar'), 'email_key': email_key},[],1)
			if lista['total'] <= 0:
				raise web.NotFound( RENDER_BASE.error("email no validado") )
			usuario = lista['data'][0]
			usuario['email_valido'] = True
			SESSION.login = usuario.id

		self.check_auth()
		if self.usuario['email'] is not None and self.usuario['email'] != '' and not self.usuario['email_valido']:
			if errores is None:
				errores = []
			errores.append('email no validado')

		return RENDER_BASE.usuario(self.usuario, errores)
	def send_valid_mail(self):
		self.usuario['email_valido'] = False
		self.usuario['email_key'] = gen_random()
		email_key = self.usuario['email_key']
		url = "http://%s/usuario?validar=%s&key=%s" % (web.ctx.host, self.usuario['email'], email_key)
		html = str( RENDER.validar_email(url, web.ctx.ip) )
		plain = html2plain(html)
		if CONF.getboolean("celery", "activo"):
			envia_email.apply_async(kwargs={'correo':self.usuario['email'], 'subject':"Validar email", 'plain':plain, 'html':html})
		else:
			envia_email(self.usuario['email'], "Validar email", plain, html)
	def POST(self):
		DefaultWeb.POST(self)
		i = web.input()
		if i.has_key('login'):
			cifrado = genClave()
			if i.get('cifrado') != cifrado:
				return RENDER_BASE.login('Validacion fallida')
			if not self.do_auth():
				return RENDER_BASE.login('Usuario o Clave erroneos')

		self.check_auth()
		if i.get('alert_web'):
			self.usuario['alert_web']=True
		else:
			self.usuario['alert_web']=False

		if i.get('alert_twitter'):
			self.usuario['alert_twitter']=True
		else:
			self.usuario['alert_twitter']=False

		if i.get('email'):
			if i.get('email') == "":
				self.usuario['email']=None
			elif i.get('revalidar') and self.usuario['email'] == i.get('email'):
				self.send_valid_mail()
			elif self.usuario['email'] != i.get('email'):
				lista = self.usuario.list(0,{'email':i.get('email')},[],1)
				if lista['total'] > 0:
					return self.GET(["email ya registrado"])
				if not valid_email(i.get('email')):
					return self.GET(["email no valido"])
				#TODO Enviar verificacion al antiguo email
				self.usuario['email'] = i.get('email')
				self.send_valid_mail()


		if i.get('alert_email'):
			self.usuario['alert_email']=True
			if not valid_email(self.usuario['email']):
				return self.GET(["email no valido"])
		else:
			self.usuario['alert_email']=False

		'''
			#TODO validar los datos
			if i.get('alert_sms'):
				usuario['alert_sms']=True
			else:
				usuario['alert_sms']=False
			if i.get('sms'):
				usuario['sms']=i.get('sms')
		#'''
		return self.GET([])

class AdminReglas(DefaultWeb):
	def __init__(self):
		DefaultWeb.__init__(self, True)
	def GET(self):
		DefaultWeb.GET(self)
		web.header('Content-Type', 'text/html')
		rapidas = ReglasRapidas()
		boes = BOE_S()
		boea = BOE_A()
		boeb = BOE_B()
		return RENDER_BASE.reglas(None, rapidas.GET(), boes.GET(), boea.GET(), boeb.GET())
	def POST(self):
		DefaultWeb.GET(self)
		i = web.input()
		if i.has_key('listado'):
			lista = i.get('listado')
			if lista not in ["seccion","departamento","epigrafe","origen_legislativo","materia","alerta","materias_cpv"]:
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
		DefaultWeb.__init__(self, True)
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
		web.header('Content-Type', 'application/json')

		if i.get('total'):
			elements = db_obj.list(0, {'usuario':self.usuario.id}, [], 1)
			return json.dumps({'total':elements['total']})

		borrar = i.get('borrar')
		if borrar is not None:
			elements = db_obj.list(0, {'boe':borrar,'usuario':self.usuario.id}, [], 1)
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
		busquedas['usuario'] = self.usuario.id
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
					elif clave in ["seccion","departamento","epigrafe","origen_legislativo","materia","alerta","materias_cpv"]:
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
		db_obj = Regla(DB)
		borrar = web.input().get('borrar')
		web.header('Content-Type', 'application/json')
		if borrar is not None:
			bid = descifrar_id(borrar, self.usuario)
			elements = db_obj.list(0, {'_id':bid,'usuario':self.usuario.id}, [], 1)
			if len(elements['data'])>0:
				if elements['data'][0].id == bid:
					elements['data'][0].remove()
					return json.dumps({"ok":"Elemento borrado"})
			raise web.NotFound(json.dumps({"error":"Regla no encontrada"}))

		(pag, busquedas, sort, tamXpag) = self.get_list_params()
		busquedas['tipo'] = self.tipo
		busquedas['usuario'] = self.usuario.id
		elements = db_obj.list(pag, busquedas, sort, tamXpag)

		return json.dumps(self.toDataTables(elements), cls=self.json_encoder)

class RapidasEncoder(ComplexEncoder):
	def default(self, obj):
		if isinstance(obj, Regla):
			ret = []
			for fila in ReglasRapidas.COLUMNAS:
				ret.append(obj[ fila['input'] ])
			ret.append(cifrar_id(obj.id, get_usuario()))
			return ret
		return ComplexEncoder.default(self, obj)
class ReglasRapidas(TablaReglasBase):
	COLUMNAS = [
		{ 'title':'alias',	'width':'10%',	'input':'alias', 'type':'text'},
		{ 'title':'expresion regular', 'width':'10%', 'input':'re_expre', 'type':'text'}
	]
	def __init__(self):
		TablaReglasBase.__init__(self, 'rapida')
		self.json_encoder = RapidasEncoder
	def GET(self):
		return TablaReglasBase.GET(self, "Reglas rapidas","reglas_rapidas")
	def POST(self):
		self.securizar_cabezera()
		alias = web.input().get('alias')
		if alias is not None:
			query = self.valida_datos()
			error = False
			if len(alias.strip())==0:
				error = json.dumps({"error":"Debe insertar un alias"})
			elif query:
				db_obj = Regla(DB)
				ret = db_obj.add_rule_S(self.usuario, alias, None, None, None, query['re_expre'])
				ret = db_obj.add_rule_A(self.usuario, alias, False, query['re_expre'], None, None, None, None, None)
				ret = db_obj.add_rule_A(self.usuario, alias, False, None, None, None, None, None, query['re_expre'])
				ret = db_obj.add_rule_B(self.usuario, alias, False, query['re_expre'], None, None, None)
				ret = db_obj.add_rule_B(self.usuario, alias, False, None, None, None, query['re_expre'])

				db_obj = Regla(DB)
				db_obj['usuario'] = self.usuario.id
				db_obj['alias'] = alias
				db_obj['tipo'] = 'rapida'
				db_obj['re_expre'] = query['re_expre']
				db_obj.save()
				return json.dumps({"ok":"Regla insertada"})
			else:
				error = json.dumps({"error":"Debe insertar mas datos ademas del alias"})
			if error:
				web.header('Content-Type', 'application/json')
				raise web.NotFound(error)
				return error
		borrar = web.input().get('borrar')
		if borrar is not None:
			bid = descifrar_id(borrar, self.usuario)
			db_obj = Regla(DB)
			elements = db_obj.list(0, {'_id':bid,'usuario':self.usuario.id}, [], 1)
			if len(elements['data'])>0:
				if elements['data'][0].id == bid:
					alias = elements['data'][0]['alias']
					re_expre = elements['data'][0]['re_expre']
					rem_elem = db_obj.list(0, {'usuario':self.usuario.id,'alias':alias,'$or':[{'re_texto':re_expre},{'re_titulo':re_expre}]}, [], 10)
					for elem in rem_elem['data']:
						elem.remove()
			else:
				web.header('Content-Type', 'application/json')
				raise web.NotFound(json.dumps({"error":"Regla no encontrada"}))
		return TablaReglasBase.POST(self)

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
			ret.append(cifrar_id(obj.id, get_usuario()))
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
			self.securizar_cabezera()
			query = self.valida_datos()
			error = False
			if len(alias.strip())==0:
				error = json.dumps({"error":"Debe insertar un alias"})
			elif query:
				db_obj = Regla(DB)
				ret = db_obj.add_rule_S(self.usuario, alias, query['seccion'], query['departamento'], query['epigrafe'], query['re_titulo'])
				return json.dumps({"ok":"Regla insertada"})
			else:
				error = json.dumps({"error":"Debe insertar mas datos ademas del alias"})
			if error:
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
			ret.append(cifrar_id(obj.id, get_usuario()))
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
			self.securizar_cabezera()
			query = self.valida_datos()
			error = False
			if len(alias.strip())==0:
				error = json.dumps({"error":"Debe insertar un alias"})
			elif query:
				db_obj = Regla(DB)
				ret = db_obj.add_rule_A(self.usuario, alias, query['malformado'], query['re_titulo'], query['departamento'], query['origen_legislativo'], query['materia'], query['alerta'], query['re_texto'])
				return json.dumps({"ok":"Regla insertada"})
			else:
				error = json.dumps({"error":"Debe insertar mas datos ademas del alias"})
			if error:
				web.header('Content-Type', 'application/json')
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
					if clave in ["departamento","materias_cpv"]:
						pc = PalagraClave(DB)
						pc.id = obj[clave]
						ret.append(str(pc))
					else:
						ret.append(obj[clave])
			ret.append(cifrar_id(obj.id, get_usuario()))
			return ret
		return ComplexEncoder.default(self, obj)
class BOE_B(TablaReglasBase):
	COLUMNAS = [
		{ 'title':'alias',	'width':'10%',	'input':'alias', 'type':'text'},
		{ 'title':'malformado',	'width':'10%',	'input':'malformado', 'type':'checkbox'},
		{ 'title':'titulo',	'width':'10%',	'input':'re_titulo', 'type':'text'},
		{ 'title':'departamento',	'width':'10%',	'select':'departamento'},
		{ 'title':'materias',	'width':'10%',	'select':'materias_cpv'},
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
			self.securizar_cabezera()
			query = self.valida_datos()
			error = False
			if len(alias.strip())==0:
				error = json.dumps({"error":"Debe insertar un alias"})
			elif query:
				db_obj = Regla(DB)
				ret = db_obj.add_rule_B(self.usuario, alias, query['malformado'], query['re_titulo'], query['departamento'], query['materias_cpv'], query['re_texto'])
				return json.dumps({"ok":"Regla insertada"})
			else:
				error = json.dumps({"error":"Debe insertar mas datos ademas del alias"})
			if error:
				web.header('Content-Type', 'application/json')
				raise web.NotFound(error)
				return error
		return TablaReglasBase.POST(self)


if __name__ == "__main__":
	APP.run()
