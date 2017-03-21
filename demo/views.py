from django.http import HttpResponse


def index(request):
    return HttpResponse('Hello world \n', content_type='text/plain')