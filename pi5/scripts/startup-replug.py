#!/usr/bin/env python3
"""One USB re-enumeration per boot, after the phone is ready but CarLife is not.

Uses the same local API as the web restart button. Never restarts cp2cl or the
phone; a volatile marker also prevents repeats after helper/service restarts.
"""
import json
import os
from pathlib import Path
import time
from urllib.request import Request, build_opener, ProxyHandler

CONFIG = Path('/etc/cp2cl/startup-replug.json')
MARKER = Path('/run/cp2cl-startup/attempted')
OPENER = build_opener(ProxyHandler({}))


class Decision:
    def __init__(self, settle=3):
        self.settle = settle
        self.ready_since = None

    def observe(self, status, now):
        car = status.get('carlife', {})
        phone = status.get('carplay', {})
        # Any protocol exchange is enough: do not interrupt authentication or
        # reconnect a previously working background session.
        if (car.get('protocol') is not None or car.get('challenge') is not None
                or car.get('session_up') or car.get('encoding')):
            return 'car_started'
        ready = (car.get('usb', {}).get('enumerated') is True
                 and phone.get('video', {}).get('active') is True
                 and phone.get('airplay', {}).get('verified') is True)
        if not ready:
            self.ready_since = None
            return 'wait'
        if self.ready_since is None:
            self.ready_since = now
        return 'replug' if now-self.ready_since >= self.settle else 'wait'

    def unavailable(self):
        self.ready_since = None


def claim(marker, reason):
    """Reserve before POST: an uncertain response must not cause a second replug."""
    try:
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, 'w') as f:
        f.write(reason+'\n')
    return True


def request(base, path, post=False):
    req = Request(base+path, data=b'' if post else None,
                  method='POST' if post else 'GET')
    with OPENER.open(req, timeout=2) as response:
        return json.load(response)


def run(base, marker=MARKER, settle=0, wait=180, fetch=request,
        clock=time.monotonic, sleep=time.sleep):
    if marker.exists():
        print('startup_replug skipped=already_handled_this_boot', flush=True)
        return
    policy = Decision(settle)
    deadline = clock()+wait
    print(f'startup_replug waiting=phone_video_and_usb settle_s={settle} timeout_s={wait}', flush=True)
    while clock() < deadline:
        try:
            action = policy.observe(fetch(base, '/api/status'), clock())
        except (OSError, ValueError, TypeError, AttributeError):
            policy.unavailable()
            sleep(0.5)
            continue
        if action == 'car_started':
            claim(marker, 'car_started')
            print('startup_replug skipped=carlife_already_started', flush=True)
            return
        if action == 'replug':
            # Check again immediately before committing the one attempt.
            try:
                checked = policy.observe(fetch(base, '/api/status'), clock())
                if checked == 'car_started':
                    claim(marker, 'car_started')
                    print('startup_replug skipped=carlife_started_before_request', flush=True)
                    return
                if checked != 'replug':
                    continue
            except (OSError, ValueError, TypeError, AttributeError):
                policy.unavailable()
                continue
            if not claim(marker, 'automatic_usb_replug'):
                return
            print('startup_replug requesting=usb_replug reason=phone_ready_car_not_started attempt=1', flush=True)
            try:
                answer = fetch(base, '/api/restart', post=True)
                if answer.get('ok') is not True:
                    raise ValueError('restart not acknowledged')
                print('startup_replug accepted=true; actual_NTG6_result_requires_car_test', flush=True)
            except (OSError, ValueError, TypeError, AttributeError) as error:
                print(f'startup_replug response_uncertain={type(error).__name__} retry=false', flush=True)
            return
        sleep(0.5)
    print('startup_replug skipped=readiness_timeout', flush=True)


def main():
    if not CONFIG.exists() or json.loads(CONFIG.read_text()).get('enabled') is not True:
        print('startup_replug disabled=true', flush=True)
        return
    config = json.loads(Path('/etc/cp2cl/config.json').read_text())
    if not config.get('early_connect'):
        print('startup_replug disabled=early_connect_required', flush=True)
        return
    # The Pi management API binds this local address, not localhost.
    run('http://192.168.4.1', marker=MARKER)


if __name__ == '__main__':
    main()
