from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect

from boe.web.forms import PerfilForm
from boe.web.models import Perfil

@csrf_protect
@login_required
def perfil(request):
    perfil = get_object_or_404(Perfil, user=request.user)
    form = PerfilForm(instance=perfil)
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        form.user = request.user
        if form.is_valid():
            model = form.save(commit=False)
            model.user = request.user
            model.save()
    context = {
        'form':form,
        'perfil':perfil
    }
    return render_to_response('boe/perfil.html', context, RequestContext(request))
