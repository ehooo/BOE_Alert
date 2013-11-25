'''

'''
import logging, httplib, urllib2, urlparse, re

from xml.parsers.expat import ParserCreate, ExpatError
from HTMLParser import HTMLParser
from datetime import datetime

from utils import get_attr, cargar_conf, FICHERO_CONFIGURACION
from db import Regla, PalagraClave, DBConnector, Alertas

FORMATO_FECHA = "%Y/%m/%d"

CONF = cargar_conf(FICHERO_CONFIGURACION)
DB = DBConnector(CONF)


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
		self.boe = None
		if dt_dia is None:
			dt_dia = datetime.now()
		self.url = dt_dia.strftime(BoeDiaParser.URL_DATE_FORMAT)

	def handle_starttag(self, tag, attrs):
		if tag == 'li' and BoeDiaParser.has_attr(attrs, "class", "puntoXML"):
			self.en_link = True
		elif self.en_link and tag == 'a':
			href_xml = get_attr(attrs, 'href')
			self.boe = href_xml[href_xml.rfind("=")+1:]
	def handle_endtag(self, tag):
		if self.en_link and (tag == 'li' or tag == 'a'):
			self.en_link = False

class BasicParser():
	def __init__(self, boe):
		self.boe = boe
		self.en_fecha = False
		self.fecha = None
		self.en_titulo = False
		self.titulo = ""
		self.p = ParserCreate()
		self.p.StartElementHandler = self.handle_starttag
		self.p.EndElementHandler = self.handle_endtag
		self.p.CharacterDataHandler = self.handle_data
		self.re_cache = {}#Para tener cache hay que inicializar re_cache={'titulo':{}}
		self.tipo = None
		self.claves = ["re_titulo","departamento"]
		self.to_alert = []
	def feed(self, contenido):
		self.p.Parse(contenido)
	def alert(self, regla):
		alerta = Alertas(DB).add(regla, self.boe, self.fecha)
		if not 'enviado' in alerta or alerta['enviado']:
			self.to_alert.append(alerta.id)

	def alertAll(self, query):
		if self.tipo:
			query['tipo'] = self.tipo
		for clave in self.claves:
			if not clave in query:
				query[clave] = {'$exists':False}

		reglas = Regla(DB)
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

		reglas = Regla(DB)
		encontradas = {'total':1}
		pag = 0
		while encontradas['total']>pag:
			encontradas = reglas.list(pag, query,[],10)
			for elem in encontradas['data']:
				tre = elem['re_'+cache]
				s = False
				#m = False
				if cache and cache in self.re_cache and tre in self.re_cache[cache]:
					s = self.re_cache[cache][tre]['search']
					#m = self.re_cache[cache][tre]['match']
				else:
					tre = re.compile(elem['re_'+cache])
					s_ = tre.search(paja)
					s = s_ is not None
					#m_ = tre.match(paja) is not None
					#m = m_ is not None
					if cache and cache in self.re_cache:
						self.re_cache[cache][tre] = { 'search':s}#, 'match':m }
				if s:# or m:
					#logging.debug("search %s %s"%(s,tre))
					#logging.debug("match %s %s"%(m,tre))
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
		self.act_sec = PalagraClave(DB)
		self.act_dep = PalagraClave(DB)
		self.act_epi = PalagraClave(DB)
		self.malformado = False
		self.boes = []
		self.tipo = 'S'
		self.claves = ["seccion","departamento","epigrafe","re_titulo"]
	def handle_starttag(self, tag, attrs):
		if tag == 'fechaInv':
			self.en_fecha = True
		elif tag in ['seccion','departamento','epigrafe']:
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
		if tag == 'fechaInv':
			self.en_fecha = False
		elif tag == 'seccion':
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
		if self.en_fecha:
			self.fecha = datetime.strptime(data.strip(), FORMATO_FECHA)
		elif self.en_titulo:
			self.titulo += data.strip()

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

		reglas = Regla(DB)
		encontradas = {'total':1}
		pag = 0
		while encontradas['total']>pag:
			encontradas = reglas.list(pag, query,[],10)
			for elem in encontradas['data']:
				tire = elem['re_titulo']
				tis = False
				#tim = False
				if tire in self.re_cache['titulo']:
					tis = self.re_cache['titulo'][tire]['search']
					#tim = self.re_cache['titulo'][tire]['match']
				else:
					tre = re.compile(tire)
					tis_ = tre.search(self.titulo)
					tis = tis_ is not None
					#tim_ = tre.match(self.titulo)
					#tim = tim_ is not None
					if cache:
						self.re_cache['titulo'][tire] = { 'search':tis}#, 'match':tim }

				tore = elem['re_texto']
				tos = False
				#tom = False
				if tore in self.re_cache['texto']:
					tos = self.re_cache['texto'][tore]['search']
					#tom = self.re_cache['texto'][tore]['match']
				else:
					tre = re.compile(tire)
					tos_ = tre.search(self.texto)
					tos = tos_ is not None
					#tom_ = tre.match(self.texto)
					#tom = tom_ is not None
					if cache:
						self.re_cache['titulo'][tore] = { 'search':tos}#, 'match':tom }
				if tis and tos:
					logging.debug("search Titulo: %s Texto: %s"%(tis, tos))
					self.alert(elem)
				#elif tim and tom:#esif por que ya ha sido alertado
				#	logging.debug("match Titulo: %s Texto: %s"%(tim, tom))
				#	self.alert(elem)
			pag += 1

class BoeAParser(BoeTexto):
	def __init__(self, boe):
		BoeTexto.__init__(self, boe)
		self.departamento = PalagraClave(DB)
		self.en_departamento = False
		self.origen_legislativo = PalagraClave(DB)
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
		if tag == 'fecha_publicacion':
			self.en_fecha = True
		elif tag == 'departamento':
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
		if tag == 'fecha_publicacion':
			self.en_fecha = False
		elif tag == 'departamento':
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
		if self.en_fecha:
			self.fecha = datetime.strptime(data.strip(), "%Y%m%d")
		elif self.en_departamento:
			self.departamento['departamento'] = data.strip()
			self.en_departamento = False
		elif self.en_origen_legislativo:
			self.origen_legislativo['origen_legislativo'] = data.strip()
			self.en_origen_legislativo = False
		elif self.en_materia:
			pc = PalagraClave(DB)
			pc['materia'] = data.strip()
			if pc.id:
				self.materias.append(pc.id)
			self.en_materia = False
		elif self.en_alerta:
			pc = PalagraClave(DB)
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
		self.departamento = PalagraClave(DB)
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
		if tag == 'fecha_publicacion':
			self.en_fecha = True
		elif tag == 'titulo':
			self.en_titulo = True
		elif tag == 'departamento':
			self.en_departamento = True
		elif tag == 'texto':
			self.en_texto = True
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_endtag(self, tag):
		if tag == 'fecha_publicacion':
			self.en_fecha = False
		elif tag == 'titulo':
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
		if self.en_fecha:
			self.fecha = datetime.strptime(data.strip(), "%Y%m%d")
		elif self.en_departamento:
			self.departamento['departamento'] = data.strip()
		elif self.en_titulo:
			self.titulo += data.strip()
		elif self.en_texto:
			self.texto += data.strip()


def boeToParser(id, rapido):
	query = {}
	constructor = None

	if id.startswith('BOE-A'):
		query = {'tipo':'A'}
		constructor = BoeAParser
	elif id.startswith('BOE-B'):
		query = {'tipo':'B'}
		constructor = BoeBParser
	elif id.startswith('BOE-S'):
		query = {'$or':[{'tipo':'S'},{'tipo':'A'},{'tipo':'B'}]}
		constructor = BoeSParser

	if constructor is None:
		return
	if rapido:
		reglas = Regla(DB).list(0,query,[],1)
		if reglas['total'] == 0:
			return
	return constructor(id)
