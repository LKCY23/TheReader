"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import logging
from backend.middleware import get_current_request

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-x$5#vj&-v1_w(c$-8yr5lx3-sli5+1ph=@%z=1^nm9(u$)+@6o'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# 允许所有主机访问
ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'backend.apps.BackendConfig',
    'api',
    'constance',
    'constance.backends.database'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'backend.middleware.RequestMiddleware',
    'backend.middleware.IPAddressMiddleware',
    'backend.middleware.RequestLoggingMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'build'],
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

WSGI_APPLICATION = 'backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'persist' / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

class RequestBasicInformation(logging.Filter):
    def filter(self, record):
        ip = None
        upn = None

        request = get_current_request()
        if request:
            # 收集IP
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0]
            else:
                ip = request.META.get("REMOTE_ADDR")

            # 收集用户upn
            user_claims = request.session.get("auth_claims", None)
            if user_claims:
                upn = user_claims["oid"]

        # 追加日志信息
        if ip:
            record.ip = ip
        else:
            record.ip = "N/A"
        if upn:
            record.upn = upn
        else:
            record.upn = "N/A"
            
        # 过滤器允许数据通过
        return True

import os
LOG_DIR = BASE_DIR / 'persist'
if not LOG_DIR.exists():
    os.makedirs(LOG_DIR, exist_ok=True)  # 仅当路径不存在时才创建

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_info': {
            '()': 'backend.settings.RequestBasicInformation',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {ip:->15} {upn:->20} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} {levelname} {message}',
            'style': '{'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'filters': ['request_info'],
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'persist' / 'debug.log',
            'level': 'INFO',
            'formatter': 'verbose',
            'mode': 'a',
            'encoding': 'utf-8',
            'maxBytes': 15 * 1024 * 1024, # 15MB
            'backupCount': 5,
            'filters': ['request_info'],
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

PERSIST_DIR = BASE_DIR / 'persist'

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'build' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 全局环境变量字典
GLOBAL_ENV = {}

DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB

# 设置CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# 增加安全设置
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Constance 配置
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_CONFIG = {
    'GUEST_CAN_VIEW': (True, '游客是否可以查看文档'),
    'GUEST_CAN_UPLOAD': (True, '游客是否可以上传文档'),
    'GUEST_CAN_DELETE': (True, '游客是否可以删除文档'),
    'GUEST_CAN_USE_API': (True, '游客是否可以使用API'),
    'SUPERUSER_PASSWORD': ('', '超级用户密码'),
}

CONSTANCE_CONFIG_FIELDSETS = {
    '游客权限设置': ('GUEST_CAN_VIEW', 'GUEST_CAN_UPLOAD', 'GUEST_CAN_DELETE', 'GUEST_CAN_USE_API'),
    '超级用户设置': ('SUPERUSER_PASSWORD',),
}
