"""
ASGI config for api project.

It exposes the ASGI callable as a module-level variable named ``application``.

Served by uvicorn (see compose/start). In DEBUG the application is wrapped
with ASGIStaticFilesHandler so static assets (admin, DRF browsable API) keep
working under uvicorn the same way runserver used to serve them.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings.local')

application = get_asgi_application()

from django.conf import settings  # noqa: E402

if settings.DEBUG:
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

    application = ASGIStaticFilesHandler(application)
