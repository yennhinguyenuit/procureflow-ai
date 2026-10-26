"""Install an official local llama.cpp CPU runtime and Qwen model in this project.

Only this setup command downloads files. The running agent never contacts a
cloud model. Large weights and binaries are ignored by Git.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = 'qwen2.5-1.5b-instruct-q4_k_m.gguf'
MODEL_SHA256 = '6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'
MODEL_SIZE = 1_117_320_736
MODEL_REPOSITORY = 'https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF'
GITHUB_API = 'https://api.github.com/repos/ggml-org/llama.cpp/releases'


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'ProcureFlow-LocalAI-Setup/1.0'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def download(url: str, path: Path, sha256: str | None = None,
             expected_size: int | None = None) -> None:
    if path.is_file() and (not expected_size or path.stat().st_size == expected_size):
        if sha256 and digest(path) == sha256:
            print(f'Already verified: {path.name}', flush=True)
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.part')
    print(f'Downloading {path.name}', flush=True)
    request = urllib.request.Request(url, headers={'User-Agent': 'ProcureFlow-LocalAI-Setup/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, partial.open('wb') as output:
            total = int(response.headers.get('Content-Length', 0))
            received, last_report = 0, 0
            for block in iter(lambda: response.read(4 * 1024 * 1024), b''):
                output.write(block)
                received += len(block)
                if received - last_report >= 64 * 1024 * 1024:
                    print(f'  {received / 1024**2:.0f} / {(total or expected_size or received) / 1024**2:.0f} MiB', flush=True)
                    last_report = received
    except OSError:
        # Windows' native TLS stack can reach hosts that reset OpenSSL handshakes.
        print('Retrying with the native Windows HTTPS client...', flush=True)
        subprocess.run(['curl.exe', '--location', '--fail', '--silent', '--show-error',
                        '--connect-timeout', '25', '--retry', '2', '--retry-delay', '1',
                        '--output', str(partial), url], check=True)
    if expected_size and partial.stat().st_size != expected_size:
        raise RuntimeError(f'Unexpected file size for {path.name}; keep the .part file for inspection')
    if sha256 and digest(partial) != sha256:
        raise RuntimeError(f'SHA-256 verification failed for {path.name}')
    partial.replace(path)
    print(f'Verified: {path.name}', flush=True)


def install() -> None:
    if platform.system() != 'Windows' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('This installer targets Windows x64. Configure another local llama.cpp server manually.')
    releases = json.loads(fetch(GITHUB_API + '?per_page=12'))
    release, asset = None, None
    for candidate in releases:
        for entry in candidate.get('assets', []):
            if entry['name'].endswith('-bin-win-cpu-x64.zip'):
                release, asset = candidate, entry
                break
        if asset:
            break
    if not asset:
        # Semantic releases can point to the nightly build through this file.
        latest = json.loads(fetch(GITHUB_API + '/latest'))
        pointer = next((a for a in latest.get('assets', []) if a['name'] == 'nightly-tag.txt'), None)
        if pointer:
            tag = fetch(pointer['browser_download_url']).decode().strip()
            release = json.loads(fetch(GITHUB_API + '/tags/' + tag))
            asset = next((a for a in release.get('assets', []) if a['name'].endswith('-bin-win-cpu-x64.zip')), None)
    if asset is None or release is None:
        raise RuntimeError('No official Windows CPU archive found in recent llama.cpp releases')
    runtime = ROOT / 'runtime' / 'llama'
    archive = ROOT / 'runtime' / asset['name']
    runtime_sha = (asset.get('digest') or '').removeprefix('sha256:') or None
    if not runtime_sha:
        raise RuntimeError('Official runtime has no SHA-256 digest; refusing an unverified executable download')
    download(asset['browser_download_url'], archive, runtime_sha, asset['size'])
    runtime.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (runtime / member.filename).resolve()
            if not target.is_relative_to(runtime.resolve()):
                raise RuntimeError('Archive entry escapes the runtime directory')
        bundle.extractall(runtime)
    model_path = ROOT / 'models' / MODEL_NAME
    download(MODEL_REPOSITORY + '/resolve/main/' + MODEL_NAME + f'?download=true&setup={int(time.time())}',
             model_path, MODEL_SHA256, MODEL_SIZE)
    (model_path.parent / 'QWEN-LICENSE.txt').write_bytes(fetch(MODEL_REPOSITORY + '/resolve/main/LICENSE'))
    manifest = {'runtime_release': release['tag_name'], 'runtime_source': asset['browser_download_url'],
                'runtime_sha256': runtime_sha, 'model_source': MODEL_REPOSITORY,
                'model_file': MODEL_NAME, 'model_sha256': MODEL_SHA256,
                'model_bytes': MODEL_SIZE}
    (ROOT / 'runtime' / 'local-ai-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Local AI installed. Run: .\\.venv\\Scripts\\python.exe -m scripts.run', flush=True)


if __name__ == '__main__':
    install()
