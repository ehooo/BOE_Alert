from django.conf.urls import url
from boe.web.views import *

urlpatterns = [
    # url(r'^$', views.acerca, name='acerca'),
    url(r'^perfil/$', perfil, name='perfil'),
]
