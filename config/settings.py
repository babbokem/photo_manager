import os
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
import logging

# Carica il file .env
load_dotenv()

# Legge il valore di DEBUG da .env e lo converte in un booleano
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Mostra nel terminale cosa sta leggendo
print(f"🔹 DEBUG: {DEBUG}")
print(f"🔹 DATABASE_URL LETTA: {os.getenv('DATABASE_URL')}")

# Configurazione del database
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'photo_manager_db',
            'USER': 'postgres',
            'PASSWORD': 'Datasei@2011',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
    }

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "photomanager-production.up.railway.app",  # Dominio Railway
    ".railway.app",  # Per accettare altri sottodomini di Railway
]

CSRF_TRUSTED_ORIGINS = [
    'https://photomanager-production.up.railway.app',  # Sostituisci con il tuo dominio Railway
    'http://127.0.0.1:8000'  # Per test locali
]

CSRF_COOKIE_SECURE = True  # Abilita per connessioni HTTPS
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_SECURE = False  # Per sviluppo locale
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 1500

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = "x4n-$ouyj(=)158ozlda&a+%9l#(g@qo9f%1)(ycv8sq+owd=_ey"

# Installed apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'event_photos',  # App personalizzata
    'storages',  # Django storages per S3 (puoi rimuoverlo se non usi S3)
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

# Root URL configuration
ROOT_URLCONF = "config.urls"

# Templates configuration
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
                'event_photos.context_processors.cart_context',  # ✅ Aggiunto
            ],
        },
    },
]

# WSGI application
WSGI_APPLICATION = "config.wsgi.application"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Configurazione statici
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configurazione dei file media
# Sempre definito, anche se non usato con S3
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Configurazione S3
# Configurazione S3 (attiva solo se USE_S3 è true)
if os.getenv("USE_S3", "False").lower() == "true":
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'eu-west-1')
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
    AWS_QUERYSTRING_AUTH = False
    AWS_DEFAULT_ACL = 'public-read'
    print("🧪 S3 CONFIGURATO")
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')




#else:
#    MEDIA_URL = '/media/'
#    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Percorso locale per lo sviluppo

# Definizione delle sotto-cartelle dentro MEDIA_ROOT
EVENT_ZIPS_DIR = os.path.join(MEDIA_ROOT, 'event_zips')  # ZIP caricati
EVENT_PHOTOS_DIR = os.path.join(MEDIA_ROOT, 'event_photos')  # Foto estratte dagli ZIP
TEMP_ZIPS_DIR = os.path.join(MEDIA_ROOT, 'temp')  # ZIP generati per il download

# Creazione automatica delle cartelle se non esistono
for directory in [EVENT_ZIPS_DIR, EVENT_PHOTOS_DIR, TEMP_ZIPS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Assicurati che la directory temp esista
TEMP_DIR = os.path.join(MEDIA_ROOT, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

LOGIN_URL = '/login/'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Usa il server SMTP del tuo provider email
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'massimiliano.cima@gmail.com'
EMAIL_HOST_PASSWORD = 'efys itmu rlyr gutj'

# Stripe Configuration
STRIPE_PUBLIC_KEY = "pk_test_51PWGkOP6vStwNJaKuajaYtnldX0jAwFSF5MGVOBwR9vorQ1a93qtPTU8chavspfc2Mjd6HAsTqj1k4t0kgeeqniW00FzmTo9zo"  # Inserisci la tua chiave pubblica
STRIPE_SECRET_KEY = "sk_test_51PWGkOP6vStwNJaKkAqFIsSuLlMXtw6zsBuqo5LyUqnzZ6zOmcKYwpNuNYValyuS4qna4YcGh5mBmmD3wRQEIUKg00DlzmWgIx"  # Inserisci la tua chiave segreta

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
