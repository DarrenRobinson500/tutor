import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# .env lives at project root (tutor/), one level above backend/
load_dotenv(BASE_DIR.parent / '.env')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

DEBUG = os.getenv("DEBUG", "true").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Stripe
STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_placeholder")
STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET", "")

ALLOWED_HOSTS = ["*", "healthcheck.railway.app"]

CSRF_TRUSTED_ORIGINS = [
    "https://www.subject-matter.com.au",
]
for _csrf_key in ("FRONTEND_URL", "CUSTOM_FRONTEND", "BACKEND_URL"):
    _csrf_val = os.getenv(_csrf_key, "").rstrip("/")
    if _csrf_val:
        CSRF_TRUSTED_ORIGINS.extend([v.strip() for v in _csrf_val.split(",")])
del _csrf_key, _csrf_val

CUSTOM_DOMAIN = os.getenv("CUSTOM_DOMAIN")
if CUSTOM_DOMAIN:
    ALLOWED_HOSTS.append(CUSTOM_DOMAIN)

if DEBUG:
    ALLOWED_HOSTS.extend(["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    'backend',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'django_celery_beat',
    'django_celery_results',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "backend.User"

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOW_CREDENTIALS = True

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    _cors_origins = [
        "https://greenlearning.vercel.app",
        "https://subject-matter.com.au",
        "https://www.subject-matter.com.au",
    ]
    for _env_key in ("FRONTEND_URL", "CUSTOM_FRONTEND", "CORS_ALLOWED_ORIGINS"):
        _val = os.getenv(_env_key, "").rstrip("/")
        if _val:
            _cors_origins.extend([v.strip() for v in _val.split(",")])
    CORS_ALLOWED_ORIGINS = list(dict.fromkeys(_cors_origins))

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

FRONTEND_URL = os.getenv("FRONTEND_URL")
CUSTOM_FRONTEND = os.getenv("CUSTOM_FRONTEND")

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
USE_I18N = True
TIME_ZONE = "Australia/Sydney"
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_ROOT = BASE_DIR / "staticfiles" / "frontend"
if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_DIRS = []
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    CSRF_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SAMESITE = "None"
else:
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'http')

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Celery
from celery.schedules import crontab

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TIMEZONE = "Australia/Sydney"
CELERY_ENABLE_UTC = False

CELERY_BEAT_SCHEDULE = {
    'run-sms-jobs': {
        'task': 'backend.tasks.run_sms_jobs',
        'schedule': 60.0,
    },
    'create-post-session-jobs': {
        'task': 'backend.tasks.create_post_session_jobs',
        'schedule': 300.0,
    },
    'send-session-reminders': {
        'task': 'backend.tasks.send_session_reminders',
        'schedule': 1800.0,  # every 30 minutes
    },
    'flag-overdue-tutor-reviews': {
        'task': 'backend.tasks.flag_overdue_tutor_reviews',
        'schedule': crontab(hour=8, minute=0),  # 8am UTC = 6pm AEST
    },
    'create-weekly-session-jobs': {
        'task': 'backend.tasks.create_weekly_session_jobs',
        'schedule': crontab(hour=20, minute=0),  # 8pm UTC = 6am AEST
    },
    'record-weekly-progress-snapshots': {
        'task': 'backend.tasks.record_weekly_progress_snapshots',
        'schedule': crontab(hour=12, minute=0, day_of_week='sunday'),  # 12pm UTC = 10pm AEST Sunday
    },
}

# Email
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_USE_TLS = not EMAIL_USE_SSL
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "SubjectMatter <noreply@subjectmatter.app>")

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
if SENDGRID_API_KEY:
    EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
    ANYMAIL = {"SENDGRID_API_KEY": SENDGRID_API_KEY}
    if 'anymail' not in INSTALLED_APPS:
        INSTALLED_APPS.append('anymail')

# SMS (ClickSend)
SMS_SEND = os.environ.get("SMS_SEND")
CLICKSEND_USERNAME = os.environ.get("CLICKSEND_USERNAME")
CLICKSEND_API_KEY = os.environ.get("CLICKSEND_API_KEY")
CLICKSEND_FROM_NUMBER = os.environ.get("CLICKSEND_FROM_NUMBER")
