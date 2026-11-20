import importlib.util
import os
from pathlib import Path
import types
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from scripts import deploy_pipeline as deployment

COMMIT = 'a' * 40


class DeploymentTests(unittest.TestCase):
    def test_hook_pins_validated_commit_and_preserves_secret(self):
        url = deployment.release_hook('https://api.render.com/deploy/srv-example?key=private&ref=old', COMMIT)
        self.assertEqual(parse_qs(urlsplit(url).query), {'key': ['private'], 'ref': [COMMIT]})

    def test_hook_rejects_other_destinations_and_invalid_commit(self):
        for hook in ('http://api.render.com/deploy/srv-a', 'https://evil.test/deploy/srv-a',
                     'https://user:password@api.render.com/deploy/srv-a'):
            with self.subTest(hook=hook), self.assertRaises(ValueError):
                deployment.release_hook(hook, COMMIT)
        with self.assertRaises(ValueError):
            deployment.release_hook('https://api.render.com/deploy/srv-a?key=private', 'main')

    def test_hook_errors_never_expose_secret_url(self):
        hook = 'https://api.render.com/deploy/srv-a?key=private'
        error = HTTPError(hook, 401, 'Unauthorized', {}, None)
        with patch.object(deployment, 'urlopen', side_effect=error):
            with self.assertRaisesRegex(RuntimeError, '^Render deploy hook returned HTTP 401.$') as caught:
                deployment.trigger_render(hook, COMMIT)
        self.assertNotIn('private', str(caught.exception))

    def test_healthy_old_backend_is_not_a_successful_release(self):
        response = MagicMock(status=200, headers={'X-Deployment-Commit': 'b' * 40})
        response.__enter__.return_value = response
        with patch.object(deployment, 'urlopen', return_value=response):
            self.assertFalse(deployment.render_ready(COMMIT))
            response.headers['X-Deployment-Commit'] = COMMIT
            self.assertTrue(deployment.render_ready(COMMIT))

    def test_pages_requires_live_artifact_identity(self):
        response = MagicMock(status=200)
        response.__enter__.return_value = response
        response.read.return_value = '{"commit": "old"}'
        with patch.object(deployment, 'urlopen', return_value=response) as fetch:
            self.assertFalse(deployment.pages_ready(COMMIT))
            self.assertEqual(fetch.call_count, 1)

    def test_readiness_timeout_is_a_failure(self):
        with patch.object(deployment.time, 'monotonic', side_effect=[0, 1, 20]), \
                patch.object(deployment.time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'did not become healthy'):
                deployment.wait_for_release(lambda commit: False, COMMIT, timeout=10)


class RenderWsgiTests(unittest.TestCase):
    def adapter(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'application/json')])
            return [b'{}']

        module = types.ModuleType('config.wsgi')
        module.application = app
        path = Path(__file__).resolve().parents[1] / 'render_wsgi.py'
        spec = importlib.util.spec_from_file_location('render_adapter_test', path)
        adapter = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'config': types.ModuleType('config'), 'config.wsgi': module}):
            spec.loader.exec_module(adapter)
        return adapter

    def test_health_preserves_response_and_exposes_platform_commit(self):
        adapter = self.adapter()
        start = MagicMock()
        with patch.dict(os.environ, {'RENDER_GIT_COMMIT': COMMIT}):
            self.assertEqual(adapter.application({'PATH_INFO': '/api/health/'}, start), [b'{}'])
        self.assertEqual(start.call_args.args[0], '200 OK')
        self.assertIn(('X-Deployment-Commit', COMMIT), start.call_args.args[1])

    def test_other_routes_and_invalid_metadata_remain_unchanged(self):
        adapter = self.adapter()
        for path, commit in [('/api/paises/', COMMIT), ('/api/health/', 'bad\r\nheader')]:
            start = MagicMock()
            with self.subTest(path=path), patch.dict(os.environ, {'RENDER_GIT_COMMIT': commit}):
                adapter.application({'PATH_INFO': path}, start)
            self.assertEqual(start.call_args.args[1], [('Content-Type', 'application/json')])
