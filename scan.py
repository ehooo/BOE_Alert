'''

'''

from boe.utils import cargar_conf, wget_url, get_attr, FICHERO_CONFIGURACION
from boe.parser import BoeDiaParser, BoeSParser, BoeAParser, BoeBParser, boeToParser
from boe.db import DBConnector, Regla, Alertas
from boe.processing import procesa_boe

import logging, httplib, urllib2, urlparse, re
from xml.parsers.expat import ParserCreate, ExpatError
from datetime import datetime

CONF = cargar_conf(FICHERO_CONFIGURACION)
DB = DBConnector(CONF)

FORMATO_FECHA = "%Y/%m/%d"


if __name__ == "__main__":
	import argparse
	from datetime import timedelta
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
	parser.add_argument('--rapido',
						action='store_true',
						default=False,
						help='No analiza si no hay posibles reglas aplicables'
						)

	args = parser.parse_args()
	inicio = datetime.strptime(args.inicio, FORMATO_FECHA)
	fin = datetime.strptime(args.fin, FORMATO_FECHA)
	undia = timedelta(1)

	while inicio <= fin:
		try:
			boe_parser = BoeDiaParser(inicio)
			proxy = False
			if CONF.has_section('conexion') and CONF.has_option('conexion','proxy'):
				proxy = CONF.getboolean('conexion','proxy')
			(contenido, headers, estado) = wget_url(boe_parser.url, proxy)

			if estado != httplib.OK:
				logging.info("Respuesta %s Cabezeras %s"%(estado, headers))
				raise ValueError("Debe ser un dia con algun BOE publicado")
			boe_parser.feed(contenido.decode('utf-8', 'replace'))
			if boe_parser.boe:
				if CONF.getboolean("celery", "activo"):
					procesa_boe.apply_async(kwargs={'rapido':args.rapido, 'boe_id':boe_parser.boe})
				else:
					procesa_boe(boe_parser.boe, args.rapido)

		except ValueError as ve:
			logging.error("ValueError: %s"%(ve))
		inicio += undia



