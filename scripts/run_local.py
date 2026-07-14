"""Local runner: start/stop all 7 microservices natively (no Docker needed).

Usage:
  python scripts/run_local.py start     # boots gateway + 6 services, waits for health
  python scripts/run_local.py stop      # kills them via the pidfile
  python scripts/run_local.py status    # health summary through the gateway

Each service gets its own SQLite DB under .runtime/ and logs under .runtime/logs/.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / ".runtime"
PIDFILE = RUNTIME / "pids.txt"

SERVICES = {
    "discovery-service": 8009,
    "user-service": 8001,
    "product-service": 8002,
    "cart-service": 8003,
    "payment-service": 8004,
    "order-service": 8005,
    "notification-service": 8006,
    "gateway": 8000,
}


def _port_free(p: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", p)) != 0


def _wait(url: str, timeout: float = 30.0) -> bool:
    import requests

    end = time.time() + timeout
    while time.time() < end:
        try:
            # The gateway's /health aggregates 6 downstream checks and can take
            # a couple of seconds; use a generous per-request timeout so we don't
            # declare a healthy service "down" just because it answered slowly.
            if requests.get(url, timeout=5).status_code == 200:
                return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


def start() -> None:
    if PIDFILE.exists():
        print("Already running? Run `stop` first, or delete .runtime/pids.txt.")
        return
    # Refuse to start if any port is already taken — a leftover cluster from a
    # previous run would otherwise be silently reused and confuse debugging.
    busy = [svc for svc, port in SERVICES.items() if not _port_free(port)]
    if busy:
        print("ERROR: the following ports are already in use:",
              ", ".join(f"{s}:{SERVICES[s]}" for s in busy))
        print("A stale cluster may still be running. Stop it first:")
        print("  python scripts/run_local.py stop")
        print("If that doesn't help, kill the processes holding those ports and retry.")
        return
    RUNTIME.mkdir(parents=True, exist_ok=True)
    (RUNTIME / "logs").mkdir(exist_ok=True)
    (RUNTIME / "data").mkdir(exist_ok=True)
    os.environ.setdefault("JWT_SECRET", "dev-secret-change-me")
    discovery_url = "http://127.0.0.1:8009"
    pids = []
    env = dict(os.environ)
    env.update({"EVENT_BUS": "memory", "JWT_SECRET": os.environ["JWT_SECRET"],
                "LOG_LEVEL": "INFO", "DISCOVERY_URL": discovery_url})
    for svc, port in SERVICES.items():
        env["SERVICE_NAME"] = svc
        env["PORT"] = str(port)
        env["DATABASE_URL"] = f"sqlite:///{RUNTIME.as_posix()}/data/{svc}.db"
        module = "gateway.main" if svc == "gateway" else f"{svc.replace('-', '_')}.main"
        logf = open(RUNTIME / "logs" / f"{svc}.log", "w")
        p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", f"{module}:app", "--host", "0.0.0.0",
             "--port", str(port)],
            cwd=str(ROOT), env=env, stdout=logf, stderr=subprocess.STDOUT,
        )
        pids.append((svc, p.pid))
        print(f"started {svc} on :{port} (pid {p.pid})")
    PIDFILE.write_text("\n".join(f"{s} {pid}" for s, pid in pids))
    print("waiting for health checks...")
    ok = all(_wait(f"http://127.0.0.1:{port}/health") for port in SERVICES.values())
    if ok:
        # extra safety: confirm each launched process is still alive (a dead pid
        # means uvicorn failed to bind — e.g. a port conflict we didn't catch).
        dead = [(s, p) for s, p in pids if not _pid_alive(p)]
        if dead:
            ok = False
            print("WARN: these services exited immediately (check logs):",
                  ", ".join(f"{s}(pid {p})" for s, p in dead))
    if ok:
        print("\nALL UP. Gateway: http://127.0.0.1:8000  (try /health and /docs)")
        # seed real sample data on first boot (idempotent — safe to re-run)
        print("seeding real sample data (users, categories, products)...")
        try:
            import seed
            seed.main()
        except SystemExit:
            pass
        except Exception as e:  # noqa: BLE001
            print("seed step skipped:", e)
        print("Quick test:  python scripts/smoke.py")
    else:
        print("\nSome services failed to start — see .runtime/logs/*.log")
        print("Run `python scripts/run_local.py stop` before retrying.")


def _pid_alive(pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        return True  # if we can't check, assume alive


def stop() -> None:
    if not PIDFILE.exists():
        print("nothing running (no pidfile).")
    else:
        for line in PIDFILE.read_text().splitlines():
            svc, pid = line.split()
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f"stopped {svc} (pid {pid})")
            except Exception as e:  # noqa: BLE001
                print(f"could not stop {svc}: {e}")
        PIDFILE.unlink()
    # Belt-and-suspenders: kill anything still bound to our ports (handles
    # stale pidfiles / orphaned workers from crashed runs).
    killed = _kill_by_ports(list(SERVICES.values()))
    if killed:
        print(f"also force-stopped {len(killed)} orphaned process(es) on service ports.")
    print("done.")


def _kill_by_ports(ports: list[int]) -> list[int]:
    """Best-effort: find PIDs listening on the given ports and SIGKILL them."""
    killed: list[int] = []
    try:
        import psutil
    except Exception:
        return killed
    listening = {c.laddr.port: c.pid for c in psutil.net_connections(kind="tcp")
                 if c.status == "LISTEN" in ("LISTEN",) and c.pid}
    for p in ports:
        pid = listening.get(p)
        if pid:
            try:
                psutil.Process(pid).kill()
                killed.append(pid)
            except Exception:  # noqa: BLE001
                pass
    return killed


def status() -> None:
    import requests
    try:
        r = requests.get("http://127.0.0.1:8000/health", timeout=3)
        print(r.json())
    except Exception as e:  # noqa: BLE001
        print("gateway not reachable:", e)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["start", "stop", "status"])
    args = ap.parse_args()
    {"start": start, "stop": stop, "status": status}[args.cmd]()


if __name__ == "__main__":
    main()
