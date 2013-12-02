'''
Funcioles utiles miscelaneas
'''
try:
	#Para Linux
	from pymongo.bson import ObjectId
except:
	#Para Windows
	from bson.objectid import ObjectId
import os, ConfigParser, logging, hashlib, random
import httplib, urllib2, urlparse

FICHERO_CONFIGURACION = os.path.dirname(__file__) + "/../boe.conf"
def cargar_conf(fichero):
	conf = ConfigParser.ConfigParser()
	conf.readfp(open(fichero))

	logging.basicConfig(format=conf.get("log", "formato").replace('$','%'))

	NIVELES = {'DEBUG': logging.DEBUG,
			  'INFO': logging.INFO,
			  'WARNING': logging.WARNING,
			  'ERROR': logging.ERROR,
			  'CRITICAL': logging.CRITICAL}
	logging.getLogger().setLevel( NIVELES[ conf.get("log", "nivel") ] )
	return conf

def gen_clave(usuario):
	clave = hashlib.md5(usuario['_id'])
	if 'email' in usuario:
		clave.update(usuario['email'])
	if 'twitter' in usuario:
		clave.update(usuario['twitter'])
	return clave.hexdigest()

def cifrar_id(id, usuario):
	return str(id)
def descifrar_id(cid, usuario):
	return ObjectId(cid)
def cifrar_clave(clave, email):
	return hashlib.sha256(clave + hashlib.md5(email).hexdigest() ).hexdigest()
def gen_random():
	clave = ""
	for i in range(random.randint(5, 10)):
		g = random.choice('0123456789')
		for i in random.choice('abcdefghijklmnopqrstuvwxyz'):
			if (int(g)%2) == 0:
				clave += i
			else:
				clave += i.upper()
			if (int(g)%3) == 0:
				clave += random.choice('0123456789')
	return hashlib.sha256(clave).hexdigest()

def get_mongo_uri(conf):
	credencial = ""
	if conf.has_option("db", "usuario") and conf.has_option("db", "clave"):
		credencial = "%(usuario)s:%(clave)s@" % {
			"usuario":	conf.get("db", "usuario"),
			"clave":	conf.get("db", "clave")
		}
	return 'mongodb://%(credencial)s%(host)s:%(puerto)s/%(nombre_db)s'%{
		"credencial": credencial,
		"host": conf.get("db", "host"),
		"puerto": conf.get("db","puerto"),
		"nombre_db": conf.get("db","nombre"),
	}

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
def proxy_wget(url, cabezera={}):
	logging.debug("VIA Proxy: %s %s"%(url, cabezera))
	req = urllib2.Request(url, headers=cabezera)
	proxy_handler = urllib2.ProxyHandler()
	opener = urllib2.build_opener(proxy_handler)
	contenido = None
	cabezeras = {}
	estado = None
	try:
		f = opener.open(req)
		estado = f.code
		contenido = f.read()
		cabezeras = f.headers.dict
		f.close()
		opener.close()
	except urllib2.HTTPError as er:
		logging.error("Acceso fallido a %s --> %s"%(url, er))
		cabezeras = er.headers.dict
		if estado is None:
			estado = er.code
		if estado is None:
			estado = er.errno
	finally:
		return (contenido, cabezeras, estado)

def wget_url(url, proxy, cabezera={}, tipo="GET", post=None):
	if proxy:
		return proxy_wget(url, cabezera)
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
