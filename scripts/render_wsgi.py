"""Render-only WSGI adapter exposing release identity on the health response."""
import os
import re

from config.wsgi import application as django_application


def application(environ, start_response):
    commit = os.environ.get('RENDER_GIT_COMMIT', '')
    if environ.get('PATH_INFO') != '/api/health/' or not re.fullmatch(r'[0-9a-f]{40}', commit):
        return django_application(environ, start_response)

    def release_response(status, headers, exc_info=None):
        return start_response(status, [*headers, ('X-Deployment-Commit', commit)], exc_info)

    return django_application(environ, release_response)
