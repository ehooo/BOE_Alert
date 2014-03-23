from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse
from django.db.models import Q

from boe.core.forms import ReglaForm
from boe.core.forms import ReglaSForm
from boe.core.forms import ReglaAForm
from boe.core.forms import ReglaBForm
from boe.core.forms import ReglaRapidaForm
from boe.core.models import Regla
from boe.core.models import ReglaA
from boe.core.models import ReglaB
from boe.core.models import ReglaS
from boe.core.models import ExpresionRegular

@login_required
def reglas(request, rule_type=None):
    context = {
        'cls_basico':'active',
        'cls_avanzado':''
    }
    context['regla_form'] = ReglaForm()
    context['rapida_form'] = ReglaRapidaForm()
    context['s_form'] = ReglaSForm()
    context['a_form'] = ReglaAForm()
    context['b_form'] = ReglaBForm()
    context['reglas'] = Regla.objects.filter(user=request.user)

    '''
    t = ExpresionRegular.objects.filter(s_titulo__isnull=False)
    context['testing'] = []
    for re_exp in t:
        context['testing'].append( re_exp.s_titulo.filter(regla__alertausuario__regla__isnull=True) )
    #'''
    return render_to_response('boe/reglas.html', context, RequestContext(request))

@csrf_protect
@login_required
def add_regla(request, rule_type=None):
    context = {
        'cls_basico':'',
        'cls_avanzado':''
    }
    context['regla_form'] = ReglaForm()
    context['rapida_form'] = ReglaRapidaForm()
    context['s_form'] = ReglaSForm()
    context['a_form'] = ReglaAForm()
    context['b_form'] = ReglaBForm()
    if request.method == 'POST':
        form = None
        if rule_type == "A":
            context['a_form'] = ReglaAForm(request.POST)
            form = context['a_form']
        elif rule_type == "B":
            context['b_form'] = ReglaBForm(request.POST)
            form = context['b_form']
        elif rule_type == "S":
            context['s_form'] = ReglaSForm(request.POST)
            form = context['s_form']
        elif rule_type == "rapida":
            context['rapida_form'] = ReglaRapidaForm(request.POST)
            form = context['rapida_form']
        if form and form.is_valid():
            if rule_type in ['A','B','S']:
                context['regla_form'] = ReglaForm(request.POST)
                if context['regla_form'].is_valid():
                    regla = context['regla_form'].save(True, request.user)
                    subregla = form.save(True, regla)
                    return redirect('boe:reglas')
                context['cls_avanzado'] = 'active'
            else:
                regla = form.save(True, request.user)
                rexpresion = form.cleaned_data["expresion"]
                ReglaS.objects.create(regla=regla, re_titulo=rexpresion)
                ReglaA.objects.create(re_texto=rexpresion, regla=regla)
                ReglaA.objects.create(re_titulo=rexpresion, regla=regla)
                ReglaB.objects.create(re_texto=rexpresion, regla=regla)
                ReglaB.objects.create(re_titulo=rexpresion, regla=regla)
                return redirect('boe:reglas')
    context['reglas'] = Regla.objects.filter(user=request.user)
    if context['cls_avanzado'] == '':
        context['cls_basico'] = 'active'
    return render_to_response('boe/reglas.html', context, RequestContext(request))
        
    return HttpResponse("Hello, world. You're at the poll index.")

@csrf_protect
@login_required
def details_regla(request, regla_id):
    regla = get_object_or_404(Regla, pk=regla_id, user=request.user)
    if request.method == 'POST':
        for id in request.POST.getlist('borrara[]'):
            try:
                dregla = ReglaA.objects.get(pk=id, regla=regla)
                dregla.delete()
            except ReglaA.DoesNotExist:
                pass
        for id in request.POST.getlist('borrarb[]'):
            try:
                dregla = ReglaB.objects.get(pk=id, regla=regla)
                dregla.delete()
            except ReglaB.DoesNotExist:
                pass
        for id in request.POST.getlist('borrars[]'):
            try:
                dregla = ReglaS.objects.get(pk=id, regla=regla)
                dregla.delete()
            except ReglaS.DoesNotExist:
                pass

    context = { 'regla':regla }
    return render_to_response('boe/detalles.html', context, RequestContext(request))


