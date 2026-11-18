"""Exercise the actual HTTP app and enforce the offline control boundary."""
import json, os, shlex, pathlib, subprocess, time, urllib.request, urllib.error, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
BIN=pathlib.Path(os.environ.get('CP2CL_BINARY',ROOT/'artifacts/cp2cl-native'))
COMMAND=shlex.split(os.environ.get('CP2CL_RUNNER',''))+[str(BIN)]
class Offline(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.proc=subprocess.Popen(COMMAND+['--offline-web'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  for _ in range(100):
   if cls.proc.poll() is not None: raise RuntimeError(cls.proc.stderr.read().decode())
   try:
    with urllib.request.urlopen('http://127.0.0.1:18080/api/status',timeout=1): break
   except OSError: time.sleep(.05)
  else: cls.proc.terminate();raise RuntimeError('HTTP startup timed out')
 @classmethod
 def tearDownClass(cls):
  cls.proc.terminate();cls.proc.communicate(timeout=5)
 def test_read_only_check(self):
  result=json.loads(subprocess.check_output(COMMAND+['--check']))
  self.assertEqual(result['mode'],'read_only_check')
  self.assertFalse(result['real_carplay_verified'])
  self.assertIsNone(result['config']['screen']['width'])
 def test_web_assets_and_json(self):
  for path in ['/','/vendor/weui.min.css','/api/status','/api/settings','/api/channels','/api/system']:
   with self.subTest(path=path),urllib.request.urlopen('http://127.0.0.1:18080'+path) as r:
    self.assertEqual(r.status,200)
    data=r.read();self.assertTrue(data)
    if path.startswith('/api/'):json.loads(data)
 def test_mutations_unavailable(self):
  for path in ['/api/settings','/api/reset','/api/restart','/api/reboot','/api/system/maintenance','/api/system/normal','/api/system/poweroff']:
   with self.subTest(path=path):
    req=urllib.request.Request('http://127.0.0.1:18080'+path,data=b'{}',headers={'Content-Type':'application/json'})
    with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
    self.assertIn(e.exception.code,(404,405))
    e.exception.close()
if __name__=='__main__':unittest.main(verbosity=2)
