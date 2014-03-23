from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

from social.pipeline.partial import partial
import logging

@partial
def check_email(strategy, details, user=None, is_new=False, *args, **kwargs):
    password = None
    try:
        password = kwargs.get('request').POST['password']
    except:
        pass
    if not user and password and details['email'].find('@') > 0:
        try:
            user = User.objects.get(email = details['email'])
        except User.DoesNotExist:
            details['password'] = make_password(password)
    if user and user.email:
        request = kwargs.get('request')
        if request and request.POST and 'password' in request.POST:
            if not is_new:
                if not user.check_password(request.POST['password']):
                    logging.warn("PASWORD WRONG for %s"%(user))
                    return redirect('login')
    return {'user': user, 'is_new': user is None}
