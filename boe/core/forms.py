from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User
from django.db import models
from django import forms

from boe.core.models import Regla
from boe.core.models import ReglaS
from boe.core.models import ReglaA
from boe.core.models import ReglaB
from boe.core.models import RegexValidator
from boe.core.models import ExpresionRegular


class ReglaForm(forms.ModelForm):
    class Meta:
        model = Regla
        exclude = ('user',)
    def save(self, commit=True, user=None):
        regla = None
        try:
            regla = Regla.objects.get(user=user, alias=self.cleaned_data["alias"])
        except Regla.DoesNotExist:
            regla = super(ReglaForm, self).save(commit=False)
            if commit:
                if user:
                    regla.user = user
                regla.save()
        return regla
class ReglaRapidaForm(forms.ModelForm):
    expresion = forms.CharField(max_length=254, validators=[RegexValidator])
    class Meta:
        model = Regla
        exclude = ('user',)
    def clean_expresion(self):
        ret = None
        if self.cleaned_data["expresion"]:
            try:
                ret = ExpresionRegular.objects.get(re_exp=self.cleaned_data["expresion"])
            except ExpresionRegular.DoesNotExist:
                ret = ExpresionRegular.objects.create(re_exp=self.cleaned_data["expresion"])
        return ret
    def save(self, commit=True, user=None):
        regla = None
        try:
            regla = Regla.objects.get(user=user, alias=self.cleaned_data["alias"])
        except Regla.DoesNotExist:
            regla = super(ReglaRapidaForm, self).save(commit=False)
            if commit:
                if user:
                    regla.user = user
                regla.save()
        return regla
class ReglaSForm(forms.ModelForm):
    titulo = models.CharField(max_length=254, unique=True, validators=[RegexValidator])
    class Meta:
        model = ReglaS
        exclude = ('regla', 're_titulo',)
    def save(self, commit=True, regla=None):
        subregla = super(ReglaSForm, self).save(commit=False)
        if commit:
            try:
                subregla.re_titulo = ExpresionRegular.objects.get(re_exp=self.cleaned_data["titulo"])
            except ExpresionRegular.DoesNotExist:
                subregla.re_titulo = ExpresionRegular.objects.create(re_exp=self.cleaned_data["titulo"])
            if regla:
                subregla.regla = regla
            subregla.save()
        return regla
class ReglaAForm(forms.ModelForm):
    titulo = models.CharField(max_length=254, unique=True, validators=[RegexValidator])
    texto = models.CharField(max_length=254, unique=True, validators=[RegexValidator])
    class Meta:
        model = ReglaA
        exclude = ('regla', 're_titulo', 're_texto',)
    def save(self, commit=True, regla=None):
        subregla = super(ReglaAForm, self).save(commit=False)
        if commit:
            try:
                subregla.re_titulo = ExpresionRegular.objects.get(re_exp=self.cleaned_data["titulo"])
            except ExpresionRegular.DoesNotExist:
                subregla.re_titulo = ExpresionRegular.objects.create(re_exp=self.cleaned_data["titulo"])
            try:
                subregla.re_texto = ExpresionRegular.objects.get(re_exp=self.cleaned_data["texto"])
            except ExpresionRegular.DoesNotExist:
                subregla.re_texto = ExpresionRegular.objects.create(re_exp=self.cleaned_data["texto"])
            if regla:
                subregla.regla = regla
            subregla.save()
        return regla
class ReglaBForm(forms.ModelForm):
    titulo = models.CharField(max_length=254, unique=True, validators=[RegexValidator])
    texto = models.CharField(max_length=254, unique=True, validators=[RegexValidator])
    class Meta:
        model = ReglaB
        exclude = ('regla', 're_titulo', 're_texto',)
    def save(self, commit=True, regla=None):
        subregla = super(ReglaBForm, self).save(commit=False)
        if commit:
            try:
                subregla.re_titulo = ExpresionRegular.objects.get(re_exp=self.cleaned_data["titulo"])
            except ExpresionRegular.DoesNotExist:
                subregla.re_titulo = ExpresionRegular.objects.create(re_exp=self.cleaned_data["titulo"])
            try:
                subregla.re_texto = ExpresionRegular.objects.get(re_exp=self.cleaned_data["texto"])
            except ExpresionRegular.DoesNotExist:
                subregla.re_texto = ExpresionRegular.objects.create(re_exp=self.cleaned_data["texto"])
            if regla:
                subregla.regla = regla
            subregla.save()
        return regla
