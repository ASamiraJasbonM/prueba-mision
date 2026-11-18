"""Regenerate provisioned dashboard and rules; no network or secrets."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
REQUESTS = '{job="datapulse"} | json | event="request" | __error__=""'
PANELS = [
    ('Top IPs: login 401 (15 min)', f'topk(10, sum by (ip) (count_over_time({REQUESTS} | path="/api/auth/login/" | status=401 [15m])))'),
    ('5xx por endpoint (60 min)', f'sum by (path) (count_over_time({REQUESTS} | status>=500 [1h]))'),
    ('p95 duración ms por endpoint', f'quantile_over_time(0.95, {REQUESTS} | unwrap duracion_ms | __error__="" [1h]) by (path)'),
    ('Errores sync por país y operación', 'sum by (pais, operacion) (count_over_time({job="datapulse"} | json | event="sync_error" | __error__="" [1h]))'),
]
RULES = [
    ('brute_force_login', f'sum by (ip) (count_over_time({REQUESTS} | path="/api/auth/login/" | status=401 [1m]))', 4),
    ('privilege_escalation_attempt', 'sum(count_over_time({job="datapulse"} | json | event="privilege_escalation_attempt" | __error__="" [5m]))', 0),
    ('mass_conflict', f'sum by (usuario_id) (count_over_time({REQUESTS} | status=409 [5m]))', 9),
    ('error_5xx_burst', f'sum(count_over_time({REQUESTS} | status>=500 [5m])) / sum(count_over_time({REQUESTS} [5m]))', 0.05),
    ('audit_chain_broken', 'sum(count_over_time({job="datapulse"} | json | event="audit_verification" | ok="false" | __error__="" [5m]))', 0),
]


def main():
    panels = [{'id': i + 1, 'type': 'timeseries', 'title': title,
        'datasource': {'type': 'loki', 'uid': 'loki'},
        'gridPos': {'x': (i % 2) * 12, 'y': (i // 2) * 9, 'w': 12, 'h': 9},
        'targets': [{'refId': 'A', 'expr': expression, 'queryType': 'range'}]} for i, (title, expression) in enumerate(PANELS)]
    dashboard = {'uid': 'datapulse-security', 'title': 'DataPulse Security', 'schemaVersion': 41,
        'version': 1, 'refresh': '10s', 'time': {'from': 'now-1h', 'to': 'now'}, 'panels': panels}
    (ROOT / 'ops/grafana/dashboards/datapulse.json').write_text(json.dumps(dashboard, indent=2) + '\n', encoding='utf-8')
    rules = []
    for title, expression, threshold in RULES:
        rules.append({'uid': title, 'title': title, 'condition': 'B', 'for': '0s',
            'noDataState': 'OK', 'execErrState': 'Error',
            'labels': {'service': 'datapulse', 'severity': 'warning'},
            'annotations': {'summary': title + ': revisar docs/IR.md; confirmar antes de contener.'},
            'data': [
                {'refId': 'A', 'relativeTimeRange': {'from': 600, 'to': 0}, 'datasourceUid': 'loki',
                 'model': {'refId': 'A', 'expr': expression, 'queryType': 'instant', 'instant': True, 'intervalMs': 1000, 'maxDataPoints': 43200}},
                {'refId': 'B', 'relativeTimeRange': {'from': 0, 'to': 0}, 'datasourceUid': '__expr__',
                 'model': {'refId': 'B', 'type': 'classic_conditions', 'conditions': [{
                     'evaluator': {'type': 'gt', 'params': [threshold]}, 'operator': {'type': 'and'},
                     'query': {'params': ['A']}, 'reducer': {'type': 'last', 'params': []}, 'type': 'query'}]}}
            ]})
    output = {'apiVersion': 1, 'groups': [{'orgId': 1, 'name': 'datapulse', 'folder': 'DataPulse', 'interval': '1m', 'rules': rules}]}
    (ROOT / 'ops/grafana/rules.yaml').write_text(yaml.safe_dump(output, sort_keys=False), encoding='utf-8')


if __name__ == '__main__':
    main()
