"""
Django settings for config project.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, True))
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-3u=)ib3e&)5iizw)h(j+nqke9ec=0s95npor3^-uxxb76t=$_c",
)

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

RAILWAY_PUBLIC_DOMAIN = env("RAILWAY_PUBLIC_DOMAIN", default=None)
if RAILWAY_PUBLIC_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)
    CSRF_TRUSTED_ORIGINS = [f"https://{RAILWAY_PUBLIC_DOMAIN}"]

ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")

# Shopify push (Phase 3). Store is the *.myshopify.com subdomain, token is an
# Admin API access token. Leave blank to disable the Push to Shopify button.
SHOPIFY_STORE = env("SHOPIFY_STORE", default="")
SHOPIFY_ACCESS_TOKEN = env("SHOPIFY_ACCESS_TOKEN", default="")
SHOPIFY_API_VERSION = env("SHOPIFY_API_VERSION", default="2026-04")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "catalog",
    "arrangements",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# Falls back to local sqlite when DATABASE_URL isn't set (local dev);
# Railway's Postgres plugin provides DATABASE_URL in deployed environments.

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}


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


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files (invoice photos, arrangement photos)
# Local dev falls back to the FileSystemStorage above. In production, set the
# AWS_* env vars below and media is stored in a private S3 bucket, served via
# short-lived signed URLs. (Railway's own filesystem is ephemeral, so uploads
# must not live on local disk in production.)
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

AWS_S3_BUCKET_NAME = env("AWS_S3_BUCKET_NAME", default="")
if AWS_S3_BUCKET_NAME:
    _s3_options = {
        "bucket_name": AWS_S3_BUCKET_NAME,
        "region_name": env("AWS_DEFAULT_REGION", default="us-east-1"),
        # Private objects served through expiring signed URLs.
        "querystring_auth": True,
        "querystring_expire": env.int("AWS_S3_URL_EXPIRE", default=3600),
        "signature_version": "s3v4",
        # Buckets with ACLs disabled (bucket-owner-enforced) reject an ACL, so
        # don't send one — access is governed by the bucket policy.
        "default_acl": None,
        # Don't silently overwrite two uploads that share a name.
        "file_overwrite": False,
    }
    # An S3-compatible endpoint (Railway bucket / MinIO / etc.) needs its URL
    # passed through, and generally requires path-style addressing rather than
    # AWS's virtual-hosted style. Omit both to talk to real AWS S3.
    _s3_endpoint = env("AWS_ENDPOINT_URL", default="")
    if _s3_endpoint:
        _s3_options["endpoint_url"] = _s3_endpoint
        _s3_options["addressing_style"] = "path"
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": _s3_options,
    }
    # boto3 reads AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from the environment.

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "arrangement-list"
LOGOUT_REDIRECT_URL = "login"

if not DEBUG:
    # Railway terminates TLS at its edge and forwards to the app over plain
    # HTTP, so trust its X-Forwarded-Proto header — otherwise SECURE_SSL_REDIRECT
    # never sees a "secure" request and loops forever (ERR_TOO_MANY_REDIRECTS).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
