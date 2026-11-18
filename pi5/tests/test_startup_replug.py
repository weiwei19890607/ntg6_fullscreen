#!/usr/bin/env python3
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'scripts/startup-replug.py'
spec = importlib.util.spec_from_file_location('startup_replug', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
READY = {'carlife': {'usb': {'enumerated': True}, 'protocol': None, 'session_up': False},
         'carplay': {'video': {'active': True}, 'airplay': {'verified': True}}}


class StartupReplug(unittest.TestCase):
    def test_zero_delay_triggers_on_the_first_ready_observation(self):
        policy = module.Decision(settle=0)
        self.assertEqual(policy.observe(READY, 0), 'replug')

    def test_phone_and_usb_must_both_be_ready_and_stable(self):
        policy = module.Decision()
        self.assertEqual(policy.observe(READY, 0), 'wait')
        self.assertEqual(policy.observe(READY, 2.9), 'wait')
        offline = copy.deepcopy(READY)
        offline['carlife']['usb']['enumerated'] = False
        self.assertEqual(policy.observe(offline, 3), 'wait')
        self.assertEqual(policy.observe(READY, 4), 'wait')
        self.assertEqual(policy.observe(READY, 7), 'replug')

    def test_any_handshake_or_session_prevents_disconnection(self):
        for field, value in [('protocol', [2, 0]), ('challenge', '384_1.0.0'),
                             ('session_up', True), ('encoding', True)]:
            status = copy.deepcopy(READY)
            status['carlife'][field] = value
            self.assertEqual(module.Decision().observe(status, 100), 'car_started')

    def test_stale_video_without_authenticated_airplay_is_not_ready(self):
        status = copy.deepcopy(READY)
        status['carplay']['airplay']['verified'] = False
        policy = module.Decision()
        self.assertEqual(policy.observe(status, 0), 'wait')
        self.assertEqual(policy.observe(status, 100), 'wait')

    def test_network_error_restarts_readiness_grace(self):
        policy = module.Decision()
        policy.observe(READY, 0)
        policy.unavailable()
        self.assertEqual(policy.observe(READY, 10), 'wait')
        self.assertEqual(policy.observe(READY, 13), 'replug')

    def exercise(self, first=None, final_handshake=False, fail_post=False):
        now = [0.0]
        calls = []
        def fetch(base, path, post=False):
            calls.append((path, post))
            if post:
                if fail_post: raise OSError('uncertain HTTP response')
                return {'ok': True}
            status = copy.deepcopy(first or READY)
            if final_handshake and len(calls) == 3:
                status['carlife']['protocol'] = [2, 0]
            return status
        def sleep(delay): now[0] += delay
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder)/'attempted'
            kwargs = dict(marker=marker, settle=0.5, wait=2, fetch=fetch,
                          clock=lambda: now[0], sleep=sleep)
            module.run('http://test', **kwargs)
            # Restarting the helper in the same boot must not send another POST.
            module.run('http://test', **kwargs)
            return calls, marker.read_text() if marker.exists() else None

    def test_exactly_one_request_even_when_helper_is_restarted(self):
        calls, marker = self.exercise()
        self.assertEqual([c for c in calls if c[1]], [('/api/restart', True)])
        self.assertEqual(marker, 'automatic_usb_replug\n')

    def test_uncertain_response_does_not_retry(self):
        calls, marker = self.exercise(fail_post=True)
        self.assertEqual(len([c for c in calls if c[1]]), 1)
        self.assertIsNotNone(marker)

    def test_handshake_starting_at_final_check_cancels_request(self):
        calls, marker = self.exercise(final_handshake=True)
        self.assertFalse(any(post for _, post in calls))
        self.assertEqual(marker, 'car_started\n')

    def test_preexisting_connection_disarms_the_entire_boot(self):
        status = copy.deepcopy(READY)
        status['carlife']['session_up'] = True
        calls, marker = self.exercise(first=status)
        self.assertEqual(calls, [('/api/status', False)])
        self.assertEqual(marker, 'car_started\n')

    def test_timeout_without_phone_does_not_request_replug(self):
        calls, marker = self.exercise(first={'carlife': {}, 'carplay': {}})
        self.assertFalse(any(post for _, post in calls))
        self.assertIsNone(marker)

if __name__ == '__main__': unittest.main(verbosity=2)
