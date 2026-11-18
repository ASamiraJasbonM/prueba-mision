"""Validate provisioned Grafana resources and every dashboard/rule LogQL query."""
import json
import os
from pathlib import Path
from time import sleep
import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    grafana = os.environ.get('GRAFANA_URL', 'http://127.0.0.1:13000')
    loki = os.environ.get('LOKI_URL', 'http://127.0.0.1:13100')
    auth = (os.environ.get('GRAFANA_ADMIN_USER', 'admin'), os.environ['GRAFANA_ADMIN_PASSWORD'])
    for _ in range(30):
        try:
            response = requests.get(grafana + '/api/health', timeout=3)
            if response.ok:
                break
        except requests.RequestException:
            pass
        sleep(1)
    response = requests.get(grafana + '/api/dashboards/uid/datapulse-security', auth=auth, timeout=10)
    response.raise_for_status()
    assert len(response.json()['dashboard']['panels']) == 4
    rules = requests.get(grafana + '/api/v1/provisioning/alert-rules', auth=auth, timeout=10)
    rules.raise_for_status()
    assert len(rules.json()) == 5
    dashboard = json.loads((ROOT / 'ops/grafana/dashboards/datapulse.json').read_text())
    provisioning = yaml.safe_load((ROOT / 'ops/grafana/rules.yaml').read_text())
    expressions = [p['targets'][0]['expr'] for p in dashboard['panels']]
    expressions += [r['data'][0]['model']['expr'] for r in provisioning['groups'][0]['rules']]
    for expression in expressions:
        response = requests.get(loki + '/loki/api/v1/query', params={'query': expression}, timeout=30)
        response.raise_for_status()
        assert response.json()['status'] == 'success', response.text
    count = 0
    for _ in range(30):
        rows = requests.get(loki + '/loki/api/v1/query_range', params={'query': '{job="datapulse"}', 'limit': 100}, timeout=30)
        rows.raise_for_status()
        count = sum(len(stream['values']) for stream in rows.json()['data']['result'])
        if count:
            break
        sleep(1)
    assert count > 0, 'No ingested data; capture real backend/DB logs first.'
    print(json.dumps({'dashboard_panels': 4, 'rules': 5, 'queries_validated': len(expressions), 'ingested_rows_sample': count}))


if __name__ == '__main__':
    main()
