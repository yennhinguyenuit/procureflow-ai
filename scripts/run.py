"""Run the complete ProcureFlow workspace and its optional bundled local model."""
from __future__ import annotations

import argparse
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def model_is_running() -> bool:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8089/health', timeout=1) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=None, help='Web port: 8002 for the separate coffee workspace, otherwise 8000')
    parser.add_argument('--without-model', action='store_true', help='Use the offline business tools without LLM inference')
    parser.add_argument('--coffee', action='store_true', help='Open the separate synthetic coffee workspace; preserve the default database')
    args = parser.parse_args()
    port = args.port if args.port is not None else (8002 if args.coffee else 8000)
    os.chdir(ROOT)
    load_dotenv(ROOT / '.env')
    if args.coffee:
        from scripts.seed_coffee import seed_coffee
        coffee_path = ROOT / 'outputs' / 'coffee-workspace.db'
        if not coffee_path.exists():
            seed_coffee(coffee_path)
        os.environ['PROCUREFLOW_DB_PATH'] = str(coffee_path)
        print('Opening the separate synthetic coffee workspace. The default database is unchanged.', flush=True)
    if not (ROOT / 'frontend' / 'dist' / 'index.html').is_file():
        raise SystemExit('Build the interface first: cd frontend; npm.cmd install; npm.cmd run build')
    process, logfile = None, None
    if args.without_model:
        os.environ['LOCAL_LLM_ENABLED'] = 'false'
    elif os.getenv('LOCAL_LLM_ENABLED', 'true').lower() not in ('0', 'false', 'no'):
        server = next((ROOT / 'runtime' / 'llama').rglob('llama-server.exe'), None)
        model = ROOT / 'models' / 'qwen2.5-1.5b-instruct-q4_k_m.gguf'
        # Never download or install software implicitly on application startup.
        if server and model.is_file() and not model_is_running():
            (ROOT / 'outputs').mkdir(exist_ok=True)
            logfile = (ROOT / 'outputs' / 'local-ai.log').open('ab')
            threads = max(1, min(4, (os.cpu_count() or 4) - 2))
            process = subprocess.Popen(
                [str(server), '-m', str(model), '--host', '127.0.0.1', '--port', '8089',
                 '-c', '2048', '--parallel', '1', '-t', str(threads),
                 '--alias', 'qwen2.5-1.5b-instruct'],
                cwd=server.parent, stdout=logfile, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            print('Loading the local Qwen model. No cloud connection is used.', flush=True)
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and process.poll() is None:
                if model_is_running():
                    break
                time.sleep(.5)
            if not model_is_running():
                print('Local model is not ready; business tools remain available. See outputs/local-ai.log.', flush=True)
        elif not server or not model.is_file():
            print('Local business agent is ready. Install the optional model with: python -m scripts.setup_local_ai', flush=True)
    print(f'ProcureFlow workspace: http://127.0.0.1:{port}', flush=True)
    try:
        import uvicorn
        uvicorn.run('src.api:app', host='127.0.0.1', port=port, log_level='info')
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        if logfile:
            logfile.close()


if __name__ == '__main__':
    main()
