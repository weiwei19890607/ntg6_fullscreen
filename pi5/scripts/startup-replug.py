#!/usr/bin/env python3
"""USB re-enumerations until CarLife starts: five fast tries, then slow retries.

Uses the same local API as the web restart button. Never restarts cp2cl or the
phone; a volatile marker prevents another retry series after helper/service restarts.
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


def device_request(base, path, post=False, udc_root=Path('/sys/class/udc')):
    answer = request(base, path, post=post)
    if not post and path == '/api/status':
        usb = answer.get('carlife', {}).get('usb', {})
        controller = usb.get('controller')
        if not isinstance(controller, str) or not controller or Path(controller).name != controller:
            raise ValueError('missing or invalid UDC controller')
        # The core's cached enumerated flag may stay true across a short
        # unbind/rebind. Read the kernel state to observe the actual cycle.
        usb['enumerated'] = (udc_root/controller/'state').read_text().strip() == 'configured'
    return answer


def run(base, marker=MARKER, settle=0, wait=None, fetch=request,
        clock=time.monotonic, sleep=time.sleep, fast_attempts=5,
        retry_interval=3, slow_interval=10, enumeration_timeout=15):
    if marker.exists():
        print('startup_replug skipped=already_handled_this_boot', flush=True)
        return
    policy = Decision(settle)
    deadline = None if wait is None else clock()+wait
    attempts = 0
    phase = 'ready'
    phase_deadline = None
    retry_at = None
    print(f'startup_replug waiting=phone_video_and_usb settle_s={settle} '
          f'readiness_timeout_s={wait} fast_attempts={fast_attempts} '
          f'retry_interval_s={retry_interval} slow_interval_s={slow_interval}', flush=True)
    while attempts or deadline is None or clock() < deadline:
        try:
            status = fetch(base, '/api/status')
            action = policy.observe(status, clock())
        except (OSError, ValueError, TypeError, AttributeError):
            policy.unavailable()
            if phase_deadline is not None and clock() >= phase_deadline:
                print('startup_replug waiting=usb_cycle retry_held=true', flush=True)
                phase_deadline = clock()+enumeration_timeout
            sleep(0.1)
            continue
        if action == 'car_started':
            if not attempts:
                claim(marker, 'car_started')
            print(f'startup_replug stopped=carlife_started attempts={attempts}', flush=True)
            return
        enumerated = status.get('carlife', {}).get('usb', {}).get('enumerated') is True
        if phase in ('disconnect', 'enumerate'):
            if clock() >= phase_deadline:
                print('startup_replug waiting=usb_cycle retry_held=true', flush=True)
                phase_deadline = clock()+enumeration_timeout
            if phase == 'disconnect' and not enumerated:
                phase = 'enumerate'
            elif phase == 'enumerate' and enumerated:
                phase = 'cooldown'
                phase_deadline = None
                retry_at = clock()+(retry_interval if attempts < fast_attempts else slow_interval)
                print(f'startup_replug enumerated=true attempt={attempts} '
                      f'handshake_wait_s={retry_interval if attempts < fast_attempts else slow_interval}', flush=True)
            sleep(0.1)
            continue
        if phase == 'cooldown':
            if not enumerated:
                # Do not count disconnected time as a handshake opportunity.
                retry_at = None
            elif retry_at is None:
                retry_at = clock()+(retry_interval if attempts < fast_attempts else slow_interval)
            if retry_at is None or clock() < retry_at:
                sleep(0.1)
                continue
        if action == 'replug':
            # Recheck immediately before requesting disconnection.
            try:
                checked = policy.observe(fetch(base, '/api/status'), clock())
                if checked == 'car_started':
                    if not attempts:
                        claim(marker, 'car_started')
                    print('startup_replug stopped=carlife_started_before_request', flush=True)
                    return
                if checked != 'replug':
                    sleep(0.1)
                    continue
            except (OSError, ValueError, TypeError, AttributeError):
                policy.unavailable()
                sleep(0.1)
                continue
            if not attempts and not claim(marker, 'automatic_usb_replug'):
                return
            attempts += 1
            print(f'startup_replug requesting=usb_replug '
                  f'reason=phone_ready_car_not_started attempt={attempts}', flush=True)
            try:
                answer = fetch(base, '/api/restart', post=True)
                if answer.get('ok') is not True:
                    raise ValueError('restart not acknowledged')
                print('startup_replug accepted=true', flush=True)
            except (OSError, ValueError, TypeError, AttributeError) as error:
                print(f'startup_replug response_uncertain={type(error).__name__} retry=false', flush=True)
                return
            # Require an observed disconnect/re-enumeration cycle. Never start
            # the handshake timer from the asynchronous POST response.
            phase = 'disconnect'
            phase_deadline = clock()+enumeration_timeout
            policy.unavailable()
        sleep(0.1)
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
    run('http://192.168.4.1', marker=MARKER, fetch=device_request)


if __name__ == '__main__':
    main()
