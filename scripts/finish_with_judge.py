"""Prompt locally for judge access; never write credentials to disk."""
import getpass
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse


def main():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    for name, prompt in (
        ('JUDGE_API_URL', 'Chat-completions endpoint URL: '),
        ('JUDGE_MODEL_ID', 'Judge model ID: '),
        ('JUDGE_API_KEY', 'Judge API key (hidden): '),
    ):
        if not env.get(name):
            env[name] = (getpass.getpass(prompt) if name.endswith('KEY') else input(prompt)).strip()
        if not env[name]:
            raise SystemExit(f'{name} is required; nothing was sent.')
    url = urlparse(env['JUDGE_API_URL'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise SystemExit('Use an HTTPS endpoint URL without embedded credentials.')
    print('Running the 60-output judge evaluation. The configured provider may charge API usage.')
    return subprocess.run(['bash', 'scripts/finish_submission.sh'], cwd=root, env=env).returncode


if __name__ == '__main__':
    sys.exit(main())
