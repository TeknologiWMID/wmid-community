import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if o]

# Di belakang reverse proxy HTTPS (Caddy/Nginx) yang mengirim X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.environ.get('SECURE_COOKIES', 'False') == 'True'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'directory',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wmid_community.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wmid_community.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ.get('DB_NAME',     'wmid_community'),
        'USER':     os.environ.get('DB_USER',     ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST':     os.environ.get('DB_HOST',     'localhost'),
        'PORT':     os.environ.get('DB_PORT',     '5432'),
    },
}

LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Wikimedia OAuth 2.0
WIKIMEDIA_CLIENT_ID = os.environ.get('WIKIMEDIA_CLIENT_ID', '')
WIKIMEDIA_CLIENT_SECRET = os.environ.get('WIKIMEDIA_CLIENT_SECRET', '')
WIKIMEDIA_REDIRECT_URI = os.environ.get('WIKIMEDIA_REDIRECT_URI', 'http://localhost:8000/oauth/callback/')
WIKIMEDIA_USER_AGENT = os.environ.get('WIKIMEDIA_USER_AGENT', 'WMID-Directory-Test/0.1')

WIKIMEDIA_AUTHORIZE_URL = 'https://meta.wikimedia.org/w/rest.php/oauth2/authorize'
WIKIMEDIA_TOKEN_URL = 'https://meta.wikimedia.org/w/rest.php/oauth2/access_token'
WIKIMEDIA_PROFILE_URL = 'https://meta.wikimedia.org/w/rest.php/oauth2/resource/profile'

DASHBOARD_API_BASE_URL = os.environ.get('DASHBOARD_API_BASE_URL', 'https://dashboard.wikimedia.or.id/api/v1')

CONTRIB_PROJECT = os.environ.get('CONTRIB_PROJECT', 'id.wikipedia.org')

MAX_WIKIS_TO_SYNC = int(os.environ.get('MAX_WIKIS_TO_SYNC', 30))
CONTRIBS_PER_WIKI = int(os.environ.get('CONTRIBS_PER_WIKI', 20))

# Wiki yang dicoba langsung jika CentralAuth tidak mengembalikan data merged.
# Format: "host" saja (tanpa https://).
FALLBACK_WIKIS = [
    'id.wikipedia.org',
    'commons.wikimedia.org',
    'www.wikidata.org',
    'meta.wikimedia.org',
    'en.wikipedia.org',
    'id.wikisource.org',
    'id.wiktionary.org',
    'www.wikimedia.org',
]
