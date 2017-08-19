from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from social.apps.django_app.default.models import UserSocialAuth
import logging

User._meta.get_field('email')._unique = False
User._meta.get_field('username')._unique = True


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)


post_save.connect(create_user_profile, sender=User)


class Perfil(models.Model):
    user = models.OneToOneField(User, related_name='boe_auth')
    envia_twitter = models.BooleanField(default=False)
    envia_email = models.BooleanField(default=False)
    envia_web = models.BooleanField(default=True)

    def __unicode__(self):
        return self.user.username

    def has_twitter(self):
        try:
            return UserSocialAuth.objects.get(user=self.user, provider="twitter")
        except UserSocialAuth.DoesNotExist:
            logging.debug("No Twitter")
            return None

    def has_email(self):
        try:
            return UserSocialAuth.objects.get(user=self.user, provider="email")
        except UserSocialAuth.DoesNotExist:
            logging.debug("No Email")
            return None
