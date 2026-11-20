"""CI release verification; standard library only, no production dependencies."""
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

BACKEND = 'https://datapulse-backend-vkc5.onrender.com'
FRONTEND = 'https://datapulse-latam.pages.dev'
# Pages rejects urllib's generic default signature (Cloudflare error 1010).
# Identify this authorized application explicitly; do not imitate a browser.
REQUEST_HEADERS = {'User-Agent': 'DataPulse-Release-Verifier/1.0', 'Cache-Control': 'no-cache'}


def release_hook(hook, commit):
    url = urlsplit(hook)
    if (url.scheme != 'https' or url.hostname != 'api.render.com'
            or not url.path.startswith('/deploy/') or url.username or url.password or url.fragment):
        raise ValueError('Invalid Render deploy hook configuration.')
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A full commit SHA is required.')
    query = [(key, value) for key, value in parse_qsl(url.query) if key != 'ref']
    query.append(('ref', commit))
    return urlunsplit((url.scheme, url.netloc, url.path, urlencode(query), ''))


def trigger_render(hook, commit):
    request = Request(release_hook(hook, commit), headers=REQUEST_HEADERS, method='POST')
    try:
        with urlopen(request, timeout=60) as response:
            if response.status not in (200, 202):
                raise RuntimeError('Render did not accept the deployment.')
    except HTTPError as exc:
        # Never interpolate exceptions: they can contain the secret hook URL.
        raise RuntimeError(f'Render deploy hook returned HTTP {exc.code}.') from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError('Unable to contact the Render deploy hook.') from None
    print('Render accepted the exact-commit deployment; waiting for the live release.', flush=True)


def render_ready(commit):
    request = Request(BACKEND + '/api/health/?release=' + commit,
                      headers=REQUEST_HEADERS)
    with urlopen(request, timeout=45) as response:
        if response.status != 200 or response.headers.get('X-Deployment-Commit') != commit:
            return False
    request = Request(BACKEND + '/api/ready/?release=' + commit, headers=REQUEST_HEADERS)
    with urlopen(request, timeout=15) as response:
        return response.status == 200 and response.headers.get('X-Deployment-Commit') == commit


def pages_ready(commit):
    request = Request(FRONTEND + '/deployment.json?release=' + commit,
                      headers=REQUEST_HEADERS)
    with urlopen(request, timeout=30) as response:
        if response.status != 200 or json.load(response).get('commit') != commit:
            return False
    with urlopen(Request(FRONTEND + '/login', headers=REQUEST_HEADERS), timeout=30) as response:
        html = response.read().decode('utf-8')
        policy = response.headers.get('Content-Security-Policy', '')
        return (response.status == 200 and '<app-root' in html and BACKEND in policy
                and "script-src 'self'" in policy and 'unsafe-eval' not in policy)


def wait_for_release(check, commit, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check(commit):
                print(f'Live release verified: {commit}', flush=True)
                return
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            pass  # Cold starts, rolling deploys, and stale HTML are retried within a bound.
        print('Waiting for the expected live commit...', flush=True)
        time.sleep(10)
    raise RuntimeError('The expected release did not become healthy before the deadline.')


def main():
    commit = os.environ['GITHUB_SHA']
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('A full commit SHA is required.')
    if sys.argv[1:] == ['render']:
        trigger_render(os.environ['RENDER_DEPLOY_HOOK_URL'], commit)
        wait_for_release(render_ready, commit, 1200)
    elif sys.argv[1:] == ['wait-render']:
        wait_for_release(render_ready, commit, 1200)
    elif sys.argv[1:] == ['pages']:
        wait_for_release(pages_ready, commit, 240)
    else:
        raise ValueError('Usage: deploy_pipeline.py render|wait-render|pages')


if __name__ == '__main__':
    try:
        main()
    except (KeyError, ValueError, RuntimeError) as error:
        print(f'Deployment failed: {error}', file=sys.stderr)
        sys.exit(1)
