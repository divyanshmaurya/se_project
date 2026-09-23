from django.http import HttpResponse


class HealthCheckMiddleware:
    """Answer ``/healthz/`` before host validation.

    Load balancers (e.g. Elastic Beanstalk) probe instances by private IP,
    which is not in ALLOWED_HOSTS, so the probe must short-circuit here.
    """

    path = "/healthz/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == self.path:
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)
