#!/usr/bin/env python3
"""Fetch the gitlink with a step-scoped token; never print private checkout logs."""
import base64
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
logs = Path(os.environ.get('RUNNER_TEMP', root / '.private-build')) / 'iitcmapkit-logs'
logs.mkdir(parents=True, exist_ok=True)
env = os.environ.copy()
token = env.pop('GH_TOKEN')
env.update(GIT_CONFIG_COUNT='1',
           GIT_CONFIG_KEY_0='http.https://github.com/.extraheader',
           GIT_CONFIG_VALUE_0='AUTHORIZATION: basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode())
with (logs / 'checkout.log').open('wb') as output:
    # Refresh the URL in existing clones before fetching the pinned commit.
    for command in (['sync'], ['update', '--init', '--depth', '1']):
        result = subprocess.run(['git', 'submodule', *command, '--', 'iitc_mapkit'],
                                cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            break
if result.returncode:
    print('::error::Private checkout failed; see encrypted diagnostics.')
raise SystemExit(result.returncode)
