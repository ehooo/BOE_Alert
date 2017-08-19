from django.conf.urls import url
from boe.core.views import *

urlpatterns = [
    url(r'^reglas/$', reglas, name='reglas'),
    url(r'^regla/add/(?P<rule_type>\w+)/$', add_regla, name='add_regla'),
    url(r'^regla/details/(?P<regla_id>\d+)/$', details_regla, name='details_regla'),
    # url(r'^regla/details/(?P<alias>\w+)/$', 'details_regla', name='details_regla'),
]
