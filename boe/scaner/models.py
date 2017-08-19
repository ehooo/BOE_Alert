from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User
from boe.core.models import Regla


class Boe(models.Model):
    boe = models.CharField(max_length=20, unique=True)
    fecha = models.DateField(auto_now_add=True)
    error = models.BooleanField(default=False)
    error_text = models.CharField(max_length=254, null=True, blank=True)
    celery_task = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        return self.boe


class AlertaUsuario(models.Model):
    user = models.ForeignKey(User, related_name='alertas')
    regla = models.ForeignKey(Regla)
    boe = models.ForeignKey(Boe, related_name='+')
    enviado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(null=True, blank=True)
