
from parser import BoeSParser, BoeAParser, BoeBParser, boeToParser
from utils import cargar_conf, wget_url, FICHERO_CONFIGURACION
from db import DBConnector, Alertas

from xml.parsers.expat import ExpatError
from celery import task
import httplib, logging

CONF = cargar_conf(FICHERO_CONFIGURACION)

@task
def envia_alerta(alerta_id):
	DB = DBConnector(CONF)
	alerta = Alertas(DB)
	alerta.id = alerta_id
	alerta['enviado'] = True
	logging.info("Notificar a %s sobre '%s' en el BOE: %s"%(alerta['usuario'], alerta['alias'], alerta['boe']))

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
	try:
		boe.feed(contenido)
		for alerta in boe.to_alert:
			if CONF.getboolean("celery", "activo"):
				envia_alerta.apply_async(kwargs={'alerta_id':alerta.id})
			else:
				envia_alerta(alerta.id)
	except ExpatError as xmlMalformado:
		#TODO lanzar alerta ???
		logging.critical("XML del BOE %s mal formado: %s, cabezeras: %s"%(boe_id,xmlMalformado,headers))

	if isinstance(boe, BoeSParser):
		logging.info("Hoy hay un total de %s BOES para procesar"%(len(boe.boes)))
		for boeid in boe.boes:
			if CONF.getboolean("celery", "activo"):
				procesa_boe.apply_async(kwargs={'boe_id':boeid,'rapido':rapido})
			else:
				procesa_boe(boeid, rapido)


