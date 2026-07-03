import os

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'service-a-dev-secret-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'service_a.urls'
WSGI_APPLICATION = 'service_a.wsgi.application'

DATABASES = {}

APPEND_SLASH = False
USE_I18N = False
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Test runner that does not require a database
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
