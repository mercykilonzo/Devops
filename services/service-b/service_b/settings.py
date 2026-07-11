import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'service-b-dev-secret-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django_prometheus',
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'service_b.urls'
WSGI_APPLICATION = 'service_b.wsgi.application'

DATABASES = {}

APPEND_SLASH = False
USE_I18N = False
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
