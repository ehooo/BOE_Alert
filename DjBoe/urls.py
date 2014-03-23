from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse

from django.contrib import admin
from django.views.generic.base import TemplateView
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', TemplateView.as_view(template_name='acerca.html'), name="acerca"),
    url('', include('boe.core.urls', namespace='boe')),
    url('', include('boe.web.urls')),
    url('', include('boe.scaner.urls', namespace='boescan')),
    url('', include('social.apps.django_app.urls', namespace='social')),
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns('django.contrib.auth.views',
    url(r'^login/$', 'login', { 'template_name': 'registration/login.html' }, name='login' ),
    url(r'^logout/$', 'logout', name='logout' ),
)