from django.utils.translation import ugettext_lazy as _
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from datetime import timedelta
from datetime import datetime
from optparse import make_option
import httplib

from boe.scaner.models import Boe
from boe.scaner.parser import BoeDiaParser
from boe.scaner.utils import wget_url
from boe.scaner.tasks import procesa_boe
from django.conf import settings
import logging

FORMATO_FECHA = "%Y/%m/%d"

class Command(BaseCommand):
	args = '[inicio [fin]]'
	help = _('Procesa los BOEs comprendidos en un rango dado de fechas o uno dado.')
	option_list = BaseCommand.option_list + (
		make_option('--inicio',
			action='store',
			type='string',
			dest='inicio',
			default=datetime.now().strftime(FORMATO_FECHA),
			help=_('Fecha de inicio en formato AAAA/MM/DD, por defecto hoy'),
		metavar='AAAA/MM/DD'),
			make_option('--fin',
			action="store",
			type='string',
			dest="fin",
			default=datetime.now().strftime(FORMATO_FECHA),
			help=_('Fecha de fin en formato AAAA/MM/DD, por defecto hoy'),
			metavar="AAAA/MM/DD"),
		make_option('--boe',
			action='store',
			type='string',
			dest='boe',
			default=None,
			help=_('BOE a analizar: BOE-NUM'),
			metavar='BOE-NUM'),
		make_option('--rapido',
			action='store_true',
			dest='rapido',
			default=False,
			help=_('No procesa los boes conocidos'),
        )
	)

	def handle(self, *args, **options):
		if options['boe']:
			if options['rapido']:
				try:
					boe_db = Boe.objects.get(boe=options['boe'])
					return
				except Boe.DoesNotExist:
					pass
			logging.info("Procesando %s"%(options['boe']))
			procesa_boe( options['boe'] )
		else:
			hoy = datetime.now().strftime(FORMATO_FECHA)
			undia = timedelta(1)
			inicio = datetime.strptime(options['inicio'], FORMATO_FECHA)
			if len(args)>0 and hoy == options['inicio']:
				inicio = datetime.strptime(args[0], FORMATO_FECHA)
			fin = datetime.strptime(options['fin'], FORMATO_FECHA)
			if len(args)>1 and hoy == options['fin']:
				fin = datetime.strptime(args[1], FORMATO_FECHA)

			while inicio <= fin:
				try:
					boe_parser = BoeDiaParser(inicio)
					(contenido, headers, estado) = wget_url(boe_parser.url, settings.PROXY)
					if estado == httplib.OK:
						boe_parser.feed(contenido.decode('utf-8', 'replace'))
					if boe_parser.boe:
						if options['rapido']:
							try:
								boe_db = Boe.objects.get(boe=boe_parser.boe)
								raise ValueError(_('BOE conocido'))
							except Boe.DoesNotExist:
								pass
						logging.info("Procesando %s"%(boe_parser.boe))
						procesa_boe( boe_parser.boe )
					logging.info("Respuesta %s Cabezeras %s"%(estado, headers))
				except ValueError as ve:
					logging.error("ValueError: %s"%(ve))
				inicio += undia
