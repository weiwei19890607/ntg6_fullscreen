#!/usr/bin/env python3
"""Exercise generated-fstab repair without touching the host's actual mounts."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'configs/initramfs/zz-cp2cl-overlay-fstab'

class BootFstab(unittest.TestCase):
    def run_hook(self, text, overlay):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'etc').mkdir();(root/'etc/fstab').write_text(text)
            if overlay:
                baseline=root/'media/root-ro/etc';baseline.mkdir(parents=True)
                (baseline/'fstab').write_text('persistent baseline must be untouched\n')
            subprocess.run(['sh',str(HOOK)],env={**os.environ,'rootmnt':str(root)},check=True)
            if overlay:
                self.assertEqual((baseline/'fstab').read_text(),'persistent baseline must be untouched\n')
            return (root/'etc/fstab').read_text()

    def test_overlay_remount_does_not_repeat_immutable_layers(self):
        boot='PARTUUID=test /boot/firmware vfat defaults,ro 0 2\n'
        root='/media/root-ro/ / overlay lowerdir=/media/root-ro/,upperdir=/media/root-rw/overlay,workdir=/media/root-rw/work 0 1\n'
        self.assertEqual(self.run_hook('# comment\n'+root+boot,True),
                         '# comment\n/media/root-ro/ / overlay defaults 0 1\n'+boot)

    def test_writable_maintenance_fstab_is_unchanged(self):
        text='PARTUUID=test / ext4 defaults,noatime 0 1\n'
        self.assertEqual(self.run_hook(text,False),text)

    def test_prerequisite_is_the_package_overlay_hook(self):
        self.assertEqual(subprocess.check_output(['sh',str(HOOK),'prereqs'],text=True).strip(),'overlayroot')

if __name__=='__main__': unittest.main(verbosity=2)
