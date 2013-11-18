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
			logging.debug("Detectado encode: %s"%(def_encode))

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
def alert(usuario):
	pass

@task
def procesa_boe(id):
	url = "http://boe.es/diario_boe/xml.php?id=%s"%id
	(contenido, headers, estado) = wget_url(url)
	p = None
	if id.startswith('BOE-A'):
		p = BoeAParser()
	elif id.startswith('BOE-B'):
		p = BoeBParser()
	elif id.startswith('BOE-S'):
		p = BoeSParser()
	if p is None:
		raise ValueError("Id '%s' no soportado"%id)
	p.Parse(contenido)
	if isinstance(p, BoeSParser):
		logging.info("Hoy hay un total de %s BOES para procesar"%(len(p.boes)))
		for boe_id in p.boes:
			#procesa_boe.apply_async((id))#Celery
			procesa_boe(boe_id)

from HTMLParser import HTMLParser
from datetime import datetime
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
	def __init__(self):
		self.p = ParserCreate()
		self.p.StartElementHandler = self.handle_starttag
		self.p.EndElementHandler = self.handle_endtag
		self.p.CharacterDataHandler = self.handle_data
	def Parse(self, contenido):
		self.p.Parse(contenido)
	def handle_starttag(self, tag, attrs):
		pass
	def handle_endtag(self, tag):
		pass
	def handle_data(self, data):
		pass

class BoeSParser(BasicParser):
	def __init__(self):
		BasicParser.__init__(self)
		self.act_sec = None
		self.act_dep = None
		self.act_epi = None
		self.en_titulo = False
		self.malformado = False
		self.titulo = ""
		self.boes = []
	def handle_starttag(self, tag, attrs):
		if tag in ['seccion','departamento','epigrafe']:
			pc = basededatos.PalagraClave(DB)
			pc[tag] = attrs['nombre'].strip()
			if tag == 'seccion':
				self.act_sec = pc
			elif tag == 'departamento':
				self.act_dep = pc
			elif tag == 'epigrafe':
				self.act_epi = pc
		elif tag == 'item':
			self.boes.append( attrs['id'] )
		elif tag == 'titulo':
			self.en_titulo = True
	def handle_endtag(self, tag):
		#TODO crear query
		query = {'seccion':None, 'departamento':None, 'epigrafe':None, 're_titulo':None}
		if tag == 'seccion':
			self.act_sec = None
		elif tag == 'departamento':
			self.act_dep = None
		elif tag == 'epigrafe':
			self.act_epi = None
		elif tag == 'titulo':
			self.titulo = ""
			self.en_titulo = False
			self.malformado = False
		elif self.en_titulo and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		if self.en_titulo:
			self.titulo += data

class BoeAParser(BasicParser):
	def __init__(self):
		BasicParser.__init__(self)
		self.en_departamento = False
		self.en_origen_legislativo = False
		self.materias = []
		self.en_materia = False
		self.alertas = []
		self.en_alerta = False
		
		self.en_titulo = False
		self.titulo = ""
		self.en_texto = False
		self.texto = ""
		self.malformado = False
	def Parse(self, contenido):
		#TODO Crear query
		BasicParser.Parse(self, contenido)

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
		elif tag == 'origen_legislativo':
			self.en_origen_legislativo = False
		elif tag == 'materia':
			self.en_materia = False
		elif tag == 'alerta':
			self.en_alerta = False
		elif tag == 'texto':
			self.en_texto = False
		elif tag == 'titulo':
			self.en_titulo = False
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		cdata = data.strip()
		if self.en_departamento:
			pc = basededatos.PalagraClave(DB)
			pc['departamento'] = cdata
			self.en_departamento = False
		elif self.en_origen_legislativo:
			pc = basededatos.PalagraClave(DB)
			pc['origen_legislativo'] = cdata
			self.en_origen_legislativo = False
		elif self.en_materia:
			pc = basededatos.PalagraClave(DB)
			pc['materia'] = cdata
			self.materias.append(pc)
			self.en_materia = False
		elif self.en_alerta:
			pc = basededatos.PalagraClave(DB)
			pc['alerta'] = cdata
			self.alertas.append(pc)
			self.en_alerta = False
		elif self.en_titulo:
			self.titulo += data
		elif self.en_texto:
			self.texto += data

class BoeBParser(BasicParser):
	def __init__(self):
		BasicParser.__init__(self)
		self.en_departamento = False
		self.en_titulo = False
		self.titulo = ""
		self.en_texto = False
		self.texto = ""
		self.malformado = False
	def Parse(self, contenido):
		#TODO Crear query
		BasicParser.Parse(self, contenido)

	def handle_starttag(self, tag, attrs):
		if tag == 'departamento':
			self.en_departamento = True
		elif tag == 'texto':
			self.en_texto = True
		elif tag == 'titulo':
			self.en_titulo = True
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_endtag(self, tag):
		if tag == 'texto':
			self.en_texto = False
		elif tag == 'titulo':
			self.en_titulo = False
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		if self.en_departamento:
			pc = basededatos.PalagraClave(DB)
			pc['departamento'] = data.strip()
			self.en_departamento = False
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

	args = parser.parse_args()
	inicio = datetime.strptime(args.inicio, FORMATO_FECHA)
	fin = datetime.strptime(args.fin, FORMATO_FECHA)
	undia = timedelta(1)
	while inicio <= fin:
		try:
			boe_parser = BoeDiaParser(inicio)
			procesa_boe(boe_parser.boe_id)
		except ValueError:
			pass
		inicio += undia



