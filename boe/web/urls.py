from django.conf.urls import patterns, url

urlpatterns = patterns('boe.web.views',
    #url(r'^$', views.acerca, name='acerca'),
    url(r'^perfil/$', 'perfil', name='perfil'),
)
