import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/install_skills.py'
spec = importlib.util.spec_from_file_location('installer', SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class InstallTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)

    def test_dry_run_has_no_side_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'absent'
            result = self.run_cli('--target', target, '--all', '--dry-run')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.exists())

    def test_source_overlap_rejected(self):
        result = self.run_cli('--target', ROOT / 'skills', '--all', '--force')
        self.assertNotEqual(result.returncode, 0)

    def test_copy_failure_preserves_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'skill'
            dest.mkdir()
            (dest / 'old.txt').write_text('keep')
            with patch.object(installer.shutil, 'copytree', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    installer.install(ROOT / 'skills/wechat-miniapp-core', dest)
            self.assertEqual((dest / 'old.txt').read_text(), 'keep')

    def test_overwrite_failure_restores_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'skill'
            dest.mkdir()
            (dest / 'old.txt').write_text('keep')
            original = Path.rename
            def rename(path, target):
                if path.name == 'new':
                    raise OSError('rename failed')
                return original(path, target)
            with patch.object(Path, 'rename', rename):
                with self.assertRaises(OSError):
                    installer.install(ROOT / 'skills/wechat-miniapp-core', dest)
            self.assertEqual((dest / 'old.txt').read_text(), 'keep')

    def test_install_skip_and_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ('--target', tmp, 'wechat-miniapp-core')
            self.assertEqual(self.run_cli(*args).returncode, 0)
            marker = Path(tmp) / 'wechat-miniapp-core/local.txt'
            marker.write_text('local')
            self.assertEqual(self.run_cli(*args).returncode, 0)
            self.assertTrue(marker.exists())
            self.assertEqual(self.run_cli(*args, '--force').returncode, 0)
            self.assertFalse(marker.exists())

    def test_symlink_destination_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / 'outside'
            outside.mkdir()
            target = Path(tmp) / 'target'
            target.mkdir()
            (target / 'wechat-miniapp-core').symlink_to(outside, target_is_directory=True)
            result = self.run_cli('--target', target, 'wechat-miniapp-core', '--force')
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(outside.exists())

if __name__ == '__main__':
    unittest.main()
