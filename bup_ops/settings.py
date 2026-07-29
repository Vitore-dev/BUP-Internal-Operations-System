from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'azure_auth',

    # Our apps
    'accounts',
    'core',
    'hr',
    'finance',
    #'reception',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bup_ops.urls'

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
                'core.context_processors.user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'bup_ops.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Custom user model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Azure AD Authentication
AZURE_AUTH = {
    'CLIENT_ID': config('AZURE_AD_CLIENT_ID'),
    'CLIENT_SECRET': config('AZURE_AD_CLIENT_SECRET'),
    'TENANT_ID': config('AZURE_AD_TENANT_ID'),
    'AUTHORITY': f'https://login.microsoftonline.com/{config("AZURE_AD_TENANT_ID")}',
    'REDIRECT_URI': config('AZURE_AD_REDIRECT_URI'),
    'SCOPES': [ 'User.Read'],
    'PUBLIC_URLS': [],
    'USERNAME_ATTRIBUTE': 'preferred_username',
}

AUTHENTICATION_BACKENDS = [
    'azure_auth.backends.AzureBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/accounts/login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Azure AD Groups
AZURE_GROUPS = {
    'ADMIN':       config('GROUP_ADMIN'),
    'HR':          config('GROUP_HR'),
    'FINANCE':     config('GROUP_FINANCE'),
    #'RECEPTION':   config('GROUP_RECEPTION'),
    'DIRECTOR':    config('GROUP_DIRECTOR'),
    #'OPS_MANAGER': config('GROUP_OPS_MANAGER'),
    'PI':          config('GROUP_PI'),
}

# Email - Microsoft Graph
GRAPH_SENDER_EMAIL = config('GRAPH_SENDER_EMAIL', default='')

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalisation
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Gaborone'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SAGE_URL = config('SAGE_URL', default='#')
