from .settings import *  # noqa: F403


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test-db.sqlite3',  # noqa: F405
    },
}
