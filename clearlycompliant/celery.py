import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clearlycompliant.settings')

app = Celery('clearlycompliant')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()