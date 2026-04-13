"""
Django settings for cloudchat project.
AWS Services integrated:
  1. EC2    — Hosting Django app
  2. RDS    — PostgreSQL database
  3. S3     — Store chat export files
  4. IAM    — Secure access (no hardcoded keys)
  5. CloudWatch — Logging
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────
# CORE
# ──────────────────────────────────────────────
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'unsafe-secret-key')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    'localhost 127.0.0.1 13.60.91.12'
).split()

# ──────────────────────────────────────────────
# APPS
# ──────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'accounts',
    'chat',
    'profiles',

    'rest_framework',
    'channels',
]

# ──────────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cloudchat.urls'

# ──────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ──────────────────────────────────────────────
# WSGI / ASGI
# ──────────────────────────────────────────────
WSGI_APPLICATION = 'cloudchat.wsgi.application'
ASGI_APPLICATION = 'cloudchat.asgi.application'

# ──────────────────────────────────────────────
# DATABASE (RDS + SQLite fallback)
# ──────────────────────────────────────────────
_USE_RDS = bool(os.environ.get('RDS_HOST'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql' if _USE_RDS else 'django.db.backends.sqlite3',
        'NAME': os.environ.get('RDS_DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.environ.get('RDS_USER'),
        'PASSWORD': os.environ.get('RDS_PASSWORD'),
        'HOST': os.environ.get('RDS_HOST'),
        'PORT': os.environ.get('RDS_PORT', '5432'),
    }
}

# ──────────────────────────────────────────────
# PASSWORD VALIDATION
# ──────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ──────────────────────────────────────────────
# I18N
# ──────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────
# STATIC & MEDIA
# ──────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ──────────────────────────────────────────────
# AWS S3 CONFIG (SAFE)
# ──────────────────────────────────────────────
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

AWS_STORAGE_BUCKET_NAME = "erp-exports-cloudchat-app"
AWS_S3_REGION_NAME = "eu-north-1"

AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False

# ──────────────────────────────────────────────
# EMAIL (SMTP)
# ──────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# ──────────────────────────────────────────────
# CLOUDWATCH LOGGING
# ──────────────────────────────────────────────
_CW_ENABLED = bool(os.environ.get('CLOUDWATCH_ENABLED'))

_handlers = ['console']
_handlers_config = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    }
}

if _CW_ENABLED:
    _handlers.append('cloudwatch')
    _handlers_config['cloudwatch'] = {
        'class': 'watchtower.CloudWatchLogHandler',
        'log_group': 'cloudchat-logs',
        'stream_name': 'django-app',
        'formatter': 'verbose',
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },

    'handlers': _handlers_config,

    'loggers': {
        'django': {
            'handlers': _handlers,
            'level': 'INFO',
            'propagate': False,
        },
        'cloudchat_app': {
            'handlers': _handlers,
            'level': 'INFO',
            'propagate': False,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'