#!/usr/bin/env python3
"""Encrypt diagnostic logs only with 7-Zip; packages are uploaded separately."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def encrypt(platform):
    password = os.environ.get('ARTIFACT_PASSWORD', '')
    if not password:
        print('::error::ARTIFACT_PASSWORD is required; no plaintext logs will be uploaded.')
        return 1
    sevenzip = shutil.which('7zz') or shutil.which('7z')
    if not sevenzip and os.name == 'nt':
        candidate = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / '7-Zip/7z.exe'
        if candidate.is_file():
            sevenzip = str(candidate)
    if not sevenzip:
        print('::error::7-Zip is not installed.')
        return 1
    logs = Path(os.environ.get('RUNNER_TEMP', ROOT / '.private-build')) / 'iitcmapkit-logs'
    if not logs.is_dir():
        print('No diagnostic logs to encrypt.')
        return 0
    destination = ROOT / 'dist-encrypted'
    destination.mkdir(exist_ok=True)
    output = destination / f'IITCMapKit-{platform}-logs.7z'
    # Never retain an archive from a previous attempt if the new encryption fails.
    output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='iitcmapkit-encrypt-') as temporary:
        payload = Path(temporary)
        if logs.is_dir():
            shutil.copytree(logs, payload / 'logs')
        # AES-256 with encrypted headers; no shell expansion, password never logged.
        commands = [
            [sevenzip, 'a', '-t7z', '-mhe=on', '-mx=1', '-y', '-p' + password, str(output), '.'],
            [sevenzip, 't', '-y', '-p' + password, str(output)],
        ]
        for command in commands:
            try:
                result = subprocess.run(command, cwd=payload, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode:
                    output.unlink(missing_ok=True)
                    print('::error::Encrypted archive creation or verification failed.')
                    return 1
            except OSError:
                output.unlink(missing_ok=True)
                print('::error::Could not start archive encryption.')
                return 1
    print('Encrypted archive verified:', output.name)
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', required=True, choices=['macos-arm64'])
    raise SystemExit(encrypt(parser.parse_args().platform))
