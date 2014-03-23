from boe.utils import cargar_conf, wget_url, FICHERO_CONFIGURACION
from boe.parser import BoeDiaParser
from boe.processing import procesa_boe

import logging, httplib
from datetime import datetime


if __name__ == "__main__":
	import argparse
	from datetime import timedelta
	FORMATO_FECHA = "%Y/%m/%d"
	parser = argparse.ArgumentParser(description='Procesado de Alertas del BOE.')
	parser.add_argument('inicio',
						nargs='?',
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
	parser.add_argument('--boe',
						default=None,
						type=str,
						help='BOE a analizar: BOE-NUM',
						metavar='BOE-NUM'
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

	CONF = cargar_conf(FICHERO_CONFIGURACION)

	if args.boe is not None:
		if CONF.getboolean("celery", "activo"):
			logging.debug("Analizando el BOE: %s con Celery"%(args.boe))
			task_id = procesa_boe.apply_async(kwargs={'rapido':args.rapido, 'boe_id':args.boe})
		else:
			logging.debug("Analizando el BOE: %s"%(args.boe))
			procesa_boe(args.boe, args.rapido)
	else:
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
						task_id = procesa_boe.apply_async(kwargs={'rapido':args.rapido, 'boe_id':boe_parser.boe})
					else:
						procesa_boe(boe_parser.boe, args.rapido)

			except ValueError as ve:
				logging.error("ValueError: %s"%(ve))
			inicio += undia



