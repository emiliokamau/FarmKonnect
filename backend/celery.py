# backend/celery.py
import os
from celery import Celery

# set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmkonnect.settings')

app = Celery('farmkonnect')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Example beat schedule (run every 6 hours)
app.conf.beat_schedule = {
    'fetch-market-prices-every-6h': {
        'task': 'etl.tasks.fetch_and_save_market_prices',
        'schedule': 6 * 60 * 60,  # seconds
    },
}
