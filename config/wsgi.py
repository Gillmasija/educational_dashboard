"""
WSGI config for educational dashboard project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Get the WSGI application for the Django project
application = get_wsgi_application()
