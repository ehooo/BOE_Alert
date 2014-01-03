
from parser import BoeSParser, BoeAParser, BoeBParser, boeToParser
from utils import cargar_conf, wget_url, FICHERO_CONFIGURACION, html2plain
from db import DBConnector, Alertas, Usuario

from email.mime.multipart import MIMEMultipart
from xml.parsers.expat import ExpatError
from email.mime.text import MIMEText
from celery import task
import httplib, logging, smtplib
import web


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
	DB = DBConnector(CONF)
	alerta = Alertas(DB)
	alerta.id = alerta_id
	if alerta['enviado']:
		return
	alerta['enviado'] = True

	usuario = Usuario(DB)
	usuario.id = alerta['usuario']
	if usuario['alert_email'] and usuario['email_valido'] and usuario['email']:
		RENDER = web.template.render(CONF.get('web','tema'))
		links = {
			'pdf':"http://boe.es/boe/dias/%s/pdfs/%s.pdf"%(alerta['fecha'], alerta['boe']),
			'html':"http://boe.es/diario_boe/txt.php?id=%s"%(alerta['boe']),
			'xml':"http://boe.es/diario_boe/xml.php?id=%s"%(alerta['boe']),
			'epub':"http://boe.es/diario_boe/epub.php?id=%s"%(alerta['boe'])
		}
		html = str( RENDER.alerta_email(alerta['boe'], ", ".join(alerta['alias']), links ) )
		plain = html2plain(html)
		subject = "Alerta sobre %s"%alerta['boe']
		if CONF.getboolean("celery", "activo"):
			envia_email.apply_async(kwargs={'correo':usuario['email'],"subject":subject,"plain":plain,'html':html})
		else:
			envia_email(usuario['email'], subject, plain, html)
	if usuario['alert_twitter'] and usuario['twitter']:
		url = "http://boe.es/diario_boe/txt.php?id=%s"%(alerta['boe'])
		contenido = "Datos de interes en %s (%s) %s"%(alerta['boe'], len(alerta['alias']), url)
		if CONF.getboolean("celery", "activo"):
			envia_dm.apply_async(kwargs={'usuario':usuario['twitter'],"contenido":contenido})
		else:
			envia_dm(usuario['twitter'], contenido)

@task
def envia_email(correo, subject, plain, html=None):
	if not CONF.has_section("email"):
		return
	msg = MIMEMultipart('alternative')
	msg['Subject'] = subject
	msg['From'] = CONF.get("email", "email")
	msg['To'] = correo
	msg.attach(MIMEText(plain, 'plain'))
	if html:
		msg.attach(MIMEText(html, 'html'))

	smtp_server = None
	if CONF.has_option("email", "ssl") and CONF.getboolean("email", "ssl"):
		smtp_server = smtplib.SMTP_SSL()
	else:
		smtp_server = smtplib.SMTP()

	smtp_server.connect(CONF.get("email", "server"), CONF.getint("email", "port"))

	if CONF.has_option("email", "tls") and CONF.getboolean("email", "tls"):
		smtp_server.starttls()
		smtp_server.ehlo(CONF.get("email", "server"))

	if CONF.has_option("email", "usuario") and CONF.has_option("email", "clave"):
		smtp_server.login(CONF.get("email", "usuario"), CONF.get("email", "clave"))

	smtp_server.sendmail(msg['From'], msg['To'], msg.as_string())
	smtp_server.quit()
	#smtp_server.close()
	logging.info("Notificado %s por e-Mail sobre '%s'"%(correo, subject))

@task
def envia_dm(usuario, contenido):
	logging.info("Notificar a @%s con un DM con el texto '%s'"%(usuario, contenido))

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


