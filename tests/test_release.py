import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('release', Path(__file__).parents[1] / 'scripts/release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.assets = Path(self.temporary.name)
        self.base = 'IITC-MapKit-1.3.0-macOS-arm64'
        for suffix in ('.zip', '.dmg'):
            package = self.assets / (self.base + suffix)
            package.write_bytes(b'fixture package ' + suffix.encode())
            package.with_name(package.name + '.sha256').write_text(
                hashlib.sha256(package.read_bytes()).hexdigest() + '  ' + package.name + '\n')

    def test_valid_assets(self):
        self.assertEqual(len(release.validate_assets('v1.3.0', self.assets)), 4)

    def test_invalid_tags(self):
        for tag in ('1.3.0', 'v1.3', 'v1.3.0-rc1', 'v01.3.0', 'v1.3.0\n'):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                release.version_for_tag(tag)

    def test_wrong_version(self):
        with self.assertRaises(ValueError):
            release.validate_assets('v1.3.1', self.assets)

    def test_corrupt_package(self):
        (self.assets / (self.base + '.zip')).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            release.validate_assets('v1.3.0', self.assets)

    def test_extra_logs_rejected(self):
        (self.assets / 'logs.7z').write_bytes(b'private')
        with self.assertRaises(ValueError):
            release.validate_assets('v1.3.0', self.assets)

    def test_published_release_not_overwritten(self):
        existing = subprocess.CompletedProcess([], 0, '{"isDraft": false}', '')
        with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'owner/build'}), \
             patch.object(release.subprocess, 'run', return_value=existing), \
             patch.object(release.subprocess, 'check_output') as commands:
            with self.assertRaises(ValueError):
                release.publish('v1.3.0', self.assets)
            commands.assert_not_called()

    def test_publish_only_after_download_verification(self):
        commands = []

        def gh(command, **kwargs):
            commands.append(command)
            if command[1:3] == ['release', 'view']:
                if command[command.index('--json') + 1] == 'assets':
                    return json.dumps({'assets': [{'name': p.name} for p in self.assets.iterdir()]})
                return '{"isDraft": false, "url": "https://example.test/release"}'
            if command[1:3] == ['release', 'download']:
                destination = Path(command[command.index('--dir') + 1])
                for path in self.assets.iterdir():
                    shutil.copy2(path, destination / path.name)
            return ''

        missing = subprocess.CompletedProcess([], 1, '', 'release not found')
        with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'owner/build'}), \
             patch.object(release.subprocess, 'run', return_value=missing), \
             patch.object(release.subprocess, 'check_output', side_effect=gh):
            release.publish('v1.3.0', self.assets)
        self.assertEqual([command[2] for command in commands],
                         ['create', 'upload', 'view', 'download', 'edit', 'view'])
        self.assertIn('--draft', commands[0])
        self.assertIn('--verify-tag', commands[0])


if __name__ == '__main__':
    unittest.main()
