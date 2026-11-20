"""Supervise HTTP and the queue worker as one deployable service, without a broker."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    environment = {**os.environ, 'SYNC_WORKER_REQUIRED': 'True'}
    workers = os.environ.get('WEB_CONCURRENCY', '2')
    children = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(subprocess.Popen([sys.executable, 'backend/manage.py', 'procesar_sincronizaciones'],
            cwd=ROOT, env=environment))
        children.append(subprocess.Popen([sys.executable, '-m', 'gunicorn', 'scripts.render_wsgi:application',
            '--bind', '0.0.0.0:' + os.environ.get('PORT', '8000'), '--workers', workers,
            '--timeout', '60', '--forwarded-allow-ips=127.0.0.1'], cwd=ROOT, env=environment))
        while not stopping and all(child.poll() is None for child in children):
            time.sleep(1)
        return 0 if stopping else 1
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == '__main__':
    sys.exit(main())
