import os

# Django settings for uiapi project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Muharem Hrnjadovic', 'muharem@openquake.org'),
)

MANAGERS = ADMINS


# PLEASE NOTE: do *not* ever use any of the password below in production !!

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'HOST': '',
        'PORT': '',
    },
}


def dbn():
    """The name of the db as well as the db user ceredential to use."""
    return dict(
        NAME=os.environ.get("OQ_MTAPI_DB", "mtapi"),
        USER=os.environ.get("OQ_MTAPI_USER", "oq_uiapi_writer"),
        PASSWORD=os.environ.get("OQ_MTAPI_PASSWORD"))


DATABASES["default"].update(dbn())

# PLEASE NOTE: do *not* ever use any of the password above in production !!

OQ_ROOT = "/usr/openquake"
OQ_UPLOAD_DIR = os.path.join(OQ_ROOT, "spool")
OQ_ENGINE_DIR = os.path.join(OQ_ROOT, "engine")
OQ_APIAPP_DIR = os.path.join(OQ_ROOT, "apiapp")

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Zurich'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/var/www/openquake/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'tu%+*x)8p270f!witb5y36_2mtua80oga1o-$*jezm+l)ps#y('

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'geonode.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django.contrib.gis',
    'geonode.mtapi')

NRML_RUNNER_PATH = "%s/bin/nrml_runner.py" % OQ_APIAPP_DIR
OQRUNNER_PATH = "%s/bin/oqrunner.py" % OQ_APIAPP_DIR

import sys
APIAPP_PYTHONPATH = ":".join(
    [seg for seg in sys.path if seg.find("geonode") < 0])
APIAPP_PYTHONPATH += ":%s:%s" % (OQ_ENGINE_DIR, OQ_APIAPP_DIR)

SITEURL = "http://gemsun02.ethz.ch/"
GEOSERVER_BASE_URL = SITEURL + "geoserver-geonode-dev/"
