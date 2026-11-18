def security_responses(result, generator, request, public):
    error = {'description': 'Error uniforme. 429: throttled o account_locked; 400: captcha_required o validation_error.',
             'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ErrorResponse'}}}}
    result.setdefault('components', {}).setdefault('schemas', {})['ErrorResponse'] = {
        'type': 'object', 'properties': {'error': {'type': 'object', 'properties': {
            'code': {'type': 'string'}, 'message': {'type': 'string'}, 'details': {}}}}}
    for path, methods in result.get('paths', {}).items():
        for method, operation in methods.items():
            if method not in {'get', 'post', 'put', 'delete', 'patch'}:
                continue
            operation.setdefault('responses', {}).setdefault('429', {**error, 'headers': {
                'Retry-After': {'schema': {'type': 'integer'}, 'description': 'Segundos de espera.'}}})
            if path.startswith('/api/auth/') and method == 'post':
                operation['responses'].setdefault('400', error)
                operation['responses'].setdefault('401', error)
            if path in {'/api/paises/sync-indicadores/', '/api/riesgo/calcular/'}:
                operation.setdefault('parameters', []).append({'in': 'header', 'name': 'Idempotency-Key',
                    'required': False, 'schema': {'type': 'string', 'maxLength': 128},
                    'description': 'Por usuario y endpoint; mismo cuerpo durante 5 minutos. Otro cuerpo: 409.'})
    return result
