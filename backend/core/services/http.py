import json
from decimal import Decimal
import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def reject_constant(value):
    raise ValueError('Número JSON no finito.')


def get_json(url, params=None, headers=None):
    retry = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=['GET'], respect_retry_after_header=False)
    with requests.Session() as session:
        session.mount('https://', HTTPAdapter(max_retries=retry))
        response = session.get(url, params=params, headers=headers, timeout=settings.EXTERNAL_API_TIMEOUT)
        response.raise_for_status()
        return json.loads(response.text, parse_float=Decimal, parse_constant=reject_constant)
