"""
Django settings for config project (グループ10 卒業制作 / みまもりケアリング).

Secrets and server-specific values come from environment variables,
so nothing sensitive is stored in this public repository.
"""

import os
from pathlib import Path

from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent


# --- Security (values come from environment variables on the server) ---
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-not-for-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")


# --- Applications ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'accounts',
    'preregister',
    'schedule',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Shared templates (base.html, index.html) live in <repo>/templates/
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

WSGI_APPLICATION = 'config.wsgi.application'


# --- Database ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# --- Authentication ---
# Our own User model (email login + role). Must be set before the first migrate.
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'index'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'index'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Language / time ---
LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True


# --- Static files ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Bootstrap uses "danger" for errors; Django calls it "error".
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}


# --- Web Push (VAPID) ---
# Secrets are NOT written in the code. They come from environment variables,
# so they never end up in git.
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
# Contact address sent to the push service. Change it to the team's address if you like.
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:group10@example.com")

# Allow logins and forms through the Cloudflare quick-tunnel HTTPS address.
# The "*" matches the random name that changes on every tunnel start.
CSRF_TRUSTED_ORIGINS = ["https://*.trycloudflare.com"]