'''

'''
import logging, httplib

def get_attr(attrs, key):
	for (k,v) in attrs:
		if k == key:
			return v
	return None
def wget(host, path, cabezera={}, tipo="GET", post=None):
	logging.debug("%s%s %s"%(host, path, cabezera))
	conn = httplib.HTTPConnection(host)
	conn.request(tipo, path, post, cabezera)
	res = conn.getresponse()
	estado = res.status
	cabezeras = res.getheaders()
	content_type = get_attr(cabezeras, 'content-type')

	def_encode = 'latin_1'
	if content_type:
		init = content_type.find('charset=')
		if init > -1:
			init += len('charset=')
			def_encode = content_type[init:]
			#logging.debug("Detectado encode: %s"%(def_encode))

	contenido = res.read()
	conn.close()
	contenido = eval("u"+repr(contenido))
	contenido = contenido.encode(def_encode)
	return (contenido, cabezeras, estado)

import urlparse
def wget_url(url, cabezera={}, tipo="GET", post=None):
	url = urlparse.urlparse(url)
	dominio = url.netloc
	if url.hostname:
		dominio = url.hostname
	if url.port:
		dominio += ":"+str(url.port)
	path = "/"
	if url.path:
		path = url.path
	if url.query:
		path += "?"+url.query
	if url.fragment:
		path += "#"+url.fragment
	return wget(dominio, path, cabezera, tipo, post)

from utilidades import cargar_conf
CONF = cargar_conf()
import basededatos
DB = basededatos.DBConnector(CONF)

from celery import task
@task
def envia_alerta(aviso):
	logging.info("Notificar a %s sobre '%s' en el BOE: %s"%(aviso['usuario'], aviso['alias'], aviso['boe']))

@task
def procesa_boe(id, rapido=False):
	url = "http://boe.es/diario_boe/xml.php?id=%s"%id
	(contenido, headers, estado) = wget_url(url)
	if estado != httplib.OK:
		#TODO Notificar como malformado?
		logging.error("Error %s al acceder al BOE: %s"%(estado, id))
		return
	p = None
	if id.startswith('BOE-A'):
		if rapido:
			reglas = basededatos.Regla(DB)
			reglas.list(0,{'tipo':'A'},[],1)
			if reglas['total'] == 0:
				return
		p = BoeAParser(id)
	elif id.startswith('BOE-B'):
		if rapido:
			reglas = basededatos.Regla(DB)
			reglas.list(0,{'tipo':'B'},[],1)
			if reglas['total'] == 0:
				return
		p = BoeBParser(id)
	elif id.startswith('BOE-S'):
		if rapido:
			reglas = basededatos.Regla(DB)
			reglas.list(0,{'$or':[{'tipo':'S'},{'tipo':'A'},{'tipo':'B'}]},[],1)
			if reglas['total'] == 0:
				return
		p = BoeSParser(id)
	if p is None:
		raise ValueError("Id '%s' no soportado"%id)
	p.feed(contenido)
	if isinstance(p, BoeSParser):
		logging.info("Hoy hay un total de %s BOES para procesar"%(len(p.boes)))
		for boe_id in p.boes:
			#procesa_boe.apply_async([boe_id, rapido])#Celery
			procesa_boe(boe_id, rapido)

from HTMLParser import HTMLParser
from datetime import datetime
import re
class BoeDiaParser(HTMLParser):
	URL_DATE_FORMAT = "http://boe.es/boe/dias/%Y/%m/%d/"

	@staticmethod
	def has_attr(attrs, key, value=None):
		v = get_attr(attrs, key)
		if v is not None and (value is None or v == value):
			return True
		return False

	def __init__(self, dt_dia=None):
		HTMLParser.__init__(self)
		self.en_link = False
		self.boe_id = None
		if dt_dia is None:
			dt_dia = datetime.now()
		url = dt_dia.strftime(BoeDiaParser.URL_DATE_FORMAT)
		(contenido, headers, estado) = wget_url(url)

		if estado != httplib.OK:
			logging.info("Respuesta %s Cabezeras %s"%(estado, headers))
			raise ValueError("dt_dia debe se un dia con algun BOE publicado")
		self.feed(contenido.decode('utf-8', 'replace'))
	def handle_starttag(self, tag, attrs):
		if tag == 'li' and BoeDiaParser.has_attr(attrs, "class", "puntoXML"):
			self.en_link = True
		elif self.en_link and tag == 'a':
			href_xml = get_attr(attrs, 'href')
			self.boe_id = href_xml[href_xml.rfind("=")+1:]
	def handle_endtag(self, tag):
		if self.en_link and (tag == 'li' or tag == 'a'):
			self.en_link = False

from xml.parsers.expat import ParserCreate
class BasicParser():
	def __init__(self, boe):
		self.boe = boe
		self.en_titulo = False
		self.titulo = ""
		self.p = ParserCreate()
		self.p.StartElementHandler = self.handle_starttag
		self.p.EndElementHandler = self.handle_endtag
		self.p.CharacterDataHandler = self.handle_data
		self.re_cache = {}
		self.tipo = None
		self.claves = ["re_titulo","departamento"]
	def feed(self, contenido):
		self.p.Parse(contenido)
	def alert(self, regla):
		avisos = basededatos.Avisos(DB)
		av = avisos.add(regla, self.boe)
		if not 'enviado' in av or not av['enviado']:
			envia_alerta(av)
			#alert.apply_async([elem['usuario'], self.boe])#Celery
	def alertAll(self, query):
		if self.tipo:
			query['tipo'] = self.tipo
		for clave in self.claves:
			if not clave in query:
				query[clave] = {'$exists':False}

		reglas = basededatos.Regla(DB)
		encontradas = {'total':1}
		pag = 0
		while encontradas['total']>pag:
			encontradas = reglas.list(pag, query,[],10)
			for elem in encontradas['data']:
				self.alert(elem)
			pag += 1
	def alertTitulo(self, query):
		self.alertRe(query, self.titulo, 'titulo')
	def alertRe(self, query, paja, cache='titulo'):
		if self.tipo:
			query['tipo'] = self.tipo
		query['re_'+cache] = {'$exists':True}
		for clave in self.claves:
			if not clave in query:
				query[clave] = {'$exists':False}

		reglas = basededatos.Regla(DB)
		encontradas = {'total':1}
		pag = 0
		while encontradas['total']>pag:
			encontradas = reglas.list(pag, query,[],10)
			for elem in encontradas['data']:
				tre = elem['re_'+cache]
				s = False
				m = False
				if cache and cache in self.re_cache and tre in self.re_cache[cache]:
					s = self.re_cache[cache][tre]['search']
					m = self.re_cache[cache][tre]['match']
				if s is False and m is False:
					tre = re.compile(elem['re_'+cache])
					s = tre.search(paja)
					m = tre.match(paja)
					if cache and cache in self.re_cache:
						self.re_cache[cache][tre] = { 'search':s, 'match':m }
				if s is not None or m is not None:
					logging.debug("search %s"%s)
					logging.debug("match %s"%m)
					self.alert(elem)
			pag += 1
	def handle_starttag(self, tag, attrs):
		pass
	def handle_endtag(self, tag):
		pass
	def handle_data(self, data):
		pass

class BoeSParser(BasicParser):
	def __init__(self, boe):
		BasicParser.__init__(self, boe)
		self.act_sec = basededatos.PalagraClave(DB)
		self.act_dep = basededatos.PalagraClave(DB)
		self.act_epi = basededatos.PalagraClave(DB)
		self.malformado = False
		self.boes = []
		self.tipo = 'S'
		self.claves = ["seccion","departamento","epigrafe","re_titulo"]
	def handle_starttag(self, tag, attrs):
		if tag in ['seccion','departamento','epigrafe']:
			valor = attrs['nombre'].strip()
			if tag == 'seccion':
				self.act_sec[tag] = valor
				if self.act_sec.id:
					self.alertAll({'seccion':self.act_sec.id})
			elif tag == 'departamento':
				self.act_dep[tag] = valor
				if self.act_dep.id:
					self.alertAll({'departamento':self.act_dep.id})
					if self.act_sec.id:
						self.alertAll({'seccion':self.act_sec.id,'departamento':self.act_dep.id})
			elif tag == 'epigrafe':
				self.act_epi[tag] = valor
				if self.act_epi.id:
					self.alertAll({'epigrafe':self.act_epi.id})
					if self.act_dep.id:
						self.alertAll({'departamento':self.act_dep.id,'epigrafe':self.act_epi.id})
						if self.act_sec.id:
							self.alertAll({'seccion':self.act_sec.id,'departamento':self.act_dep.id,'epigrafe':self.act_epi.id})
					if self.act_sec.id:
						self.alertAll({'seccion':self.act_sec.id,'epigrafe':self.act_epi.id})
		elif tag == 'item':
			self.boes.append( attrs['id'] )
		elif tag == 'titulo':
			self.en_titulo = True
	def handle_endtag(self, tag):
		if tag == 'seccion':
			self.act_sec.id = None
		elif tag == 'departamento':
			self.act_dep.id = None
		elif tag == 'epigrafe':
			self.act_epi.id = None
		elif tag == 'titulo':
			self.alertTitulo({})
			if self.act_epi.id:
				self.alertTitulo({'epigrafe':self.act_epi.id})
				if self.act_dep.id:
					self.alertTitulo({'departamento':self.act_dep.id,'epigrafe':self.act_epi.id})
					if self.act_sec.id:
						self.alertTitulo({'seccion':self.act_sec.id,'departamento':self.act_dep.id,'epigrafe':self.act_epi.id})
				if self.act_sec.id:
					self.alertTitulo({'seccion':self.act_sec.id,'epigrafe':self.act_epi.id})
			if self.act_dep.id:
				self.alertTitulo({'departamento':self.act_dep.id})
				if self.act_sec.id:
					self.alertTitulo({'seccion':self.act_sec.id,'departamento':self.act_dep.id})
			if self.act_sec.id:
				self.alertTitulo({'seccion':self.act_sec.id})
			self.titulo = ""
			self.en_titulo = False
			self.malformado = False
		elif self.en_titulo and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		if self.en_titulo:
			self.titulo += data

class BoeTexto(BasicParser):
	def __init__(self, boe):
		BasicParser.__init__(self, boe)
		self.en_texto = False
		self.texto = ""
		self.re_cache['titulo'] = {}
		self.re_cache['texto'] = {}
	def alertTitulo(self, query):
		BasicParser.alertRe(self, query, self.titulo, 'titulo')
	def alertTexto(self, query):
		self.alertRe(query, self.texto, 'texto')
	def alertTT(self, query):
		if self.tipo:
			query['tipo'] = self.tipo
		query['re_texto'] = {'$exists':True}
		query['re_titulo'] = {'$exists':True}

		reglas = basededatos.Regla(DB)
		encontradas = {'total':1}
		pag = 0
		while encontradas['total']>pag:
			encontradas = reglas.list(pag, query,[],10)
			for elem in encontradas['data']:
				tire = elem['re_titulo']
				tis = False
				tim = False
				if tire in self.re_cache['titulo']:
					tis = self.re_cache['titulo'][tire]['search']
					tim = self.re_cache['titulo'][tire]['match']
				if tis is False and tim is False:
					tre = re.compile(tire)
					tis = tre.search(self.titulo)
					tim = tre.match(self.titulo)
					if cache:
						self.re_cache['titulo'][tire] = { 'search':tis, 'match':tim }

				tore = elem['re_texto']
				tos = False
				tom = False
				if tore in self.re_cache['texto']:
					tos = self.re_cache['texto'][tore]['search']
					tom = self.re_cache['texto'][tore]['match']
				if tos is False and tom is False:
					tre = re.compile(tire)
					tos = tre.search(self.texto)
					tom = tre.match(self.texto)
					if cache:
						self.re_cache['titulo'][tore] = { 'search':tos, 'match':tom }
				if tis is not None and tos:
					logging.debug("search Titulo: %s Texto: %s"%(tis, tos))
					self.alert(elem)
				if tim is not None and tom:
					logging.debug("match Titulo: %s Texto: %s"%(tim, tom))
					self.alert(elem)
			pag += 1

class BoeAParser(BoeTexto):
	def __init__(self, boe):
		BoeTexto.__init__(self, boe)
		self.departamento = basededatos.PalagraClave(DB)
		self.en_departamento = False
		self.origen_legislativo = basededatos.PalagraClave(DB)
		self.en_origen_legislativo = False
		self.materias = []
		self.en_materia = False
		self.alertas = []
		self.en_alerta = False

		self.malformado = False
		self.tipo = 'A'
		self.claves = ["departamento","origen_legislativo","materia","alerta","re_texto","seccion","re_titulo"]
	def feed(self, contenido):
		BasicParser.feed(self, contenido)
		if self.departamento.id:
			self.alertTitulo({'departamento':self.departamento.id,'malformado':False})
			self.alertTexto({'departamento':self.departamento.id,'malformado':False})
			self.alertTT({'departamento':self.departamento.id,'malformado':False})

		if self.origen_legislativo.id:
			self.alertTitulo({'origen_legislativo':self.origen_legislativo.id,'malformado':False})
			self.alertTexto({'departamento':{'$exists':False},'origen_legislativo':self.origen_legislativo.id,'materia':{'$exists':False},'alerta':{'$exists':False},'re_titulo':{'$exists':False},'malformado':False})
			self.alertTT({'departamento':{'$exists':False},'origen_legislativo':self.origen_legislativo.id,'materia':{'$exists':False},'alerta':{'$exists':False},'malformado':False})
			if self.departamento.id:
				self.alertTitulo({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$exists':False},'alerta':{'$exists':False},'re_texto':{'$exists':False},'malformado':False})
				self.alertTexto({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$exists':False},'alerta':{'$exists':False},'re_titulo':{'$exists':False},'malformado':False})
				self.alertTT({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$exists':False},'alerta':{'$exists':False},'malformado':False})

		if len(self.materias)>0:
			self.alertAll({'materia':{'$in':self.materias},'malformado':False})
			self.alertTitulo({'materia':{'$in':self.materias},'malformado':False})
			self.alertTexto({'materia':{'$in':self.materias},'malformado':False})
			self.alertTT({'materia':{'$in':self.materias},'malformado':False})

			if self.origen_legislativo.id:
				self.alertTitulo({'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
				self.alertTexto({'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
				self.alertTT({'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
				if self.departamento.id:
					self.alertTitulo({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
					self.alertTexto({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
					self.alertTT({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})

		if len(self.alertas)>0:
			self.alertAll({'alerta':{'$in':self.alertas},'malformado':False})
			self.alertTitulo({'alerta':{'$in':self.alertas},'malformado':False})
			self.alertTexto({'alerta':{'$in':self.alertas},'malformado':False})
			self.alertTT({'alerta':{'$in':self.alertas},'malformado':False})
			if len(self.materias)>0:
				self.alertAll({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':False})
				self.alertTitulo({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':False})
				self.alertTexto({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':False})
				self.alertTT({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':False})

				if self.origen_legislativo.id:
					self.alertTitulo({'alerta':{'$in':self.alertas},'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
					self.alertTexto({'alerta':{'$in':self.alertas},'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
					self.alertTT({'alerta':{'$in':self.alertas},'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
					if self.departamento.id:
						self.alertTitulo({'alerta':{'$in':self.alertas},'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
						self.alertTexto({'alerta':{'$in':self.alertas},'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})
						self.alertTT({'alerta':{'$in':self.alertas},'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':False})

		if self.malformado:
			self.alertAll({'malformado':True})
			self.alertTitulo({'malformado':True})
			self.alertTexto({'malformado':True})
			self.alertTT({'malformado':True})

			if self.departamento.id:
				self.alertAll({'departamento':self.departamento.id,'malformado':True})
				self.alertTitulo({'departamento':self.departamento.id,'malformado':True})
				self.alertTexto({'departamento':self.departamento.id,'malformado':True})
				self.alertTT({'departamento':self.departamento.id,'malformado':True})
			if self.origen_legislativo.id:
				self.alertAll({'origen_legislativo':self.origen_legislativo.id,'malformado':True})
				self.alertTitulo({'origen_legislativo':self.origen_legislativo.id,'malformado':True})
				self.alertTexto({'origen_legislativo':self.origen_legislativo.id,'malformado':True})
				self.alertTT({'origen_legislativo':self.origen_legislativo.id,'malformado':True})
				if self.departamento.id:
					self.alertTitulo({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'malformado':True})
					self.alertTexto({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'malformado':True})
					self.alertTT({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'malformado':True})

			if len(self.materias)>0:
				self.alertAll({'materia':{'$in':self.materias},'malformado':True})
				self.alertTitulo({'materia':{'$in':self.materias},'malformado':True})
				self.alertTexto({'materia':{'$in':self.materias},'malformado':True})
				self.alertTT({'materia':{'$in':self.materias},'malformado':True})

				if self.origen_legislativo.id:
					self.alertTitulo({'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
					self.alertTexto({'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
					self.alertTT({'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
					if self.departamento.id:
						self.alertTitulo({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
						self.alertTexto({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
						self.alertTT({'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})

			if len(self.alertas)>0:
				self.alertAll({'alerta':{'$in':self.alertas},'malformado':True})
				self.alertTitulo({'alerta':{'$in':self.alertas},'malformado':True})
				self.alertTexto({'alerta':{'$in':self.alertas},'malformado':True})
				self.alertTT({'alerta':{'$in':self.alertas},'malformado':True})
				if len(self.materias)>0:
					self.alertAll({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':True})
					self.alertTitulo({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':True})
					self.alertTexto({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':True})
					self.alertTT({'alerta':{'$in':self.alertas},'materia':{'$in':self.materias},'malformado':True})

					if self.origen_legislativo.id:
						self.alertTitulo({'alerta':{'$in':self.alertas},'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
						self.alertTexto({'alerta':{'$in':self.alertas},'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
						self.alertTT({'alerta':{'$in':self.alertas},'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
						if self.departamento.id:
							self.alertTitulo({'alerta':{'$in':self.alertas},'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
							self.alertTexto({'alerta':{'$in':self.alertas},'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})
							self.alertTT({'alerta':{'$in':self.alertas},'departamento':self.departamento.id,'origen_legislativo':self.origen_legislativo.id,'materia':{'$in':self.materias},'malformado':True})

	def handle_starttag(self, tag, attrs):
		if tag == 'departamento':
			self.en_departamento = True
		elif tag == 'origen_legislativo':
			self.en_origen_legislativo = True
		elif tag == 'materia':
			self.en_materia = True
		elif tag == 'alerta':
			self.en_alerta = True
		elif tag == 'texto':
			self.en_texto = True
		elif tag == 'titulo':
			self.en_titulo = True
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_endtag(self, tag):
		if tag == 'departamento':
			self.en_departamento = False
			if self.departamento.id:
				self.alertAll({'departamento':self.departamento.id,'malformado':False})
		elif tag == 'origen_legislativo':
			self.en_origen_legislativo = False
			if self.origen_legislativo.id:
				self.alertAll({'origen_legislativo':self.origen_legislativo.id,'malformado':False})
		elif tag == 'materia':
			self.en_materia = False
		elif tag == 'alerta':
			self.en_alerta = False
		elif tag == 'texto':
			self.en_texto = False
			self.alertTexto({'malformado':False})
		elif tag == 'titulo':
			self.en_titulo = False
			self.alertTitulo({'malformado':False})
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		if self.en_departamento:
			self.departamento['departamento'] = data.strip()
			self.en_departamento = False
		elif self.en_origen_legislativo:
			self.origen_legislativo['origen_legislativo'] = data.strip()
			self.en_origen_legislativo = False
		elif self.en_materia:
			pc = basededatos.PalagraClave(DB)
			pc['materia'] = data.strip()
			if pc.id:
				self.materias.append(pc.id)
			self.en_materia = False
		elif self.en_alerta:
			pc = basededatos.PalagraClave(DB)
			pc['alerta'] = data.strip()
			if pc.id:
				self.alertas.append(pc.id)
			self.en_alerta = False
		elif self.en_titulo:
			self.titulo += data.strip()
		elif self.en_texto:
			self.texto += data.strip()

class BoeBParser(BoeTexto):
	def __init__(self, boe):
		BoeTexto.__init__(self, boe)
		self.en_departamento = False
		self.departamento = basededatos.PalagraClave(DB)
		self.malformado = False
		self.re_cache['titulo'] = {}
		self.re_cache['texto'] = {}
		self.tipo = 'B'
	def feed(self, contenido):
		BoeTexto.feed(self, contenido)
		if self.departamento.id:
			self.alertTitulo({'departamento':self.departamento.id,'malformado':False})
			self.alertTexto({'departamento':self.departamento.id,'malformado':False})
			self.alertTT({'departamento':self.departamento.id,'malformado':False})
		self.alertTT({'malformado':False})
		if self.malformado:
			self.alertAll({'malformado':True})
			if self.departamento.id:
				self.alertAll({'departamento':self.departamento.id,'malformado':True})
				self.alertTitulo({'departamento':self.departamento.id,'malformado':True})
				self.alertTexto({'departamento':self.departamento.id,'malformado':True})
				self.alertTT({'departamento':self.departamento.id,'malformado':True})
			self.alertTitulo({'malformado':True})
			self.alertTexto({'malformado':True})
			self.alertTT({'malformado':True})

	def handle_starttag(self, tag, attrs):
		if tag == 'titulo':
			self.en_titulo = True
		elif tag == 'departamento':
			self.en_departamento = True
		elif tag == 'texto':
			self.en_texto = True
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_endtag(self, tag):
		if tag == 'titulo':
			self.en_titulo = False
			self.alertTitulo({'malformado':False})
		elif tag == 'departamento':
			self.en_departamento = False
			if self.departamento.id:
				self.alertAll({'departamento':self.departamento.id,'malformado':False})
		elif tag == 'texto':
			self.en_texto = False
			self.alertTexto({'malformado':False})
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		if self.en_departamento:
			self.departamento['departamento'] = data.strip()
		elif self.en_titulo:
			self.titulo += data.strip()
		elif self.en_texto:
			self.texto += data.strip()


if __name__ == "__main__":
	import argparse
	from datetime import timedelta
	FORMATO_FECHA = "%Y/%m/%d"
	parser = argparse.ArgumentParser(description='Procesado de Alertas del BOE.')
	parser.add_argument('inicio',
						default=datetime.now().strftime(FORMATO_FECHA),
						type=str,
						help='Fecha de inicio en formato AAAA/MM/DD, por defecto hoy',
						metavar='AAAA/MM/DD'
						)
	parser.add_argument('--fin',
						default=datetime.now().strftime(FORMATO_FECHA),
						type=str,
						help='Fecha de fin en formato AAAA/MM/DD, por defecto hoy',
						metavar='AAAA/MM/DD'
						)
	parser.add_argument('-r','--rapido'
						type=bool,
						default=None,
						help='No analiza si no hay posibles reglas aplicables'
						)

	args = parser.parse_args()
	inicio = datetime.strptime(args.inicio, FORMATO_FECHA)
	fin = datetime.strptime(args.fin, FORMATO_FECHA)
	undia = timedelta(1)
	while inicio <= fin:
		try:
			boe_parser = BoeDiaParser(inicio)
			procesa_boe(boe_parser.boe_id, args.r)
		except ValueError:
			pass
		inicio += undia



