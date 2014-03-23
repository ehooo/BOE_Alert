'''

'''

from django.contrib.auth.models import User
from django.db.models import Q
from django.db import IntegrityError

from boe.scaner.models import Boe
from boe.scaner.models import AlertaUsuario

from boe.core.models import Regla
from boe.core.models import ReglaA
from boe.core.models import ReglaB
from boe.core.models import ReglaS

from boe.core.models import Seccion
from boe.core.models import Departamento
from boe.core.models import Epigrafe
from boe.core.models import OrigenLegislativo
from boe.core.models import Materia
from boe.core.models import MateriasCPV
from boe.core.models import Alerta
from boe.core.models import ExpresionRegular

from boe.scaner.utils import get_attr

import re
from xml.parsers.expat import ParserCreate, ExpatError
from HTMLParser import HTMLParser
from datetime import datetime
from symbol import except_clause

FORMATO_FECHA = "%Y/%m/%d"

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
		self.boe = None
		if dt_dia is None:
			dt_dia = datetime.now()
		self.url = dt_dia.strftime(BoeDiaParser.URL_DATE_FORMAT)

	def handle_starttag(self, tag, attrs):
		if tag == 'li' and BoeDiaParser.has_attr(attrs, "class", "puntoXML"):
			self.en_link = True
		elif self.en_link and tag == 'a':
			href_xml = get_attr(attrs, 'href')
			self.boe = href_xml[href_xml.rfind("=")+1:]
	def handle_endtag(self, tag):
		if self.en_link and (tag == 'li' or tag == 'a'):
			self.en_link = False

class BasicParser():
	def __init__(self, boe, model):
		self.boe = boe
		self.en_fecha = True
		self.en_titulo = False
		self.titulo = ""
		self.malformado = False
		self.model = model()

		self.p = ParserCreate()
		self.p.StartElementHandler = self.handle_starttag
		self.p.EndElementHandler = self.handle_endtag
		self.p.CharacterDataHandler = self.handle_data
	def feed(self, contenido):
		self.p.Parse(contenido)
		self.alerta_modelo()
	def handle_starttag(self, tag, attrs):
		if tag == 'titulo':
			self.titulo = ""
			self.en_titulo = True
	def handle_endtag(self, tag):
		if tag == 'titulo':
			self.en_titulo = False
	def handle_data(self, data):
		if self.en_fecha:
			try:
				self.boe.fecha = datetime.strptime(data.strip(), FORMATO_FECHA)
				self.en_fecha = False
			except ValueError:
				pass
		elif self.en_titulo:
			self.titulo += data.strip()
	def alerta_modelo(self):#Ha de analizarse el modelo para avisar a los destinatarios
		pass

class BoeSParser(BasicParser):
	def __init__(self, boe):
		BasicParser.__init__(self, boe, ReglaS)
		self.boes = []

	def handle_starttag(self, tag, attrs):
		BasicParser.handle_starttag(self, tag, attrs)
		if tag == 'fechaInv':
			self.en_fecha = True
		elif tag in ['seccion','departamento','epigrafe']:
			valor = attrs['nombre'].strip().lower()
			if tag == 'seccion':
				try:
					self.model.seccion = Seccion.objects.create(texto=valor)
				except IntegrityError:
					self.model.seccion = Seccion.objects.get(texto=valor)
			elif tag == 'departamento':
				try:
					self.model.departamento = Departamento.objects.create(texto=valor)
				except IntegrityError:
					self.model.departamento = Departamento.objects.get(texto=valor)
			elif tag == 'epigrafe':
				
				try:
					self.model.epigrafe = Epigrafe.objects.create(texto=valor)
				except IntegrityError:
					self.model.epigrafe = Epigrafe.objects.get(texto=valor)
		elif tag == 'item':
			self.boes.append(attrs['id'])
	def handle_endtag(self, tag):
		BasicParser.handle_endtag(self, tag)
		if tag == 'titulo':
			self.alerta_modelo()
		elif tag == 'fechaInv':
			self.en_fecha = False
		elif tag == 'seccion':
			self.model.seccion = None
		elif tag == 'departamento':
			self.model.departamento = None
		elif tag == 'epigrafe':
			self.model.epigrafe = None
		elif self.en_titulo and tag == 'img':
			self.malformado = True

	def alerta_modelo(self):
		#Alertamos primero a los "simples"
		to_alert = ReglaS.objects.filter(
			Q(seccion__isnull=True) | Q(seccion=self.model.seccion),
			Q(departamento__isnull=True) | Q(departamento=self.model.departamento),
			Q(epigrafe__isnull=True) | Q(epigrafe=self.model.epigrafe),
			Q(re_titulo__isnull=True)
		)
		for subregla in to_alert:
			try:
				AlertaUsuario.objects.get(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)
			except AlertaUsuario.DoesNotExist:
				AlertaUsuario.objects.create(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)
		all_re = ReglaS.objects.filter(re_titulo__isnull=False)

		#Alertamos de las expresiones regulares
		ex_search = ExpresionRegular.objects.filter(s_titulo__isnull=False)
		for re_exp in ex_search:
			reexp = re.compile(re_exp.re_exp, re.UNICODE|re.IGNORECASE)
			
			if reexp.search(self.titulo):
				to_alert = ReglaS.objects.filter(
					Q(seccion__isnull=True) | Q(seccion=self.model.seccion),
					Q(departamento__isnull=True) | Q(departamento=self.model.departamento),
					Q(epigrafe__isnull=True) | Q(epigrafe=self.model.epigrafe),
					Q(re_titulo=re_exp)
				)
				for subregla in to_alert:
					try:
						AlertaUsuario.objects.get(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)
					except AlertaUsuario.DoesNotExist:
						AlertaUsuario.objects.create(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)

class BoeTexto(BasicParser):
	def __init__(self, boe, model):
		BasicParser.__init__(self, boe, model)
		self.en_texto = False
		self.texto = ""

	def handle_data(self, data):
		BasicParser.handle_data(self, data)
		if self.en_texto:
			self.texto += data.strip()
	def handle_starttag(self, tag, attrs):
		BasicParser.handle_starttag(self, tag, attrs)
		if tag == 'texto':
			self.texto = ""
			self.en_texto = True
	def handle_endtag(self, tag):
		BasicParser.handle_endtag(self, tag)
		if tag == 'texto':
			self.en_texto = False
			self.alerta_modelo()

class BoeAParser(BoeTexto):
	def __init__(self, boe):
		BoeTexto.__init__(self, boe, ReglaA)
		self.alertas = []
		self.materias = []
		self.en_departamento = False
		self.en_origen_legislativo = False
		self.en_materia = False
		self.en_rango = False
		self.en_alerta = False

	def handle_starttag(self, tag, attrs):
		BoeTexto.handle_starttag(self, tag, attrs)
		if tag == 'fecha_publicacion':
			self.en_fecha = True
		elif tag == 'departamento':
			self.en_departamento = True
		elif tag == 'origen_legislativo':
			self.en_origen_legislativo = True
		elif tag == 'materia':
			self.en_materia = True
		elif tag == 'rango':
			self.en_rango = True
		elif tag == 'alerta':
			self.en_alerta = True
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_endtag(self, tag):
		if tag == 'fecha_publicacion':
			self.en_fecha = False
		elif tag == 'departamento':
			self.en_departamento = False
		elif tag == 'origen_legislativo':
			self.en_origen_legislativo = False
		elif tag == 'materia':
			self.en_materia = False
		elif tag == 'alerta':
			self.en_alerta = False
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		BoeTexto.handle_data(self, data)
		valor = data.strip().lower()
		if self.en_departamento:
			try:
				self.model.departamento = Departamento.objects.create(texto=valor)
			except IntegrityError:
				self.model.departamento = Departamento.objects.get(texto=valor)
			self.en_departamento = False
		elif self.en_origen_legislativo:
			try:
				self.model.origen_legislativo = OrigenLegislativo.objects.create(texto=valor)
			except IntegrityError:
				self.model.origen_legislativo = OrigenLegislativo.objects.get(texto=valor)
			self.en_origen_legislativo = False
		elif self.en_materia:
			materia = None
			try:
				materia = Materia.objects.create(texto=valor)
			except IntegrityError:
				materia = Materia.objects.get(texto=valor)
			self.materias.append( materia )
			self.en_materia = False
		elif self.en_alerta:
			alerta = None
			try:
				alerta = Alerta.objects.create(texto=valor)
			except IntegrityError:
				alerta = Alerta.objects.get(texto=valor)
			self.alertas.append( alerta )
			self.en_alerta = False
	def alerta_modelo(self):
		#Calculamos las expresiones regulares que aciertan
		all_re = ExpresionRegular.objects.filter(Q(a_titulo__isnull=False) | Q(a_texto__isnull=False))
		en_titulo = []
		en_texto = []
		for re_exp in all_re:
			reexp = re.compile(re_exp.re_exp, re.UNICODE|re.IGNORECASE)
			#TODO ver si no hace falta buscar porque ya se va a notificar
			es_titulo = False
			es_texto = False
			if ReglaA.objects.filter( Q(re_titulo__isnull=False) ).count() > 0:
				es_titulo = True
			if ReglaA.objects.filter( Q(re_texto__isnull=False) ).count() > 0:
				es_texto = True

			if es_titulo and reexp.search(self.titulo):
				en_titulo.append(re_exp)
			if es_texto and reexp.search(self.texto):
				en_texto.append(re_exp)

		to_alert = ReglaA.objects.filter(
			Q(rango__isnull=True) | Q(rango=self.model.rango),
			Q(departamento__isnull=True) | Q(departamento=self.model.departamento),
			Q(origen_legislativo__isnull=True) | Q(origen_legislativo=self.model.origen_legislativo),
			Q(materias__isnull=True) | Q(materias__in=self.materias),
			Q(alertas__isnull=True) | Q(alertas__in=self.alertas),
			Q(re_titulo__isnull=True) | Q(re_titulo__in=en_titulo),
			Q(re_texto__isnull=True) | Q(re_texto__in=en_texto)
		)
		for subregla in to_alert:
			try:
				AlertaUsuario.objects.get(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)
			except AlertaUsuario.DoesNotExist:
				AlertaUsuario.objects.create(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)

class BoeBParser(BoeTexto):
	def __init__(self, boe):
		BoeTexto.__init__(self, boe, ReglaB)
		self.en_departamento = False
		self.en_materias_cpv = False

	def handle_starttag(self, tag, attrs):
		if tag == 'fecha_publicacion':
			self.en_fecha = True
		elif tag == 'departamento':
			self.en_departamento = True
		elif tag == 'materias_cpv':
			self.en_materias_cpv = True
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_endtag(self, tag):
		if tag == 'fecha_publicacion':
			self.en_fecha = False
		elif tag == 'departamento':
			self.en_departamento = False
		elif tag == 'materias_cpv':
			self.en_materias_cpv = False
		elif (self.en_texto or self.en_titulo) and tag == 'img':
			self.malformado = True
	def handle_data(self, data):
		valor = data.strip().lower()
		if self.en_departamento:
			try:
				self.model.departamento = Departamento.objects.create(texto=valor)
			except IntegrityError:
				self.model.departamento = Departamento.objects.get(texto=valor)
			self.en_departamento = False
		elif self.en_materias_cpv:
			try:
				self.model.materias_cpv = MateriasCPV.objects.create(texto=valor)
			except IntegrityError:
				self.model.materias_cpv = MateriasCPV.objects.get(texto=valor)
			self.en_materias_cpv = False
	def alerta_modelo(self):
		#Calculamos las expresiones regulares que aciertan
		all_re = ExpresionRegular.objects.filter(Q(b_titulo__isnull=False) | Q(b_texto__isnull=False))
		en_titulo = []
		en_texto = []
		for re_exp in all_re:
			reexp = re.compile(re_exp.re_exp, re.UNICODE|re.IGNORECASE)
			#TODO ver si no hace falta buscar porque ya se va a notificar
			es_titulo = False
			es_texto = False
			if ReglaB.objects.filter( Q(re_titulo__isnull=False) ).count() > 0:
				es_titulo = True
			if ReglaB.objects.filter( Q(re_texto__isnull=False) ).count() > 0:
				es_texto = True
			if es_titulo and reexp.search(self.titulo):
				en_titulo.append(re_exp)
			if es_texto and reexp.search(self.texto):
				en_texto.append(re_exp)

		to_alert = ReglaB.objects.filter(
			Q(departamento__isnull=True) | Q(departamento=self.model.departamento),
			Q(materias_cpv__isnull=True) | Q(materias_cpv=self.model.materias_cpv),
			Q(re_titulo__isnull=True) | Q(re_titulo__in=en_titulo),
			Q(re_texto__isnull=True) | Q(re_texto__in=en_texto)
		)
		for subregla in to_alert:
			try:
				AlertaUsuario.objects.get(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)
			except AlertaUsuario.DoesNotExist:
				AlertaUsuario.objects.create(boe=self.boe, regla=subregla.regla, user=subregla.regla.user)

def boe2parser(boe_id):
	if isinstance(boe_id, Boe):
		boe_id = boe_id.boe
	constructor = None
	if boe_id.startswith('BOE-A'):
		constructor = BoeAParser
	elif boe_id.startswith('BOE-B'):
		constructor = BoeBParser
	elif boe_id.startswith('BOE-S'):
		constructor = BoeSParser
	if constructor is None:
		return
	try:
		boe_id = Boe.objects.get(boe=boe_id)
	except Boe.DoesNotExist:
		boe_id = Boe.objects.create(boe=boe_id)
	return constructor(boe_id)
