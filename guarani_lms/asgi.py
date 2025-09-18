# guarani_lms/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "guarani_lms.settings")
application = get_asgi_application()