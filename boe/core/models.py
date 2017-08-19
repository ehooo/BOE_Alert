from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from django.db import models
from django.contrib.auth.models import User
import re


class RegexValidator(object):
    def __init__(self, *arg, **karg):
        print arg
        print karg
        pass

    """
    Validates that the input are regular expression.
    """

    def __call__(self, value):
        try:
            re.compile(value)
        except:
            raise ValidationError(_("Not valid Regular Expresion."), code=_('re_error'))


class ExpresionRegular(models.Model):
    re_exp = models.CharField(max_length=254, unique=True, validators=[RegexValidator])

    def __unicode__(self):
        return self.re_exp


class Seccion(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class Departamento(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class Epigrafe(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class OrigenLegislativo(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class Materia(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class MateriasCPV(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class Alerta(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class Rango(models.Model):
    texto = models.CharField(max_length=200, unique=True)

    def __unicode__(self):
        return self.texto


class Regla(models.Model):
    user = models.ForeignKey(User, related_name='reglas')
    alias = models.CharField(max_length=200)
    malformado = models.BooleanField(default=False)

    def __unicode__(self):
        return self.alias


class ReglaS(models.Model):
    regla = models.ForeignKey(Regla, related_name='s')
    re_titulo = models.ForeignKey(ExpresionRegular, related_name='s_titulo', blank=True, null=True)
    seccion = models.ForeignKey(Seccion, related_name='+', blank=True, null=True)
    departamento = models.ForeignKey(Departamento, related_name='+', blank=True, null=True)
    epigrafe = models.ForeignKey(Epigrafe, related_name='+', blank=True, null=True)

    def __unicode__(self):
        return self.regla.alias


class ReglaA(models.Model):
    regla = models.ForeignKey(Regla, related_name='a')
    re_titulo = models.ForeignKey(ExpresionRegular, related_name='a_titulo', blank=True, null=True)
    re_texto = models.ForeignKey(ExpresionRegular, related_name='a_texto', blank=True, null=True)
    rango = models.ForeignKey(Rango, related_name='+', blank=True, null=True)
    departamento = models.ForeignKey(Departamento, related_name='+', blank=True, null=True)
    origen_legislativo = models.ForeignKey(OrigenLegislativo, related_name='+', blank=True, null=True)
    materias = models.ForeignKey(Materia, related_name='+', blank=True, null=True)
    alertas = models.ForeignKey(Alerta, related_name='+', blank=True, null=True)

    def __unicode__(self):
        return self.regla.alias


class ReglaB(models.Model):
    regla = models.ForeignKey(Regla, related_name='b')
    re_titulo = models.ForeignKey(ExpresionRegular, related_name='b_titulo', blank=True, null=True)
    re_texto = models.ForeignKey(ExpresionRegular, related_name='b_texto', blank=True, null=True)
    departamento = models.ForeignKey(Departamento, related_name='+', blank=True, null=True)
    materias_cpv = models.ForeignKey(MateriasCPV, related_name='+', blank=True, null=True)

    def __unicode__(self):
        return self.regla.alias
