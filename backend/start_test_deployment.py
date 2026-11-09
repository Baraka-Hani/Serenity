"""Run an isolated Serenity test instance behind a temporary HTTPS tunnel."""
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "backend" / "test-data"
CLIENT = ROOT / "backend" / "tools" / "cloudflared"


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA, 0o700)
    if not CLIENT.is_file():
        raise SystemExit("Install the official cloudflared client in backend/tools first.")
    children = []
    def stop(*_):
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    tunnel = subprocess.Popen([str(CLIENT), "tunnel", "--no-autoupdate", "--protocol", "http2", "--url", "http://127.0.0.1:8766"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    children.append(tunnel)
    try:
        for line in tunnel.stdout:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                origin = match.group(0)
                env = dict(os.environ, ROAM_PORT="8766", ROAM_DATA_DIR=str(DATA), ROAM_PUBLIC_ORIGIN=origin)
                server = subprocess.Popen([sys.executable, str(ROOT / "backend" / "server.py")], cwd=ROOT, env=env)
                children.append(server)
                (DATA / "test-url.txt").write_text(origin + "\n")
                print("Serenity HTTPS test address: " + origin, flush=True)
                break
        else:
            raise SystemExit("Tunnel did not provide an HTTPS address.")
        for line in tunnel.stdout:
            if "ERR" in line:
                print(line.rstrip(), flush=True)
            if server.poll() is not None:
                raise SystemExit("Test server stopped.")
    finally:
        stop()


if __name__ == "__main__":
    main()
