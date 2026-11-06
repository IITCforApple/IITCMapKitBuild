#!/usr/bin/env python3
"""Keep private diagnostics off the public console; publish only verified packages."""
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'iitc_mapkit'
LOGS = Path(os.environ.get('RUNNER_TEMP', ROOT / '.private-build')) / 'iitcmapkit-logs'
PACKAGES = ROOT / 'dist-artifacts'
NAMES = ('MACOS_CERTIFICATE_P12_BASE64', 'MACOS_CERTIFICATE_PASSWORD',
         'NOTARY_APPLE_ID', 'NOTARY_APP_PASSWORD', 'SIGNING_IDENTITY', 'SIGNING_TEAM_ID')


def build():
    LOGS.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PACKAGES, ignore_errors=True)
    env = os.environ.copy()
    settings = {name: env.pop(name, '') for name in NAMES}
    for name in ('ARTIFACT_PASSWORD', 'IITCMAPKIT_READ_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN'):
        env.pop(name, None)
    missing = [name for name in NAMES if not settings[name]]
    if missing:
        print('::error::Missing ' + ', '.join(missing), flush=True)
        return 1
    identity = settings['SIGNING_IDENTITY']
    if not identity.startswith('Developer ID Application:') or not identity.endswith('(' + settings['SIGNING_TEAM_ID'] + ')'):
        print('::error::SIGNING_IDENTITY must be a Developer ID Application identity for SIGNING_TEAM_ID.')
        return 1

    def run(name, command, cwd=SOURCE):
        print(name + ': running', flush=True)
        with (LOGS / (name + '.log')).open('wb') as output:
            result = subprocess.run([str(arg) for arg in command], cwd=cwd, env=env,
                                    stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(name)
        print(name + ': passed', flush=True)

    with tempfile.TemporaryDirectory(prefix='iitc-signing-') as temporary:
        temporary = Path(temporary)
        keychain = temporary / 'build.keychain-db'
        original = shlex.split(subprocess.check_output(['security', 'list-keychains', '-d', 'user'], text=True))
        try:
            p12 = temporary / 'signing.p12'
            p12.write_bytes(base64.b64decode(settings['MACOS_CERTIFICATE_P12_BASE64'], validate=True))
            p12.chmod(0o600)
            password = secrets.token_urlsafe(32)
            run('create-keychain', ['security', 'create-keychain', '-p', password, keychain])
            run('keychain-timeout', ['security', 'set-keychain-settings', '-lut', '21600', keychain])
            run('unlock-keychain', ['security', 'unlock-keychain', '-p', password, keychain])
            run('import-certificate', ['security', 'import', p12, '-k', keychain, '-P', settings['MACOS_CERTIFICATE_PASSWORD'], '-T', '/usr/bin/codesign', '-T', '/usr/bin/security'])
            p12.unlink()
            run('key-access', ['security', 'set-key-partition-list', '-S', 'apple-tool:,apple:,codesign:', '-s', '-k', password, keychain])
            run('keychain-search', ['security', 'list-keychains', '-d', 'user', '-s', keychain, *original])
            run('notary-credentials', ['xcrun', 'notarytool', 'store-credentials', 'iitc-build', '--keychain', keychain,
                '--apple-id', settings['NOTARY_APPLE_ID'], '--password', settings['NOTARY_APP_PASSWORD'], '--team-id', settings['SIGNING_TEAM_ID']])
            run('toolchain', ['xcodebuild', '-version'])
            run('metal-toolchain', ['xcodebuild', '-downloadComponent', 'MetalToolchain'])
            run('revision', ['git', 'rev-parse', 'HEAD'])
            env['IITC_SIGN_IDENTITY'] = identity
            run('build', ['zsh', 'Scripts/build.command'])
            run('package-check', ['zsh', 'Scripts/check-package.command'])
            app = SOURCE / '.release/IITC MapKit.app'
            submission = temporary / 'notary.zip'
            run('notary-zip', ['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', app, submission])

            def notarize(path, label):
                run(label, ['xcrun', 'notarytool', 'submit', path, '--keychain-profile', 'iitc-build',
                            '--keychain', keychain, '--wait', '--timeout', '45m', '--output-format', 'json'])
                result = json.loads((LOGS / (label + '.log')).read_text())
                if result.get('status') != 'Accepted':
                    if result.get('id'):
                        run(label + '-details', ['xcrun', 'notarytool', 'log', result['id'], '--keychain-profile', 'iitc-build', '--keychain', keychain])
                    raise RuntimeError(label)
                run(label + '-staple', ['xcrun', 'stapler', 'staple', path if path.suffix == '.dmg' else app])
                run(label + '-ticket', ['xcrun', 'stapler', 'validate', path if path.suffix == '.dmg' else app])

            notarize(submission, 'notarize-app')
            run('gatekeeper-app', ['spctl', '--assess', '--type', 'execute', '--verbose=2', app])
            run('zip', ['zsh', 'Scripts/package-mac.command'])
            version = (SOURCE / 'VERSION').read_text().strip()
            # Source owns the installer artwork and Finder layout for every build.
            run('dmg', ['zsh', 'Scripts/package-mac-dmg.command'])
            dmg = SOURCE / '.release' / f'IITC-MapKit-{version}-macOS-arm64.dmg'
            run('sign-dmg', ['codesign', '--force', '--sign', identity, '--timestamp', dmg])
            notarize(dmg, 'notarize-dmg')
            run('verify-dmg', ['hdiutil', 'verify', dmg])
            run('gatekeeper-dmg', ['spctl', '--assess', '--type', 'open', '--context', 'context:primary-signature', '--verbose=2', dmg])
            run('final-signature', ['codesign', '--verify', '--deep', '--strict', app])
            PACKAGES.mkdir()
            for path in (dmg, dmg.with_suffix('.zip')):
                shutil.copy2(path, PACKAGES / path.name)
                checksum = hashlib.sha256(path.read_bytes()).hexdigest()
                (PACKAGES / (path.name + '.sha256')).write_text(checksum + '  ' + path.name + '\n')
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
                    output.write(f'package_base={dmg.stem}\n')
        finally:
            # Do not leave imported private keys or notary credentials on the runner.
            subprocess.run(['security', 'list-keychains', '-d', 'user', '-s', *original], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['security', 'delete-keychain', str(keychain)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(build())
    except Exception:
        shutil.rmtree(PACKAGES, ignore_errors=True)
        print('::error::Build or notarization failed; details are in the encrypted logs.', flush=True)
        raise SystemExit(1)
