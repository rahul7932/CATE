#!/usr/bin/env python3
"""
CATE Sandbox runner - starts all four apps and waits for readiness.
Press Ctrl+C to stop.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "fastapi", "uvicorn", "requests"])
    import requests

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
APPS = [
    ("Collector", "sandbox/collector/app.py", 8003),
    ("Trad ML", "sandbox/trad_ml/app.py", 8001),
    ("LLM", "sandbox/llm/app.py", 8002),
    ("Hospital", "sandbox/hospital/app.py", 8000),
]

DEBUG = "--debug" in sys.argv


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for(port: int, timeout: float = 15.0, path: str = "/health") -> bool:
    start = time.time()
    last_err = None
    url = f"http://localhost:{port}{path}"
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code in (200, 304):
                return True
        except Exception as e:
            last_err = e
        time.sleep(0.3)
    if DEBUG and last_err:
        print(f"  Last error: {last_err}", file=sys.stderr)
    return False


def main():
    # Check for port conflicts before starting
    all_ports = [(n, p) for n, _, p in APPS] + [("Frontend", 3000)]
    used = [(name, port) for (name, port) in all_ports if port_in_use(port)]
    if used:
        print("Port(s) already in use. Stop any existing sandbox processes first:")
        for name, port in used:
            print(f"  {name}: port {port}")
        print("\nTo free ports: for p in 8000 8001 8002 8003 3000; do lsof -ti :$p | xargs kill -9 2>/dev/null; done")
        sys.exit(1)

    procs = []
    out = None if DEBUG else subprocess.DEVNULL
    for name, script, port in APPS:
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / script)],
            cwd=str(ROOT),
            stdout=out,
            stderr=out,
        )
        procs.append((name, proc))

    # Collector has /health; others don't. Check collector first, then others by port.
    # Hospital, trad_ml, llm don't have /health - let's add a simple one or just check port.
    # Actually the plan says "health checks on each port". We could do a simple TCP connect
    # or add /health to all. Let me add /health to hospital, trad_ml, llm for consistency.
    # Actually the collector has /health. For the others we can try a GET to their root or
    # just wait a bit. Let me add /health to all apps for simplicity.

    time.sleep(1)
    for name, proc in procs:
        if proc.poll() is not None:
            print(f"Error: {name} exited early (code {proc.returncode})")
            if not DEBUG:
                print("Run with --debug to see subprocess output: python sandbox/run.py --debug")
            for n, p in procs:
                p.terminate()
            sys.exit(1)

    # Wait for all apps
    for (name, _), (_, _, port) in zip(procs, APPS):
        if not wait_for(port):
            print(f"{name} (port {port}) did not become ready")
            for _, p in procs:
                p.terminate()
            sys.exit(1)

    # Start Next.js frontend
    frontend_proc = None
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "package.json").exists():
        node_modules = FRONTEND_DIR / "node_modules"
        if not node_modules.exists():
            print("Installing frontend dependencies...")
            subprocess.check_call(
                ["npm", "install"],
                cwd=str(FRONTEND_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=out,
            stderr=out,
        )
        if not wait_for(3000, timeout=30, path="/"):
            print("Frontend (port 3000) did not become ready")
            for _, p in procs:
                p.terminate()
            if frontend_proc:
                frontend_proc.terminate()
            sys.exit(1)

    print("\nCATE Sandbox running.")
    if frontend_proc:
        print("Open http://localhost:3000")
    else:
        print("API: http://localhost:8000 (Frontend not found - run from frontend/: npm run dev)")
    print("Press Ctrl+C to stop.\n")

    try:
        for _, proc in procs:
            proc.wait()
        if frontend_proc:
            frontend_proc.wait()
    except KeyboardInterrupt:
        for name, proc in procs:
            proc.terminate()
            proc.wait()
        if frontend_proc:
            frontend_proc.terminate()
            frontend_proc.wait()
        print("\nStopped.")


if __name__ == "__main__":
    main()
