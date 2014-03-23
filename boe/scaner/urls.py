from django.conf.urls import patterns, url

urlpatterns = patterns('boe.scaner.views',
    url(r'^alertas/$', 'alertas', name='alertas'),

    url(r'^run/$', 'run_hoy', name='run'),
    url(r'^status/$', 'status', name='status'),
    url(r'^run/(?P<boe_id>BOE-[SAB][\d-]+)/$', 'run_boe', name='run_boe'),
)
