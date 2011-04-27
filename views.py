from django.http import HttpResponse
import simplejson

def upload(request):
    result = dict(
        status="success", msg="Model upload successful",
        ruptures=[2, 3, 4], sources=[2,3,4])
    return HttpResponse(simplejson.dumps(result))
