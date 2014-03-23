'''
Funcioles utiles miscelaneas
'''
import logging
import httplib
import urllib2
import urlparse

def get_attr(attrs, key):
	for (k,v) in attrs:
		if k == key:
			return v
	return None
from HTMLParser import HTMLParser
class HTML2Plain(HTMLParser):
	def __init__(self):
		HTMLParser.__init__(self)
		self.plain = ""
		self.href = None
	def handle_data(self, data):
		self.plain += data
	def handle_starttag(self, tag, attrs):
		if tag == 'a':
			self.href = get_attr(attrs, 'href')
			if self.href is not None:
				self.plain += "["
	def handle_endtag(self, tag):
		if tag == 'a' and self.href is not None:
			self.plain += "](%s)"%self.href
def html2plain(html):
	parser = HTML2Plain()
	parser.feed(html)
	return parser.plain

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
