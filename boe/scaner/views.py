from django.conf import settings
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from celery.task.control import inspect
from datetime import date
import httplib
import logging

from boe.scaner.parser import BoeDiaParser
from boe.scaner.utils import wget_url
from boe.scaner.tasks import procesa_boe, procesa
from boe.scaner.models import Boe
from djcelery.models import TaskMeta
from kombu.transport.django.models import Message
from celery.states import ALL_STATES

from django.shortcuts import render_to_response
from django.shortcuts import get_object_or_404
from django.template import RequestContext


@login_required
def alertas(request):
    '''
    perfil = get_object_or_404(Perfil, user=request.user)
    print request.user.alertas.all()
    print request.user.alertas.count()
    lista_alertas = AlertaUsuario.objects.filter(user=request.user)
    print lista_alertas
    #'''
    return render_to_response('boe/alertas.html', {}, RequestContext(request))


@login_required
def run_hoy(request):
    hoy = date.today()
    boe_parser = BoeDiaParser(hoy)
    boes = Boe.objects.filter(fecha=hoy, boe__startswith='BOE-S')
    if boes.count() > 0:
        return redirect('boescan:run_boe', boes[0].boe)
    else:
        (contenido, headers, estado) = wget_url(boe_parser.url, settings.PROXY)
        if estado == httplib.OK:
            boe_parser.feed(contenido.decode('utf-8', 'replace'))
            if boe_parser.boe:
                boe_id = Boe.objects.create(boe=boe_parser.boe, fecha=hoy)
                return redirect('boescan:run_boe', boe_parser.boe)
        logging.info("Respuesta %s Cabezeras %s" % (estado, headers))
    raise Http404


@login_required
def run_boe(request, boe_id):
    boe_obj = get_object_or_404(Boe, boe=boe_id)
    result = None
    if not boe_obj.celery_task:
        result = procesa_boe(boe_id)
    else:
        result = procesa.AsyncResult(boe_obj.celery_task)

    context = {
        'boe': boe_obj,
        'result': result
    }
    return render_to_response('boe/scaner.html', context, RequestContext(request))


# @login_required
def status(request):
    response_data = {}

    if request.user.is_staff:
        i = inspect()
        response_data['active'] = i.active()
        response_data['stats'] = i.stats()

        boes_error = Boe.objects.filter(error=True)
        response_data['error'] = []
        for er in boes_error.all():
            response_data['error'].append({
                'error_text': er.error_text,
                # 'task':er.celery_task,
                'boe': er.boe
            })

    msgs = Message.objects.filter(queue__name="celery")
    response_data['tasks'] = msgs.count()
    response_data['tasks_done'] = 0
    import json, base64
    for msg in msgs.all():
        payload = json.loads(msg.payload)
        task_id = payload['properties']['correlation_id']
        body = payload['body']
        if payload['properties']['body_encoding'] == 'base64':
            body = base64.b64decode(body)
        try:
            if procesa.AsyncResult(task_id).status == 'SUCCESS':
                response_data['tasks_done'] += 1
                '''
                print payload
                print task_id
                print body,"\n"
                #'''
        except:
            '''
            print payload
            print task_id
            print body,"\n"
            #'''
            pass

    for taskstatus in ALL_STATES:
        response_data[taskstatus.lower()] = TaskMeta.objects.filter(status=taskstatus).count()

    if response_data['failure'] > 0:
        response_data['failure_tasks'] = []
        failtasks = TaskMeta.objects.filter(status='FAILURE')
        for task in failtasks:
            response_data['failure_tasks'].append({
                'task_id': task.task_id
                , 'traceback': task.traceback
            })
    return HttpResponse(json.dumps(response_data), content_type="application/json")
