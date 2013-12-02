
from parser import BoeSParser, BoeAParser, BoeBParser, boeToParser
from utils import cargar_conf, wget_url, FICHERO_CONFIGURACION
from db import DBConnector, Alertas

from xml.parsers.expat import ExpatError
from celery import task
import httplib, logging

CONF = cargar_conf(FICHERO_CONFIGURACION)

'''
http://docs.celeryproject.org/en/latest/reference/celery.schedules.html#celery.schedules.crontab
from celery.schedules import crontab
from celery.task import periodic_task

@periodic_task(run_every=crontab(hour=7, minute=30, day_of_week="mon-sat"))
def every_monday_morning():
	
    print("This is run every Monday morning at 7:30")
'''


@task
def envia_alerta(alerta_id):
	alerta = Alertas(DBConnector(CONF))
	alerta.id = alerta_id
	alerta['enviado'] = True
	logging.info("Notificar a %s sobre '%s' en el BOE: %s"%(alerta['usuario'], alerta['alias'], alerta['boe']))

@task
def envia_email(correo, contenido):
	logging.info("Notificar a %s con un e-Mail con el texto '%s'"%(correo, contenido))

@task
def procesa_boe(boe_id, rapido):
	url = "http://boe.es/diario_boe/xml.php?id=%s"%boe_id
	proxy = False
	if CONF.has_section('conexion') and CONF.has_option('conexion','proxy'):
		proxy = CONF.getboolean('conexion','proxy')
	(contenido, headers, estado) = wget_url(url, proxy)

	if estado != httplib.OK:
		#TODO Notificar como malformado?
		logging.error("Error %s al acceder al BOE: %s"%(estado, boe_id))
		return
	boe = boeToParser(boe_id, rapido)
	if boe is None:
		logging.error("Error BOE %s no procesable" % boe_id)
		return
	try:
		boe.feed(contenido)
		for alerta in boe.to_alert:
			if CONF.getboolean("celery", "activo"):
				envia_alerta.apply_async(kwargs={'alerta_id':alerta})
			else:
				envia_alerta(alerta)
	except ExpatError as xmlMalformado:
		#TODO lanzar alerta ???
		logging.critical("XML del BOE %s mal formado: %s"%(boe_id,xmlMalformado))

	if isinstance(boe, BoeSParser):
		logging.info("Hoy hay un total de %s BOES para procesar"%(len(boe.boes)))
		for boeid in boe.boes:
			if CONF.getboolean("celery", "activo"):
				procesa_boe.apply_async(kwargs={'boe_id':boeid,'rapido':rapido})
			else:
				procesa_boe(boeid, rapido)


