from __future__ import absolute_import
from django.conf import settings

from boe.scaner.parser import BoeSParser
from boe.scaner.parser import boe2parser
from boe.scaner.utils import wget_url
from boe.scaner.utils import html2plain
from boe.scaner.models import Boe
from boe.scaner.models import AlertaUsuario
from boe.core.models import Regla

from celery import task
from datetime import datetime
import httplib
import logging

from xml.parsers.expat import ExpatError

@task
def procesa(boe_id):
	boe_db = None
	try:
		boe_db = Boe.objects.get(boe=boe_id)
	except Boe.DoesNotExist:
		boe_db = Boe.objects.create(boe=boe_id)
	url = "http://boe.es/diario_boe/xml.php?id=%s"%boe_db.boe
	(contenido, headers, estado) = wget_url(url, settings.PROXY)

	if estado != httplib.OK:
		boe_db.error = True
		boe_db.error_text = "Error %s al acceder al BOE"%(estado)
		logging.error("Error %s al acceder al BOE: %s"%(estado, boe_db.boe))
		return

	boeparser = boe2parser(boe_db)
	if boeparser is None:
		boe_db.error = True
		boe_db.error_text = "Error BOE no procesable"
		logging.error("Error BOE %s no procesable" % boe_db.boe)
		return
	try:
		boeparser.feed(contenido)
		envia_alerta(boe_db)
	except ExpatError as xmlMalformado:
		error_text = "XML del BOE %s mal formado: %s"%(boe_db.boe, xmlMalformado)
		logging.critical(error_text)
		boeparser.boe.error = True
		boeparser.boe.error_text = error_text

	if isinstance(boeparser, BoeSParser):
		logging.info("Hoy hay un total de %s BOES para procesar"%(len(boeparser.boes)))
		#'''
		for boeid in boeparser.boes:
			procesa_boe(boeid)
		#'''

@task
def cron_procesa():
    hoy = date.today()
    boe_parser = BoeDiaParser(hoy)
    (contenido, headers, estado) = wget_url(boe_parser.url, settings.PROXY)
    if estado == httplib.OK:
        boe_parser.feed(contenido.decode('utf-8', 'replace'))
        if boe_parser.boe:
			logging.info("Procesando %s"%(boe_parser.boe))
			procesa_boe( boe_parser.boe )
    logging.info("Respuesta %s Cabezeras %s"%(estado, headers))

def clean_db():
	pass

def envia_alerta(boe_db):
	alertas = AlertaUsuario.objects.filter(boe=boe_db).order_by('user')
	last_user=None
	all_rules=[]
	for alerta in alertas:
		if last_user and last_user!=alerta.user:
			if last_user.boe_auth.envia_twitter:
				envia_dm(boe_db, last_user, all_rules)
			if last_user.boe_auth.envia_email:
				envia_email(boe_db, last_user, all_rules)
			all_rules=[]
		else:
			last_user = alerta.user
			if not alerta.regla.alias in all_rules:
				all_rules.append(alerta.regla.alias)
				alerta.enviado = True

def envia_dm(boe_db, user, alias):
	url = "http://boe.es/diario_boe/txt.php?id=%s"%(boe_db.boe)
	relgas = ", ".join(alias)
	contenido = "(%(num)s) %(url)s %(alias)s"%{'url':url,'num':len(relgas),'alias':relgas}

	AlertaUsuario.objects.filter(boe=boe_db, user=user).update(fecha_envio = datetime.now() )
	logging.info("Notificar a @%s con un DM sobre '%s'"%(user, relgas))

def envia_email(boe_db, user, alias):
	links = {
		'pdf':"http://boe.es/boe/dias/%s/pdfs/%s.pdf"%(boe_db.fecha, boe_db.boe),
		'html':"http://boe.es/diario_boe/txt.php?id=%s"%(boe_db.boe),
		'xml':"http://boe.es/diario_boe/xml.php?id=%s"%(boe_db.boe),
		'epub':"http://boe.es/diario_boe/epub.php?id=%s"%(boe_db.boe)
	}
	relgas = ", ".join(alias)
	subject = "Alerta sobre %s"%(boe_db.boe)

	alertas = AlertaUsuario.objects.filter(boe=boe_db, user=user).update(fecha_envio = datetime.now() )
	logging.info("Notificar a @%s con un Email sobre '%s'"%(user_id, relgas))

def procesa_boe(boe_id):
	boe_db = None
	try:
		boe_db = Boe.objects.get(boe=boe_id)
	except Boe.DoesNotExist:
		boe_db = Boe.objects.create(boe=boe_id)
	celerytask = procesa.apply_async(kwargs={'boe_id':boe_id})
	boe_db.celery_task = celerytask.task_id
	boe_db.save()
	return celerytask 
