from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from django import forms

from boe.web.models import Perfil


class PerfilForm(forms.ModelForm):
    error_messages = {
        'no_twitter': _("No hay cuenta de Twitter asociada."),
        'no_email': _("No hay cuenta de email asociada."),
        'no_user': _("No existe el usuario."),
    }

    class Meta:
        model = Perfil
        exclude = ('user',)

    def get_perfil(self):
        try:
            return Perfil.objects.get(user=self.user)
        except Perfil.DoesNotExist:
            raise forms.ValidationError(
                self.error_messages['no_user'],
                code='no_user',
            )

    def clean_envia_twitter(self):
        perfil = self.get_perfil()
        envia_twitter = self.cleaned_data["envia_twitter"]
        if envia_twitter and perfil:
            if not perfil.has_twitter():
                self.cleaned_data["envia_twitter"] = False
                raise forms.ValidationError(
                    self.error_messages['no_twitter'],
                    code='no_twitter',
                )
        return envia_twitter

    def clean_envia_email(self):
        perfil = self.get_perfil()
        envia_email = self.cleaned_data["envia_email"]
        if envia_email and perfil:
            if not perfil.has_email():
                self.cleaned_data["envia_email"] = False
                raise forms.ValidationError(
                    self.error_messages['no_email'],
                    code='no_email',
                )
        return envia_email

    def save(self, commit=True):
        perfil = super(PerfilForm, self).save(commit=False)
        if perfil.has_twitter():
            perfil.envia_twitter = self.cleaned_data["envia_twitter"]
        else:
            perfil.envia_twitter = False
        if perfil.has_email():
            perfil.envia_email = self.cleaned_data["envia_email"]
        else:
            perfil.envia_email = False
        perfil.envia_web = self.cleaned_data["envia_web"]

        if commit:
            perfil.save()
        return perfil
