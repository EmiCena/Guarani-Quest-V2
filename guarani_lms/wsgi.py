# guarani_lms/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "guarani_lms.settings")
application = get_wsgi_application()