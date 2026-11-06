#!/usr/bin/env python3
"""Publish exactly four verified assets, keeping diagnostics out of Releases."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def version_for_tag(tag):
    if not re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', tag):
        raise ValueError('Release tag must be vMAJOR.MINOR.PATCH')
    return tag[1:]


def validate_assets(tag, directory):
    base = f'IITC-MapKit-{version_for_tag(tag)}-macOS-arm64'
    paths = [directory / (base + suffix) for suffix in ('.zip', '.zip.sha256', '.dmg', '.dmg.sha256')]
    if set(directory.iterdir()) != set(paths) or any(not p.is_file() or p.is_symlink() for p in paths):
        raise ValueError('Release must contain exactly ZIP, DMG and their two checksums')
    for package, checksum in zip(paths[::2], paths[1::2]):
        expected = hashlib.sha256(package.read_bytes()).hexdigest() + '  ' + package.name
        if not package.stat().st_size or checksum.read_text().strip() != expected:
            raise ValueError('Package checksum mismatch: ' + package.name)
    return paths


def publish(tag, directory):
    paths = validate_assets(tag, directory)
    repo = os.environ['GITHUB_REPOSITORY']

    def gh(*args):
        return subprocess.check_output(['gh', *args, '--repo', repo], text=True)

    # A rerun can resume a draft, but never replaces a published release.
    existing = subprocess.run(['gh', 'release', 'view', tag, '--repo', repo,
                               '--json', 'isDraft'], capture_output=True, text=True)
    if existing.returncode == 0:
        if not json.loads(existing.stdout)['isDraft']:
            raise ValueError('Release is already published; refusing to overwrite it')
    elif 'release not found' not in existing.stderr.lower():
        raise RuntimeError('Unable to check existing release: ' + existing.stderr)
    else:
        with tempfile.TemporaryDirectory() as temporary:
            notes = Path(temporary) / 'notes.md'
            notes.write_text('macOS arm64 application and disk image.\n\n'
                             'Developer ID signed, notarized, stapled and verified by Gatekeeper in CI.\n'
                             'SHA-256 files are provided for both packages. Encrypted diagnostic logs remain in Actions.\n')
            gh('release', 'create', tag, '--verify-tag', '--draft', '--title', 'IITC MapKit ' + tag[1:], '--notes-file', str(notes))
    gh('release', 'upload', tag, *map(str, paths), '--clobber')
    assets = json.loads(gh('release', 'view', tag, '--json', 'assets'))['assets']
    if {a['name'] for a in assets} != {p.name for p in paths}:
        raise ValueError('Unexpected or missing draft assets; leaving release unpublished')
    with tempfile.TemporaryDirectory() as temporary:
        gh('release', 'download', tag, '--dir', temporary)
        downloaded = validate_assets(tag, Path(temporary))
        expected = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        if any(hashlib.sha256(p.read_bytes()).hexdigest() != expected[p.name] for p in downloaded):
            raise ValueError('Uploaded asset differs; leaving release unpublished')
    gh('release', 'edit', tag, '--draft=false', '--verify-tag')
    result = json.loads(gh('release', 'view', tag, '--json', 'isDraft,url'))
    if result['isDraft']:
        raise RuntimeError('Release is still a draft')
    print('Published:', result['url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--source-version', type=Path)
    parser.add_argument('--assets', type=Path, default=Path('release-assets'))
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    version = version_for_tag(args.tag)
    if args.source_version:
        if args.source_version.read_text().strip() != version:
            raise SystemExit('Tag does not match the pinned source VERSION')
        print('Release tag matches source VERSION')
    elif args.validate_only:
        validate_assets(args.tag, args.assets)
        print('Release assets verified')
    else:
        publish(args.tag, args.assets)
